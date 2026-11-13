"""Export selected code identity without changing target state."""
import hashlib
import json
import os
import gdb
from . import debug_gdb, code_reference
from .experiments import read_bytes, require
from .labtools import MAX_ELF


def capture(address=None):
    inferior, thread, frame = debug_gdb.target()
    pc = int(frame.pc()) if address is None else address
    require(type(pc) is int and 0 <= pc < 2**64, 'invalid code address')
    mappings = [item for item in debug_gdb.read_maps(inferior) if item['start'] <= pc < item['end']]
    require(len(mappings) == 1 and 'x' in mappings[0]['permissions'], 'code must be in an executable mapping')
    mapping = mappings[0]
    path = mapping['path']
    require(path.startswith('/') and not path.endswith(' (deleted)'), 'file-backed nondeleted module required')
    stat = os.stat(path)
    major, minor = (int(part, 16) for part in mapping['device'].split(':'))
    require(stat.st_ino == mapping['inode'] and os.major(stat.st_dev) == major and os.minor(stat.st_dev) == minor,
            'mapped module identity differs from file on disk')
    data = read_bytes(path, MAX_ELF)
    offset = mapping['offset'] + pc - mapping['start']
    va = code_reference.virtual_address(data, offset)
    sample = data[offset:offset + 16]
    require(bytes(inferior.read_memory(pc, len(sample))) == sample, 'runtime code differs from file; refusing static link')
    metadata = debug_gdb.metadata(inferior, thread, frame)
    return dict(schema='ressembly.code-reference.v1', module_path=path,
                module_sha256=hashlib.sha256(data).hexdigest(), file_offset=offset,
                elf_virtual_address=va, runtime_pc=pc, mapping_start=mapping['start'],
                mapping_end=mapping['end'], mapping_offset=mapping['offset'], file_bytes_hex=sample.hex(),
                run_id=metadata['run_id'], pid=inferior.pid, gdb_version=gdb.VERSION,
                provenance='selected stopped code address; file bytes checked against runtime',
                pc_semantics='selected address, not inferred writer or call instruction')


class Reference(gdb.Command):
    """rs-code-reference NEW_FILE [ADDRESS]: export verified ELF code link for Ghidra."""
    def __init__(self):
        super().__init__('rs-code-reference', gdb.COMMAND_FILES)

    def invoke(self, argument, from_tty):
        self.dont_repeat()
        args = gdb.string_to_argv(argument)
        try:
            require(len(args) in (1, 2), 'usage: rs-code-reference NEW_FILE [ADDRESS]')
            result = capture(int(args[1], 0) if len(args) == 2 else None)
            with open(args[0], 'x') as stream:
                json.dump(result, stream, indent=2, ensure_ascii=True)
                stream.write('\n')
            gdb.write('Code reference saved. Import only the matching binary into Ghidra.\n')
        except (ValueError, OSError, gdb.error) as error:
            raise gdb.GdbError(str(error)) from error


def register():
    Reference()
