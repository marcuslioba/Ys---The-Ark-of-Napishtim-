"""Rebuild idm.bin with full-length translations (no truncation/padding).

Format (reverse-engineered from extracted/arc/idm.bin -- see NOTES.md):

  Index table at file start (bytes 0x0000-0x3BFF):
    1446 entries of (uint32 offset, uint32 size), little-endian.
    `offset` is relative to BASE=0x3C00, where the data section starts.
    Entries come in consecutive groups of 6: English, a second English
    variant ("UK"), French, German, Spanish, Italian -- always in that
    order. Empty slots have size=0 and still carry the running offset.
    Unused table bytes (after entry 1446, up to 0x3C00) are padded with
    the byte 0x38 ('8'), matching the original file.

  Each non-empty block, starting at BASE+offset:
    uint32 msg_count, uint32 1, uint32 0, uint32 0      (16-byte header)
    then `msg_count` messages, each:
      uint32 msg_id, uint32 n_pages, uint32 n_tok       (12 bytes)
      n_tok x uint32                                     (formatting/page tokens)
      n_pages x (uint32 len, char[len] text)             (page strings)

Only English slots (index % 6 == 0 or 1) are translated, using
extracted/translations_por.json (keyed by the original English text).
Translated pages are written at their real length -- nothing is
truncated or padded -- and the index table is rewritten to match the
new (generally larger) block sizes and offsets.
"""
import json
import struct
from pathlib import Path

BASE = 0x3C00
NUM_TABLE_ENTRIES = 1446

root = Path(__file__).parent.parent
data = (root / 'extracted' / 'arc' / 'idm.bin').read_bytes()
translations = json.loads((root / 'extracted' / 'translations_por.json').read_text(encoding='utf-8'))


def u32(buf, pos):
    return struct.unpack_from('<I', buf, pos)[0]


def parse(data: bytes):
    entries = [struct.unpack_from('<II', data, i * 8) for i in range(NUM_TABLE_ENTRIES)]
    blocks = []
    for slot, (off, sz) in enumerate(entries):
        if sz == 0:
            blocks.append(None)
            continue
        start = BASE + off
        end = start + sz
        p = start
        h0, h1, h2, h3 = (u32(data, p), u32(data, p + 4), u32(data, p + 8), u32(data, p + 12))
        p += 16
        messages = []
        for _ in range(h0):
            mid, npg, ntok = u32(data, p), u32(data, p + 4), u32(data, p + 8)
            p += 12
            toks = [u32(data, p + 4 * i) for i in range(ntok)]
            p += 4 * ntok
            pages = []
            for _ in range(npg):
                L = u32(data, p)
                text_bytes = data[p + 4:p + 4 + L]
                pages.append(text_bytes)
                p += 4 + L
            messages.append({'mid': mid, 'toks': toks, 'pages': pages})
        assert p == end, f'slot {slot}: parsed to {p:#x}, expected {end:#x}'
        blocks.append({'h1': h1, 'h2': h2, 'h3': h3, 'messages': messages})
    return blocks


def apply_translations(blocks):
    replaced = 0
    for slot, block in enumerate(blocks):
        if block is None:
            continue
        if slot % 6 not in (0, 1):
            continue  # only English (and its "UK" variant) slots
        for msg in block['messages']:
            new_pages = []
            for page_bytes in msg['pages']:
                try:
                    text = page_bytes.decode('cp1252')
                except UnicodeDecodeError:
                    new_pages.append(page_bytes)
                    continue
                new_text = translations.get(text)
                if new_text is None:
                    new_pages.append(page_bytes)
                else:
                    new_pages.append(new_text.encode('cp1252'))
                    replaced += 1
            msg['pages'] = new_pages
    return replaced


def serialize(blocks):
    table = bytearray(b'8' * BASE)
    body = bytearray()
    cursor = 0  # relative to BASE
    for slot in range(NUM_TABLE_ENTRIES):
        block = blocks[slot]
        if block is None:
            struct.pack_into('<II', table, slot * 8, cursor, 0)
            continue
        block_start = cursor
        msg_count = len(block['messages'])
        body += struct.pack('<IIII', msg_count, block['h1'], block['h2'], block['h3'])
        for msg in block['messages']:
            body += struct.pack('<III', msg['mid'], len(msg['pages']), len(msg['toks']))
            for t in msg['toks']:
                body += struct.pack('<I', t)
            for page_bytes in msg['pages']:
                body += struct.pack('<I', len(page_bytes))
                body += page_bytes
        block_size = len(body) - block_start
        struct.pack_into('<II', table, slot * 8, block_start, block_size)
        cursor = len(body)
    return bytes(table) + bytes(body)


if __name__ == '__main__':
    blocks = parse(data)
    replaced = apply_translations(blocks)
    out = serialize(blocks)

    out_path = root / 'output' / 'idm.bin'
    out_path.write_bytes(out)
    print(f'replaced {replaced} page strings')
    print(f'original size {len(data)}, new size {len(out)} ({len(out) - len(data):+d} bytes)')
