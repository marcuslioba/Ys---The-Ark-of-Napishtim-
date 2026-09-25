import zlib, os

def scan(path, limit=5_000_000):
    data = open(path, 'rb').read()
    starts = []
    start = 0
    while True:
        idx = data.find(b'\x78\xda', start)
        if idx == -1:
            break
        starts.append(idx)
        start = idx + 2
    hits = []
    for idx in starts:
        try:
            dec = zlib.decompressobj()
            out = dec.decompress(data[idx:idx + limit])
            out += dec.flush()
            if len(out) > 20:
                ascii_count = sum(1 for b in out if 32 <= b < 127)
                ratio = ascii_count / max(1, len(out))
                hits.append((idx, len(out), ratio, out[:60]))
        except Exception:
            pass
    return hits

base = r'D:\PSP_GAME\USRDIR\data\arc'
for fname in ['help.bin', 'handbook.bin', 'idm.bin', 'human.bin', 'init.bin', 'rehda.bin']:
    path = os.path.join(base, fname)
    hits = scan(path)
    hits.sort(key=lambda h: -h[2])
    print('===', fname, 'zlib streams:', len(hits))
    for idx, ln, ratio, prev in hits[:5]:
        print('  ', idx, ln, round(ratio, 2), prev)
