"""Parser/serializer for data/arc/handbook.bin's charadb.dat entry
(character and monster bios shown in the in-game Handbook).

charadb.dat is NOT compressed and has no header or index table: it is
125 variable-length records packed back to back, nothing else.

Every record:
    char  name[32]       null-padded latin-1 (shown as the entry title)
    uint8 page_count     1-3
    page_count times:
        uint8 length     byte length of this page's text
        char  text[len]  latin-1, NOT null-terminated. '\\n' = manual
                         line break (the engine does not word-wrap; the
                         English always keeps a space before a '\\n').
                         Some pages also end in a trailing '\\n'.
    char  icon[32]       null-padded path, e.g. 'data\\title\\human_001.dds'
    [monster records only]
    uint32 LE stats[5]   enemy data shown on the monster page (HP, etc.)

Which records carry the 20-byte stats block is decided by the icon path:
'data\\title\\mons_NNN.dds' and 'data\\title\\boss_NNN.dds' do, while
'human_NNN' and 'rehda_NNN' (the character bios) do not. The file is
laid out as 31 human + 22 rehda bios, then 72 monster/boss entries (the
first one being the boss "Geis", icon mons_056). The 20 bytes that look
like a "trailer" after the final icon are simply the last monster's
stats block.

What earlier looked like a "page-count byte" + "page marker byte" is
really page_count + a per-page length prefix (e.g. 'n' = 0x6e = 110
bytes). A translated page therefore MUST have its length byte rewritten,
and can be at most 255 bytes long.

parse()/serialize() are byte-exact inverses on the original file
(verified by verify_roundtrip()).
"""
import struct

NAME_SIZE = 32
ICON_SIZE = 32
STATS_SIZE = 20
ICON_SIG = b'data\\'
STATS_ICON_KINDS = (b'\\mons_', b'\\boss_')


def has_stats(icon: bytes) -> bool:
    return any(k in icon for k in STATS_ICON_KINDS)


def parse(chunk: bytes):
    """Return a list of record dicts:
        name_raw  (bytes, 32)    name  (str)
        pages     (list[str])    page texts, latin-1 decoded
        icon_raw  (bytes, 32)    icon  (str)
        stats     (tuple of 5 ints) or None
    Raises if the data does not consume exactly to the end of the chunk.
    """
    records = []
    pos = 0
    while pos < len(chunk):
        start = pos
        name_raw = chunk[pos:pos + NAME_SIZE]
        pos += NAME_SIZE
        count = chunk[pos]
        pos += 1
        if not 1 <= count <= 3:
            raise ValueError(f'record @{start:#x}: bad page count {count}')
        pages = []
        for _ in range(count):
            length = chunk[pos]
            pos += 1
            pages.append(chunk[pos:pos + length].decode('latin-1'))
            pos += length
        icon_raw = chunk[pos:pos + ICON_SIZE]
        pos += ICON_SIZE
        if not icon_raw.startswith(ICON_SIG):
            raise ValueError(f'record @{start:#x}: icon field {icon_raw!r} '
                             f'does not start with {ICON_SIG!r}')
        stats = None
        if has_stats(icon_raw):
            stats = struct.unpack_from('<5I', chunk, pos)
            pos += STATS_SIZE
        if pos > len(chunk):
            raise ValueError(f'record @{start:#x} runs past end of data')
        records.append({
            'offset': start,
            'name_raw': name_raw,
            'name': name_raw.split(b'\x00', 1)[0].decode('latin-1'),
            'pages': pages,
            'icon_raw': icon_raw,
            'icon': icon_raw.split(b'\x00', 1)[0].decode('latin-1'),
            'stats': stats,
        })
    return records


def encode_name(name: str) -> bytes:
    raw = name.encode('latin-1')
    if len(raw) >= NAME_SIZE:
        raise ValueError(f'name {name!r} too long ({len(raw)} >= {NAME_SIZE})')
    return raw.ljust(NAME_SIZE, b'\x00')


def serialize(records) -> bytes:
    """Inverse of parse(). Uses name_raw/icon_raw so untouched records
    are reproduced byte-for-byte (including any padding junk)."""
    out = bytearray()
    for rec in records:
        name_raw = rec['name_raw']
        assert len(name_raw) == NAME_SIZE
        out += name_raw
        pages = rec['pages']
        if not 1 <= len(pages) <= 3:
            raise ValueError(f'{rec["name"]}: bad page count {len(pages)}')
        out.append(len(pages))
        for text in pages:
            raw = text.encode('latin-1')
            if len(raw) > 255:
                raise ValueError(f'{rec["name"]}: page is {len(raw)} bytes (max 255)')
            out.append(len(raw))
            out += raw
        assert len(rec['icon_raw']) == ICON_SIZE
        out += rec['icon_raw']
        if has_stats(rec['icon_raw']):
            out += struct.pack('<5I', *rec['stats'])
        elif rec['stats'] is not None:
            raise ValueError(f'{rec["name"]}: stats on a non-monster record')
    return bytes(out)


def clean_text(page: str) -> str:
    """A page's prose with the manual line breaks removed (for translators)."""
    return ' '.join(line.strip() for line in page.split('\n') if line.strip())


# Layout limits observed in the English data: every page is at most 3
# lines, and lines are <= 39 chars (almost all <= 37). The engine does not
# word-wrap on its own, so translated text is re-wrapped to these limits.
MAX_LINE = 37
MAX_LINES = 3


def wrap_page(text: str, trailing_newline: bool = False,
              width: int = MAX_LINE, max_lines: int = MAX_LINES) -> str:
    """Greedy word-wrap `text` into the in-game page format: lines joined
    by ' \\n' (space kept before the break, like the English). A literal
    '\\n' in `text` forces a break. Raises if the result exceeds the
    page's line budget."""
    lines = []
    for segment in text.split('\n'):
        cur = ''
        for word in segment.split():
            if len(word) > width:
                raise ValueError(f'word too long for a line: {word!r}')
            if not cur:
                cur = word
            elif len(cur) + 1 + len(word) <= width:
                cur += ' ' + word
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    if len(lines) > max_lines:
        raise ValueError(f'{len(lines)} lines > {max_lines}: {lines!r}')
    out = ' \n'.join(lines)
    if trailing_newline:
        out += '\n'
    return out


def verify_roundtrip(chunk: bytes) -> int:
    """Assert serialize(parse(chunk)) == chunk; return the record count."""
    records = parse(chunk)
    rebuilt = serialize(records)
    if rebuilt != chunk:
        first = next(i for i, (a, b) in enumerate(zip(rebuilt, chunk)) if a != b)
        raise AssertionError(f'round-trip mismatch at byte {first:#x} '
                             f'(len {len(rebuilt)} vs {len(chunk)})')
    return len(records)


if __name__ == '__main__':
    from pathlib import Path
    import arc_container as arc
    root = Path(__file__).parent.parent
    data = (root / 'extracted' / 'arc' / 'handbook.bin').read_bytes()
    _, _, off, size = arc.find_entry(data, 'charadb.dat')
    chunk = data[off:off + size]
    n = verify_roundtrip(chunk)
    print(f'charadb.dat: {size} bytes, {n} records, round-trip OK')
