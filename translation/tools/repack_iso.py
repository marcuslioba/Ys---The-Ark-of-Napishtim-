import io
from pathlib import Path

import pycdlib
import pycdlib.pycdlib as _pycdlib_mod

# The source ISO uses lowercase, non-conformant ISO9660 filenames (common on PSP
# UMD images). pycdlib refuses to *write* such names by default; since we know
# the existing filesystem already contains them (we can read them fine), relax
# the check for names we add back.
_pycdlib_mod._check_iso9660_filename = lambda name, interchange_level: None

# All *translated* inputs/outputs are resolved relative to this script's own
# location (translation/tools/repack_iso.py -> translation/), so `repack_iso.py`
# always picks up whichever checkout you last ran `git pull` in -- no more
# silently reading a stale copy from some other folder on disk.
ROOT = Path(__file__).resolve().parent.parent

# The original, untranslated ISO is a large binary asset that is intentionally
# NOT tracked in git (see .gitignore). It only needs to exist once on disk; if
# your checkout moves, update this path to point at your copy of the original.
SRC = r"C:\Users\USER\Downloads\Ys The Ark of Napishtim\Ys - The Ark of Napishtim (USA).iso"
DST = str(ROOT / 'output' / 'Ys - The Ark of Napishtim (PT-BR) v3.iso')

REPLACEMENTS = {
    '/PSP_GAME/USRDIR/data/movie/im03a_kaizoku_eng.srt':
        str(ROOT / 'output' / 'movie' / 'im03a_kaizoku_eng.srt'),
    '/PSP_GAME/USRDIR/data/movie/im03b_kazaminooka_eng.srt':
        str(ROOT / 'output' / 'movie' / 'im03b_kazaminooka_eng.srt'),
    '/PSP_GAME/USRDIR/data/arc/idm.bin':
        str(ROOT / 'output' / 'idm.bin'),
}

print(f'Using translated files from: {ROOT / "output"}')
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
