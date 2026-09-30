"""Rebuild data/arc/init.bin with translated item/weapon/armor/accessory
names and descriptions (invinfo_eng.dat.z, a fixed-size-record database
inside the init.bin 'arc' container -- see arc_container.py).

Record layout (184 bytes each, 77 records, 16-byte file header before
the first record):
    char name[0x34]         (52 bytes, null-padded)
    char code[8]             at +0x34  (e.g. 'sw_00', 'ky_23' -- unused here)
    ... 16 bytes of numeric fields at +0x3C (unused here) ...
    char desc[108]           at +0x4C, '\\r\\n' line breaks, null-padded

Names/descriptions are fixed-size slots (52 / 108 bytes) -- unlike
idm.bin there is no pointer table, so translations must fit in the
original byte budget (truncation would corrupt the following record).
extracted/items_por.json holds the accepted translations; a null desc
value means "leave this record untouched" (used for the 5 gold-pickup
entries, whose original text is a Japanese template, not real English).
"""
import json
import struct
from pathlib import Path

import arc_container as arc

root = Path(__file__).parent.parent

NAME_SIZE = 0x34
DESC_OFFSET = 0x4C
DESC_SIZE = 108
RECORD_HEADER = 16


def main():
    data = bytearray((root / 'extracted' / 'arc' / 'init.bin').read_bytes())
    translations = json.loads((root / 'extracted' / 'items_por.json').read_text(encoding='utf-8'))

    found = arc.find_entry(bytes(data), 'invinfo_eng.dat.z')
    if found is None:
        raise SystemExit('invinfo_eng.dat.z not found in init.bin')
    _, _, offset, size = found
    decompressed = bytearray(arc.decompress(bytes(data[offset:offset + size])))

    _n1, _n2, record_size, count = struct.unpack_from('<IIII', decompressed, 0)

    replaced = 0
    for idx_str, entry in translations.items():
        idx = int(idx_str)
        if idx >= count:
            continue
        desc_pt = entry['desc']
        if desc_pt is None:
            continue
        name_pt = entry['name']
        rec_off = RECORD_HEADER + idx * record_size

        name_bytes = name_pt.encode('latin-1').ljust(NAME_SIZE, b'\x00')
        desc_bytes = desc_pt.encode('latin-1').ljust(DESC_SIZE, b'\x00')
        if len(name_bytes) > NAME_SIZE:
            raise ValueError(f'item {idx} ({name_pt!r}): name too long for {NAME_SIZE}-byte slot')
        if len(desc_bytes) > DESC_SIZE:
            raise ValueError(f'item {idx} ({name_pt!r}): description too long for {DESC_SIZE}-byte slot')

        decompressed[rec_off:rec_off + NAME_SIZE] = name_bytes
        decompressed[rec_off + DESC_OFFSET:rec_off + DESC_OFFSET + DESC_SIZE] = desc_bytes
        replaced += 1

    new_entry = arc.compress(bytes(decompressed))
    arc.replace_entry(data, 'invinfo_eng.dat.z', new_entry)

    out_path = root / 'output' / 'init.bin'
    out_path.write_bytes(bytes(data))
    print(f'replaced {replaced} item records')
    print(f'invinfo_eng.dat.z: {size} -> {len(new_entry)} bytes (compressed)')
    print(f'init.bin size unchanged: {len(data)} bytes')


if __name__ == '__main__':
    main()
