"""Test build: same as repack_iso.py, but idm.bin has French (accented)
text copied into the English slot instead of our PT-BR translation. Used
to check whether this USA build's font can render accented Latin-1 text
at all, independent of the language-switch setting (which this build
ignores -- see NOTES.md). Run tools/test_fra_in_eng.py first to produce
output/idm_fratest.bin.
"""
import io
from pathlib import Path

import pycdlib
import pycdlib.pycdlib as _pycdlib_mod

_pycdlib_mod._check_iso9660_filename = lambda name, interchange_level: None

ROOT = Path(__file__).resolve().parent.parent

SRC = r"C:\Users\USER\Downloads\Ys The Ark of Napishtim\Ys - The Ark of Napishtim (USA).iso"
DST = str(ROOT / 'output' / 'Ys - The Ark of Napishtim (FRA-TEST).iso')

REPLACEMENTS = {
    '/PSP_GAME/USRDIR/data/arc/idm.bin':
        str(ROOT / 'output' / 'idm_fratest.bin'),
}

print(f'Using test file from: {ROOT / "output" / "idm_fratest.bin"}')
print(f'Reading original ISO from:   {SRC}')

iso = pycdlib.PyCdlib()
iso.open(SRC)

for iso_path, local_path in REPLACEMENTS.items():
    rec = iso.get_record(iso_path=iso_path)
    old_size = rec.get_data_length()
    with open(local_path, 'rb') as f:
        new_bytes = f.read()
    iso.rm_file(iso_path=iso_path)
    iso.add_fp(io.BytesIO(new_bytes), len(new_bytes), iso_path=iso_path)
    print(f'{iso_path}: {old_size} -> {len(new_bytes)} bytes')

iso.write(DST)
iso.close()
print('wrote', DST)
