"""Generic length-prefixed string extractor for idm.bin (and similar files).

Observed record shape around each dialogue line:
    ... some 4-byte header fields ...
    uint32 LE  text_len
    char[text_len]  text   (no separator; next record's header follows immediately)

We don't need to fully understand the header fields to *extract* text: we scan
every 4-byte-aligned position, treat it as a candidate length L, and check
whether the L bytes that follow look like real text. This is heuristic but
works well because game text is heavily printable ASCII/Latin-1 with '\\n'
escapes, while random binary header bytes are not.
"""
import json
import struct
import sys
from pathlib import Path

MIN_LEN = 2
MAX_LEN = 600


def looks_like_text(b: bytes) -> bool:
    if not b:
        return False
    printable = 0
    for byte in b:
        if byte == 0x00:
            return False  # real dialogue text never embeds a null byte
        if 32 <= byte < 127:
            printable += 1
        elif byte in (0x0a, 0x0d):
            printable += 1
        # allow latin-1 accented range for fra/ger/ita/spa blocks
        elif 0xC0 <= byte <= 0xFF:
            printable += 1
        elif byte in (0x81, 0x8A, 0x8D, 0x8F, 0x90, 0x9D):
            return False  # undefined cp1252 control bytes -> not text
    ratio = printable / len(b)
    return ratio > 0.95


def extract(path: str):
    data = Path(path).read_bytes()
    n = len(data)
    results = []
    pos = 0
    # start scanning after the initial pointer table; but to be safe, scan whole file
    while pos + 4 <= n:
        (L,) = struct.unpack_from('<I', data, pos)
        if MIN_LEN <= L <= MAX_LEN and pos + 4 + L <= n:
            candidate = data[pos + 4: pos + 4 + L]
            if looks_like_text(candidate):
                try:
                    text = candidate.decode('cp1252')
                except UnicodeDecodeError:
                    text = None
                if text is not None:
                    results.append({
                        'offset': pos,
                        'len_field_offset': pos,
                        'length': L,
                        'text': text,
                    })
                    pos += 4 + L
                    continue
        pos += 4
    return results


if __name__ == '__main__':
    src = sys.argv[1]
    out = sys.argv[2]
    results = extract(src)
    print(f'extracted {len(results)} strings')
    Path(out).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding='utf-8')
