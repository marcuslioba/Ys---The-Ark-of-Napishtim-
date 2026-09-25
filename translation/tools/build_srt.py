import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from srtbin import build, parse

root = Path(__file__).parent.parent
worksheet = json.loads((root / 'extracted' / 'worksheet_por.json').read_text(encoding='utf-8'))
out_dir = root / 'output' / 'movie'
out_dir.mkdir(parents=True, exist_ok=True)

for fname, entries in worksheet.items():
    data = build(entries)
    # sanity roundtrip
    reparsed = parse(data)
    assert reparsed == entries, f'roundtrip mismatch for {fname}'
    out_path = out_dir / fname
    out_path.write_bytes(data)
    orig_path = root / 'extracted' / 'movie' / fname
    orig_size = orig_path.stat().st_size
    print(f'{fname}: orig={orig_size} bytes, new={len(data)} bytes, delta={len(data)-orig_size}')
