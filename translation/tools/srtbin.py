"""Parser/builder for the game's binary .srt subtitle format used in data/movie/*.srt

Format:
    uint32 LE  count
    repeated `count` times:
        uint32 LE  start_ms
        uint32 LE  end_ms
        char[20]   speaker (null-padded, not necessarily null-terminated if exactly 20 chars)
        uint32 LE  text_len
        char[text_len] text (UTF-8/Latin-1, CRLF line breaks, no terminator)
"""
import struct
import json
import sys
from pathlib import Path

SPEAKER_LEN = 20


def parse(data: bytes):
    (count,) = struct.unpack_from('<I', data, 0)
    off = 4
    entries = []
    for _ in range(count):
        start, end = struct.unpack_from('<II', data, off)
        off += 8
        speaker_raw = data[off:off + SPEAKER_LEN]
        speaker = speaker_raw.split(b'\x00', 1)[0].decode('latin-1')
        off += SPEAKER_LEN
        (text_len,) = struct.unpack_from('<I', data, off)
        off += 4
        text = data[off:off + text_len].decode('latin-1')
        off += text_len
        entries.append({
            'start': start,
            'end': end,
            'speaker': speaker,
            'text': text,
        })
    assert off == len(data), f'trailing bytes: parsed {off}, total {len(data)}'
    return entries


def build(entries) -> bytes:
    out = struct.pack('<I', len(entries))
    for e in entries:
        speaker_bytes = e['speaker'].encode('latin-1')
        if len(speaker_bytes) > SPEAKER_LEN:
            raise ValueError(f"speaker name too long: {e['speaker']!r}")
        speaker_bytes = speaker_bytes.ljust(SPEAKER_LEN, b'\x00')
        text_bytes = e['text'].encode('latin-1')
        out += struct.pack('<II', e['start'], e['end'])
        out += speaker_bytes
        out += struct.pack('<I', len(text_bytes))
        out += text_bytes
    return out


def dump_worksheet(srt_paths, out_json):
    worksheet = {}
    for p in srt_paths:
        data = Path(p).read_bytes()
        entries = parse(data)
        worksheet[Path(p).name] = entries
    Path(out_json).write_text(json.dumps(worksheet, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'wrote {out_json} with {len(worksheet)} files')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'dump':
        srt_dir = Path(sys.argv[2])
        out_json = sys.argv[3]
        paths = sorted(srt_dir.glob('*_eng.srt'))
        dump_worksheet(paths, out_json)
    elif cmd == 'verify':
        # roundtrip test on one file
        p = Path(sys.argv[2])
        data = p.read_bytes()
        entries = parse(data)
        rebuilt = build(entries)
        print('match:', rebuilt == data, len(rebuilt), len(data))
