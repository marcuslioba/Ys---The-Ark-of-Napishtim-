"""Rebuild data/arc/handbook.bin (in-game Handbook: character and monster
bios) in PT-BR.

handbook.bin is an 'arc' container (see arc_container.py); only its
LAST entry, charadb.dat (uncompressed), holds text. Its record format
is documented in handbook_container.py:
    name[32] + u8 page_count + page_count x (u8 len + text) + icon[32]
    [+ 5 x uint32 stats for mons_/boss_ records]

Translations live in extracted/handbook_por.json (one object per record,
in file order: English name/pages for reference + name_por/pages_por).
Each PT page is re-wrapped to the English layout limits (<= 3 lines of
<= 37 chars, ' \\n' line breaks; the engine does not word-wrap), and a
page that ended in '\\n' in the original keeps that trailing '\\n'.
Page count, icon field and monster stats are copied unchanged.

Since charadb.dat is the last entry in handbook.bin, the new (larger)
entry is simply written over the old one at the same offset, its size
field in the arc entry table is updated, and the file is padded to a
2048-byte boundary like the original. Nothing else moves.

Verification performed on every run:
  1. serialize(parse(original)) == original  (byte-exact round trip)
  2. the JSON's English text matches the current extraction
  3. the rebuilt charadb.dat re-parses to the same record count, names
     (except translated ones), page counts, icons and stats, with the
     PT text in place; and every byte of handbook.bin before charadb.dat
     is unchanged apart from that one size field.
"""
import json
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import arc_container as arc  # noqa: E402
import handbook_container as hb  # noqa: E402

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'extracted' / 'arc' / 'handbook.bin'
JSON = ROOT / 'extracted' / 'handbook_por.json'
OUT = ROOT / 'output' / 'handbook.bin'
ENTRY = 'charadb.dat'
SECTOR = 2048

data = SRC.read_bytes()
table_pos, flags, off, size = arc.find_entry(data, ENTRY)
last_end = max(o + s for _, _, o, s in arc.parse(data))
assert off + size == last_end, f'{ENTRY} is not the last entry in the container'
assert not any(data[off + size:]), 'unexpected non-zero bytes after charadb.dat'
orig = data[off:off + size]

# 1. byte-exact round trip of the parser on the original
n = hb.verify_roundtrip(orig)
print(f'{ENTRY}: {size} bytes, {n} records, parser round-trip OK')

records = hb.parse(orig)
tr = json.loads(JSON.read_text())
assert len(tr) == len(records), f'JSON has {len(tr)} records, file has {len(records)}'

# 2. apply translations
for rec, t in zip(records, tr):
    # make sure the JSON still lines up with the binary
    assert t['name'] == rec['name'], (t['id'], t['name'], rec['name'])
    assert t['pages'] == [hb.clean_text(p) for p in rec['pages']], (t['id'], t['name'])
    assert len(t['pages_por']) == len(rec['pages']), (t['id'], 'page count changed')

    if t['name_por'] != rec['name']:
        rec['name_raw'] = hb.encode_name(t['name_por'])
        rec['name'] = t['name_por']

    new_pages = []
    for en, pt in zip(rec['pages'], t['pages_por']):
        if not pt.isascii():
            raise ValueError(f'#{t["id"]} {t["name"]}: non-ASCII (accents?) in {pt!r}')
        new_pages.append(hb.wrap_page(pt, trailing_newline=en.endswith('\n')))
    rec['pages'] = new_pages

new_chunk = hb.serialize(records)

# 3. re-parse and compare structure against the original
orig_recs = hb.parse(orig)
check = hb.parse(new_chunk)
assert len(check) == len(orig_recs)
for o, c, t, wanted in zip(orig_recs, check, tr, records):
    assert c['name'] == t['name_por'], (t['id'], c['name'])
    assert len(c['pages']) == len(o['pages']), (t['id'], 'page count')
    assert c['icon_raw'] == o['icon_raw'], (t['id'], 'icon')
    assert c['stats'] == o['stats'], (t['id'], 'stats')
    assert c['pages'] == wanted['pages'], (t['id'], 'text')
    assert [hb.clean_text(p) for p in c['pages']] == \
        [hb.clean_text(p) for p in t['pages_por']], (t['id'], 'clean text')
assert hb.serialize(check) == new_chunk

# 4. write the new handbook.bin: same prefix, new tail, updated size field
out = bytearray(data[:off]) + new_chunk
struct.pack_into('<I', out, table_pos + arc.NAME_LEN + 8, len(new_chunk))
out += b'\x00' * (-len(out) % SECTOR)

out = bytes(out)
assert out[:table_pos + arc.NAME_LEN + 8] == data[:table_pos + arc.NAME_LEN + 8]
assert out[table_pos + arc.NAME_LEN + 12:off] == data[table_pos + arc.NAME_LEN + 12:off]
assert arc.find_entry(out, ENTRY) == (table_pos, flags, off, len(new_chunk))
assert out[off:off + len(new_chunk)] == new_chunk

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(out)
changed = sum(1 for o, c in zip(orig_recs, check) if o['pages'] != c['pages'])
renamed = sum(1 for o, c in zip(orig_recs, check) if o['name'] != c['name'])
print(f'translated {changed}/{len(check)} records ({renamed} names), '
      f'{ENTRY} {size} -> {len(new_chunk)} bytes')
print(f'handbook.bin {len(data)} -> {len(out)} bytes, written to {OUT}')
