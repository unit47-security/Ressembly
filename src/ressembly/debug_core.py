"""Bounded, debugger-independent memory presentation primitives."""
MAX_ADDRESS = (1 << 64) - 1


def checked_range(address, size, limit):
    if type(address) is not int or type(size) is not int:
        raise ValueError('address and size must be integers')
    if address < 0 or address > MAX_ADDRESS or size < 1 or size > limit:
        raise ValueError('address/size outside supported bounds (size 1..{})'.format(limit))
    if address + size - 1 > MAX_ADDRESS:
        raise ValueError('address range overflows uint64')


def parse_maps(text):
    regions = []
    for line in text.splitlines():
        fields = line.split(None, 5)
        if len(fields) < 5:
            raise ValueError('malformed Linux maps entry')
        lo, hi = (int(part, 16) for part in fields[0].split('-'))
        permissions = fields[1]
        if not 0 <= lo < hi <= 1 << 64 or len(permissions) != 4:
            raise ValueError('invalid Linux mapping range/permissions')
        if any(c not in options for c, options in zip(permissions, ('r-', 'w-', 'x-', 'ps'))):
            raise ValueError('invalid Linux mapping permissions')
        regions.append(dict(start=lo, end=hi, permissions=permissions,
                            offset=int(fields[2], 16), device=fields[3], inode=int(fields[4]),
                            path=fields[5] if len(fields) == 6 else ''))
    return regions


def readable_prefix(regions, address, size):
    """Consecutive readable byte count, even across adjacent mappings."""
    cursor = address
    end = address + size
    for region in regions:
        if region['end'] <= cursor:
            continue
        if region['start'] > cursor or region['permissions'][0] != 'r':
            break
        cursor = min(end, region['end'])
        if cursor == end:
            break
    return cursor - address


def find_matches(data, pattern, limit=256):
    if not isinstance(pattern, bytes) or not 1 <= len(pattern) <= 256:
        raise ValueError('pattern must contain 1..256 bytes')
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError('match limit must be 1..256')
    offsets, start = [], 0
    while True:
        position = data.find(pattern, start)
        if position < 0:
            return offsets, False
        if len(offsets) == limit:
            return offsets, True
        offsets.append(position)
        start = position + 1


def walk_pointers(address, read, depth):
    checked_range(address, 8, 8)
    if type(depth) is not int or not 1 <= depth <= 32:
        raise ValueError('depth must be 1..32')
    seen, nodes = set(), []
    for _ in range(depth):
        if address == 0:
            return dict(nodes=nodes, termination='null', next_address=address)
        if address in seen:
            return dict(nodes=nodes, termination='cycle', next_address=address)
        seen.add(address)
        try:
            checked_range(address, 8, 8)
            data = read(address, 8)
            if len(data) != 8:
                raise ValueError('short pointer read')
        except (OSError, ValueError, RuntimeError) as error:
            return dict(nodes=nodes, termination='unreadable', next_address=address, error=str(error))
        value = int.from_bytes(data, 'little')
        nodes.append(dict(address=address, value=value))
        address = value
    reason = 'null' if address == 0 else 'cycle' if address in seen else 'depth_limit'
    return dict(nodes=nodes, termination=reason, next_address=address)
