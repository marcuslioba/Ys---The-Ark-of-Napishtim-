"""Parser for the game's generic 'arc' container format, used by
data/arc/*.bin files that bundle several named sub-files together
(e.g. init.bin holds castinfo_eng.dat.z, invinfo_eng.dat.z, etc).

Format:
    uint32 LE  header_size
    repeated entries of 40 bytes each, starting at offset 4, until
    offset 4+header_size:
        char[28]  name (null-padded)
        uint32 LE flags   (high byte 0x40 = directory, 0x01 = file,
                            0x41 = last file in its group)
        uint32 LE offset  (absolute, from start of the arc file)
        uint32 LE size

Any entry whose name ends in '.z' is zlib-compressed with the game's
custom 8-byte header seen throughout this project:
    uint32 LE  crc32(decompressed_data)
    uint32 LE  decompressed_size
    <zlib deflate stream>
"""
import struct
import zlib

ENTRY_SIZE = 40
NAME_LEN = 28


def parse(data: bytes):
    """Return a list of (name, flags, offset, size) for every entry."""
    header_size = struct.unpack_from('<I', data, 0)[0]
    entries = []
    pos = 4
    while pos + ENTRY_SIZE <= header_size + 4:
        name = data[pos:pos + NAME_LEN].split(b'\x00', 1)[0].decode('latin-1')
        flags, offset, size = struct.unpack_from('<III', data, pos + NAME_LEN)
        entries.append((name, flags, offset, size))
        pos += ENTRY_SIZE
    return entries


def read_entry(data: bytes, offset: int, size: int, name: str) -> bytes:
    """Return an entry's raw bytes, decompressing if the name ends in .z."""
    raw = data[offset:offset + size]
    if name.endswith('.z'):
        return decompress(raw)
    return raw


def decompress(compressed_with_header: bytes) -> bytes:
    return zlib.decompress(compressed_with_header[8:])


def compress(data: bytes) -> bytes:
    """Compress with the game's custom 8-byte header (crc32, decompressed_size)."""
    crc = zlib.crc32(data) & 0xffffffff
    return struct.pack('<II', crc, len(data)) + zlib.compress(data, level=9)


def find_entry(data: bytes, name: str):
    """Return (entry_table_offset, flags, data_offset, size) for a named entry, or None."""
    header_size = struct.unpack_from('<I', data, 0)[0]
    pos = 4
    while pos + ENTRY_SIZE <= header_size + 4:
        entry_name = data[pos:pos + NAME_LEN].split(b'\x00', 1)[0].decode('latin-1')
        flags, offset, size = struct.unpack_from('<III', data, pos + NAME_LEN)
        if entry_name == name:
            return pos, flags, offset, size
        pos += ENTRY_SIZE
    return None


def replace_entry(data: bytearray, name: str, new_bytes: bytes) -> None:
    """Overwrite a named entry's payload in place and update its size field.

    The new payload must fit within the space up to the next entry's offset
    (or the file's own end) -- this does not relocate/grow the container,
    it only works when the replacement is the same size or smaller than the
    slot the original entry had room in. Raises if it doesn't fit.
    """
    found = find_entry(bytes(data), name)
    if found is None:
        raise KeyError(f'no entry named {name!r}')
    table_pos, flags, offset, old_size = found

    # Find the next entry's offset to know how much room is available.
    entries = parse(bytes(data))
    offsets = sorted(o for _, _, o, s in entries if s > 0)
    later = [o for o in offsets if o > offset]
    slot_end = later[0] if later else len(data)
    room = slot_end - offset

    if len(new_bytes) > room:
        raise ValueError(
            f'{name}: new size {len(new_bytes)} exceeds available room {room} '
            f'(slot {offset:#x}-{slot_end:#x}); would need to relocate other entries'
        )

    data[offset:offset + room] = new_bytes.ljust(room, b'\x00')
    struct.pack_into('<I', data, table_pos + NAME_LEN + 8, len(new_bytes))
