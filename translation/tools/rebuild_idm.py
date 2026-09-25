import json
import struct
from pathlib import Path

root = Path(__file__).parent.parent
entries = json.loads((root / 'extracted' / 'idm_strings.json').read_text(encoding='utf-8'))
translations = json.loads((root / 'extracted' / 'translations_por.json').read_text(encoding='utf-8'))

src_path = r'D:\PSP_GAME\USRDIR\data\arc\idm.bin'
data = Path(src_path).read_bytes()

entries.sort(key=lambda e: e['offset'])

out = bytearray()
cursor = 0
replaced = 0
for e in entries:
    off = e['offset']
    length = e['length']
    text = e['text']
    # entry record = uint32 length + `length` bytes of text, starting at `off`
    record_start = off
    record_text_start = off + 4
    record_end = record_text_start + length

    # copy any gap before this record unchanged
    out += data[cursor:record_start]

    new_text = translations.get(text)
    if new_text is not None:
        try:
            new_bytes = new_text.encode('cp1252')
        except UnicodeEncodeError:
            new_bytes = new_text.encode('latin-1')
        out += struct.pack('<I', len(new_bytes))
        out += new_bytes
        replaced += 1
    else:
        out += data[record_start:record_end]

    cursor = record_end

out += data[cursor:]

out_path = root / 'output' / 'idm.bin'
out_path.write_bytes(bytes(out))
print(f'replaced {replaced} of {len(entries)} entries')
print(f'original size {len(data)}, new size {len(out)}')
