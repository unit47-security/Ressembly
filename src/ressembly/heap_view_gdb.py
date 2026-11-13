"""Read-only, bounded profiled glibc structural snapshots from debug types."""
import hashlib
import json
import os
import platform
import gdb
from .heap_view import decode_header, require_profile, walk_chain
from .allocator_profiles import occupied_count


def owner_path(objfile):
    while objfile.owner is not None:
        objfile = objfile.owner
    return os.path.realpath(objfile.filename)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class HeapView:
    """One stopped-state view; no cache, event hooks, writes or inferior calls."""
    def __init__(self):
        inferior, thread = gdb.selected_inferior(), gdb.selected_thread()
        if platform.system() != 'Linux' or not inferior.pid or thread is None or not thread.is_stopped():
            raise ValueError('requires a live stopped local Linux inferior')
        if inferior.connection is None or inferior.connection.type != 'native':
            raise ValueError('remote and core-file heap views are unsupported')
        if len(inferior.threads()) != 1:
            raise ValueError('initial structural profile requires one thread')
        # /proc is deliberately used to exclude remote/core sessions and record local provenance.
        with open('/proc/%d/maps' % inferior.pid) as stream:
            maps = stream.read()
        symbol = gdb.lookup_static_symbol('main_arena')
        if symbol is None or symbol.symtab is None:
            raise ValueError('matching libc debug symbols including main_arena are required')
        self.libc = owner_path(symbol.symtab.objfile)
        if self.libc not in maps or os.path.basename(self.libc) != 'libc.so.6':
            raise ValueError('main_arena debug symbols do not belong to mapped local libc.so.6')
        version = gdb.lookup_static_symbol('__libc_version')
        if version is None or owner_path(version.symtab.objfile) != self.libc:
            raise ValueError('cannot identify loaded libc version from its debug symbols')
        version_value = version.value()
        if not 1 <= version_value.type.sizeof <= 32:
            raise ValueError('unsupported libc version debug array size')
        self.version = version_value.string(length=version_value.type.sizeof).split('\x00', 1)[0]
        self.profile = require_profile(self.version, gdb.newest_frame().architecture().name(), gdb.lookup_type('void').pointer().sizeof)
        self.inferior = inferior
        self.arena = symbol.value()
        arena_type = self.arena.type.strip_typedefs()
        if owner_path(arena_type.objfile) != self.libc or arena_type.sizeof != self.profile['arena_size']:
            raise ValueError('unsupported arena debug type ownership or size')
        for name, offset in self.profile['arena_offsets'].items():
            if arena_type[name].bitpos != offset * 8:
                raise ValueError('unsupported arena debug field offset: '+name)
        self.chunk_type = gdb.lookup_type('struct malloc_chunk', symbol.symtab.global_block())
        if owner_path(self.chunk_type.objfile) != self.libc:
            raise ValueError('malloc_chunk type does not belong to the loaded libc')
        self.fd_offset = self.chunk_type['fd'].bitpos // 8
        self.size_offset = self.chunk_type['mchunk_size'].bitpos // 8
        if self.fd_offset != 16 or self.size_offset != 8:
            raise ValueError('unsupported debug type layout')
        tcache_symbol = gdb.lookup_static_symbol('tcache')
        if tcache_symbol is None or owner_path(tcache_symbol.symtab.objfile) != self.libc:
            raise ValueError('matching tcache debug symbol is required')
        self.tcache = tcache_symbol.value()
        self.tcache_state = 'active' if int(self.tcache) else 'not_initialized'
        self.tcache_capacity = None
        self.tcache_max_bytes = None
        if self.version == '2.43':
            dummy = gdb.lookup_static_symbol('__tcache_dummy')
            params = gdb.lookup_static_symbol('mp_')
            if any(item is None or item.symtab is None or owner_path(item.symtab.objfile) != self.libc
                   for item in (dummy, params)):
                raise ValueError('matching tcache dummy and malloc parameters debug symbols are required')
            if int(self.tcache) == int(dummy.value()['inactive'].address):
                self.tcache_state = 'inactive'
            elif int(self.tcache) == int(dummy.value()['disabled'].address):
                self.tcache_state = 'disabled'
            elif not int(self.tcache):
                raise ValueError('null tcache contradicts glibc 2.43 profile')
            self.tcache_capacity = int(params.value()['tcache_count'])
            self.tcache_max_bytes = int(params.value()['tcache_max_bytes'])
            if not 0 <= self.tcache_max_bytes < 1 << 64:
                raise ValueError('unsupported tcache maximum chunk size')
            if not 0 <= self.tcache_capacity <= 65535:
                raise ValueError('unsupported tcache capacity')
        self.validate_tcache_type()
        self.meta = dict(schema='ressembly.heap-structure.v1', glibc=self.version,
                         allocator_profile=self.profile['id'], tcache_counter_semantics=self.profile['tcache_counter_semantics'],
                         libc_path=self.libc, libc_sha256=sha256(self.libc),
                         gdb_version=gdb.VERSION, pid=inferior.pid, inferior=inferior.num,
                         thread=thread.global_num, pc=hex(int(gdb.newest_frame().pc())),
                         scope='main_arena and selected single thread tcache',
                         provenance='stopped GDB debug types and inferior memory',
                         lifetime_inferred=False, exploitability_inferred=False)

    def validate_tcache_type(self):
        cache_type = self.tcache.type.target().strip_typedefs()
        if owner_path(cache_type.objfile) != self.libc:
            raise ValueError('tcache type does not belong to loaded libc')
        counter = self.profile['tcache_counter']
        fields = {field.name: field for field in cache_type.fields()}
        if set(fields) != {counter, 'entries'} or cache_type.sizeof != self.profile['tcache_size']:
            raise ValueError('unsupported tcache debug type layout')
        expected = (0, self.profile['tcache_bins'] - 1)
        for name, width, offset in ((counter, 2, 0), ('entries', 8, self.profile['tcache_entries_offset'])):
            field = fields[name]
            array_type = field.type.strip_typedefs()
            if array_type.code != gdb.TYPE_CODE_ARRAY or array_type.range() != expected or field.bitpos != offset * 8:
                raise ValueError('unsupported tcache array layout')
            element = array_type.target().strip_typedefs()
            if element.sizeof != width or element.code != (gdb.TYPE_CODE_PTR if name == 'entries' else gdb.TYPE_CODE_INT):
                raise ValueError('unsupported tcache element type')
            if name == counter and int(gdb.Value(-1).cast(element)) != 65535:
                raise ValueError('tcache counter must be unsigned uint16')

    def value_at(self, address):
        return gdb.Value(address).cast(self.chunk_type.pointer()).dereference()

    def word(self, address):
        try:
            return int.from_bytes(bytes(self.inferior.read_memory(address, 8)), 'little')
        except gdb.error as error:
            raise MemoryError(str(error)) from error

    def chunk(self, user_address):
        if user_address < 16 or user_address >= 1 << 64 or user_address % 16:
            raise ValueError('user address must be a non-null aligned uint64 address')
        base = user_address - self.fd_offset
        result = decode_header(self.word(base), self.word(base + self.size_offset))
        result.update(user_address=hex(user_address), header_address=hex(base),
                      note='Header interpretation only; caller must identify a real chunk. PREV_INUSE describes the previous chunk.')
        return dict(self.meta, kind='chunk', chunk=result)

    def link_chain(self, first, limit, sentinel=0, encoded=False, user_nodes=False):
        def next_address(address):
            position = address if user_nodes else address + self.fd_offset
            stored = self.word(position)
            return stored ^ (position >> 12) if encoded else stored
        return walk_chain(first, next_address, limit, sentinel)

    def snapshot(self, limit=32):
        # Validate before iterating even when every list is empty.
        walk_chain(0, lambda _: 0, limit)
        arena_fields = {field.name for field in self.arena.type.strip_typedefs().fields()}
        if ('fastbinsY' in arena_fields) != self.profile['fastbins_present']:
            raise ValueError('arena fastbins presence contradicts allocator profile')
        if self.arena['bins'].type.range() != (0, 253):
            raise ValueError('unsupported arena bin layout')
        if self.profile['fastbins_present'] and self.arena['fastbinsY'].type.range() != (0, 9):
            raise ValueError('unsupported fastbin array layout')
        result = dict(self.meta, kind='arena', limit_per_list=limit,
                      arena=dict(address=hex(int(self.arena.address)),
                                 top=hex(int(self.arena['top'])),
                                 next=hex(int(self.arena['next'])),
                                 system_mem=int(self.arena['system_mem']),
                                 mutex=int(self.arena['mutex'])),
                      fastbins=[], bins=[], tcache=[])
        if int(self.arena['next']) != int(self.arena.address):
            raise ValueError('multiple arenas unsupported in initial profile')
        result['allocator_consistency'] = 'unknown; stop outside allocator operations for stable interpretation'
        result['fastbins_state'] = 'present' if self.profile['fastbins_present'] else 'removed_in_glibc_2.43'
        if self.profile['fastbins_present']:
            for index in range(10):
                first = int(self.arena['fastbinsY'][index])
                result['fastbins'].append(dict(index=index, **self.link_chain(first, limit, encoded=True)))
        for index in range(1, 128):
            head = self.arena['bins'][(index - 1) * 2]
            sentinel = int(head.address) - self.fd_offset
            chain = self.link_chain(int(head), limit, sentinel)
            result['bins'].append(dict(index=index, category='unsorted' if index == 1 else ('small' if index < 64 else 'large'),
                                       sentinel=sentinel, **chain))
        result['tcache_state'] = self.tcache_state
        if self.version == '2.43':
            result['tcache_max_chunk_size_exclusive'] = self.tcache_max_bytes
            result['tcache_capacity_semantics'] = 'configured per-bin slot budget; eligibility also depends on chunk size below tcache_max_chunk_size_exclusive'
        if self.tcache_state == 'active':
            cache = self.tcache.dereference()
            for index in range(self.profile['tcache_bins']):
                counter = int(cache[self.profile['tcache_counter']][index])
                count = occupied_count(self.version, counter, self.tcache_capacity)
                chain = self.link_chain(int(cache['entries'][index]), limit, encoded=True, user_nodes=True)
                entry = dict(index=index, category='small' if index < 64 else 'large', declared_count=count,
                    count_matches_traversal=(count == len(chain['nodes'])) if chain['end'] == 'null' else None, **chain)
                if self.version == '2.43':
                    entry.update(available_slots=counter, capacity=self.tcache_capacity)
                result['tcache'].append(entry)
        return result


def render(data):
    lines = ['Ressembly heap structure — glibc %s / GDB %s' % (data['glibc'], data['gdb_version']),
             'Read-only structural snapshot; no allocation lifetime or vulnerability verdict.']
    if data['kind'] == 'chunk':
        chunk = data['chunk']
        lines.append('chunk %s user %s size %#x flags prev_inuse=%s mmap=%s non_main=%s' % (
            chunk['header_address'], chunk['user_address'], chunk['chunk_size'], chunk['prev_inuse'],
            chunk['is_mmapped'], chunk['non_main_arena']))
        lines.append(chunk['note'])
    else:
        lines.append('main_arena %s top %s system_mem %s; limit %d nodes/list' % (
            data['arena']['address'], data['arena']['top'], data['arena']['system_mem'], data['limit_per_list']))
        lines.append('fastbins state='+data['fastbins_state'])
        lines.append('tcache state=%s; counter semantics=%s' % (
            data['tcache_state'], data['tcache_counter_semantics']))
        if 'tcache_max_chunk_size_exclusive' in data:
            lines.append('tcache eligible chunk size < %#x; capacity is a slot budget, not a list length' %
                         data['tcache_max_chunk_size_exclusive'])
        for family in ('fastbins', 'bins', 'tcache'):
            entries = [entry for entry in data[family] if entry['nodes'] or entry['end'] not in ('null', 'sentinel') or entry.get('declared_count', 0)]
            lines.append('%s: %d nonempty or incomplete lists / %d inspected' % (family, len(entries), len(data[family])))
            for entry in entries:
                lines.append('  [%d] %s end=%s%s' % (entry['index'], ' -> '.join(hex(node) for node in entry['nodes']), entry['end'],
                    ' declared_count=%d' % entry['declared_count'] if 'declared_count' in entry else ''))
        lines.append(data['allocator_consistency'])
    return '\n'.join(lines) + '\n'


class HeapCommand(gdb.Command):
    def __init__(self):
        super().__init__('rs-heap-view', gdb.COMMAND_DATA)

    def invoke(self, argument, from_tty):
        """rs-heap-view [arena [LIMIT] | chunk USER_ADDRESS] [--json]

        USER_ADDRESS is an integer, never an evaluated expression. Outputs to terminal only.
        """
        args = gdb.string_to_argv(argument)
        as_json = bool(args and args[-1] == '--json')
        if as_json:
            args.pop()
        try:
            if not args or args[0] == 'arena' and len(args) <= 2:
                limit = int(args[1], 0) if len(args) == 2 else 32
                data = HeapView().snapshot(limit)
            elif args[0] == 'chunk' and len(args) == 2:
                data = HeapView().chunk(int(args[1], 0))
            else:
                raise ValueError('usage: rs-heap-view [arena [LIMIT] | chunk USER_ADDRESS] [--json]')
            gdb.write(json.dumps(data, sort_keys=True) + '\n' if as_json else render(data))
        except (ValueError, OSError, MemoryError, gdb.error) as error:
            raise gdb.GdbError('Ressembly heap view: ' + str(error)) from error


def register():
    HeapCommand()
