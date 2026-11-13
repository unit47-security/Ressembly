"""Bounded structural helpers for the explicitly supported glibc heap view."""
from .allocator_profiles import profile


def require_profile(version, architecture, pointer_size):
    return profile(version, architecture, pointer_size)


def decode_header(previous_size, size_word):
    size = size_word & ~7
    return dict(previous_size=previous_size, size_word=size_word, chunk_size=size,
                prev_inuse=bool(size_word & 1), is_mmapped=bool(size_word & 2),
                non_main_arena=bool(size_word & 4),
                size_plausible=size >= 32 and size % 16 == 0,
                allocation_state='unknown_from_header')


def walk_chain(first, read_next, limit, sentinel=0, alignment=16):
    """Read at most limit nodes. A malformed list is data, never a diagnosis."""
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError('node limit must be between 1 and 256')
    nodes, seen, current = [], set(), first
    while current != sentinel:
        if current == 0:
            return dict(nodes=nodes, end='unexpected_null', next=0)
        if current in seen:
            return dict(nodes=nodes, end='cycle', next=current)
        if current < 0 or current >= 1 << 64 or current % alignment:
            return dict(nodes=nodes, end='unaligned_or_invalid', next=current)
        if len(nodes) == limit:
            return dict(nodes=nodes, end='limit', next=current)
        seen.add(current)
        try:
            next_address = read_next(current)
        except (ValueError, RuntimeError, MemoryError) as error:
            return dict(nodes=nodes, end='unreadable', next=current, error=str(error))
        nodes.append(current)
        current = next_address
    return dict(nodes=nodes, end='sentinel' if sentinel else 'null', next=current)
