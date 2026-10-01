"""One-off test: copy FRA block text (which has real accented chars) into
the ENG slot (slot%6==0), which is the slot this USA build always displays
regardless of system language setting. Purpose: confirm whether the game's
font/encoding can render accented Latin-1 characters at all, independent
of the language-switch mechanism (which this USA build ignores).
"""
import sys
sys.path.insert(0, '.')
import rebuild_idm_v2 as r

blocks = r.parse(r.data)

replaced = 0
for group_start in range(0, len(blocks), 6):
    eng = blocks[group_start]
    fra = blocks[group_start + 2] if group_start + 2 < len(blocks) else None
    if eng is None or fra is None:
        continue
    if len(eng['messages']) != len(fra['messages']):
        continue
    for emsg, fmsg in zip(eng['messages'], fra['messages']):
        if len(emsg['pages']) == len(fmsg['pages']):
            emsg['pages'] = fmsg['pages']
            replaced += 1

out = r.serialize(blocks)
out_path = r.root / 'output' / 'idm_fratest.bin'
out_path.write_bytes(out)
print(f'replaced {replaced} messages (ENG <- FRA text)')
print(f'size {len(out)}')
