"""Explicit Linux SysV AMD64 allocator profiles; no debugger dependency."""
import re

SUPPORTED_GLIBC = ('2.36', '2.43')


def profile(version, architecture='i386:x86-64', pointer_size=8):
    if version not in SUPPORTED_GLIBC or architecture != 'i386:x86-64' or pointer_size != 8:
        raise ValueError('supported profiles: glibc 2.36 or 2.43, Linux SysV AMD64, 8-byte pointers')
    modern = version == '2.43'
    return dict(id='glibc-'+version+'-amd64', version=version,
                fastbins_present=not modern,
                arena_offsets=({'top':8, 'bins':24, 'next':2072, 'system_mem':2096} if modern
                               else {'top':96, 'bins':112, 'next':2160, 'system_mem':2184}),
                arena_size=2112 if modern else 2200,
                tcache_bins=76 if modern else 64,
                tcache_counter='num_slots' if modern else 'counts',
                tcache_entries_offset=152 if modern else 128,
                tcache_size=760 if modern else 640,
                tcache_counter_semantics='available_slots' if modern else 'occupied_entries')


def banner_version(banner):
    match = re.search(r'\brelease version ([0-9.]+)(?:[,\s]|$)', banner)
    if match is None:
        raise ValueError('cannot identify loaded glibc release version')
    version = match.group(1).removesuffix('.')
    profile(version)
    return version


def occupied_count(version, raw_counter, capacity=None):
    """2.43 slots count down; never label available slots as occupied entries."""
    profile(version)
    if type(raw_counter) is not int or not 0 <= raw_counter <= 65535:
        raise ValueError('invalid uint16 tcache counter')
    if version == '2.36':
        return raw_counter
    if type(capacity) is not int or not 0 <= capacity <= 65535 or raw_counter > capacity:
        raise ValueError('tcache available slots exceed configured capacity')
    return capacity - raw_counter
