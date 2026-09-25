"""Rebuild idm.bin translating text WITHOUT changing any byte offset in the file.

Each entry's on-disk footprint (the 4-byte length field + `length` bytes of
text) is left byte-for-byte the same size as in the original file. We only
overwrite the text bytes themselves:
  - if the translation encodes to more bytes than the original slot, it is
    truncated to fit;
  - if it encodes to fewer, the remainder is right-padded with spaces.

This guarantees every subsequent record stays at its original file offset,
so any external pointer/index table (which we never fully reverse-engineered)
keeps working. It trades this safety for cropped translations on lines where
the Portuguese text is longer than the English original.
"""
import json
import struct
from pathlib import Path

root = Path(__file__).parent.parent
entries = json.loads((root / 'extracted' / 'idm_strings.json').read_text(encoding='utf-8'))
translations = json.loads((root / 'extracted' / 'translations_por.json').read_text(encoding='utf-8'))

src_path = r'E:\PSP_GAME\USRDIR\data\arc\idm.bin'
data = bytearray(Path(src_path).read_bytes())

replaced = 0
truncated = 0
padded = 0
exact = 0

for e in entries:
    off = e['offset']
    length = e['length']
    text = e['text']
    new_text = translations.get(text)
    if new_text is None:
        continue

    try:
        new_bytes = new_text.encode('cp1252')
    except UnicodeEncodeError:
        new_bytes = new_text.encode('latin-1')

    text_start = off + 4
    if len(new_bytes) > length:
        new_bytes = new_bytes[:length]
        truncated += 1
    elif len(new_bytes) < length:
        new_bytes = new_bytes + b' ' * (length - len(new_bytes))
        padded += 1
    else:
        exact += 1

    assert len(new_bytes) == length
    data[text_start:text_start + length] = new_bytes
    replaced += 1

out_path = root / 'output' / 'idm_safe.bin'
out_path.write_bytes(bytes(data))
print(f'replaced {replaced} entries (exact fit: {exact}, truncated: {truncated}, padded: {padded})')
print(f'file size unchanged: {len(data)} bytes (original was {Path(src_path).stat().st_size})')
