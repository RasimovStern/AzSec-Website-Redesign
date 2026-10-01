#!/usr/bin/env python3
"""
Compare this site's rendered text against azsec.biz, block by block.

    python3 tools/compare-content.py

Inputs, both one block per line, next to this script:
    azsec-biz-source-text.txt   azsec.biz, read from the live DOM
    ours.txt                    this page's rendered text, in document order

Produce ours.txt by loading index.html past the entry gate and collecting
  main h1,h2,h3,h4,h5,p,.pull,figcaption,dd,.btn and footer p
in document order, innerText, whitespace collapsed, dropping anything inside
.gloss-panel, .gloss-peek, .mmenu-panel or .gate, and anything under 12 chars.

Matching runs in three passes: exact on normalised text, then containment (one
of our pull-quotes legitimately carries two source blocks — its label and its
body), then similarity down to 0.72. Anything still unmatched is reported
missing. Writes result.json for docs/content-audit.html.
"""

import pathlib

HERE   = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "azsec-biz-source-text.txt"
OURS   = HERE / "ours.txt"
RESULT = HERE / "result.json"

import re, difflib, json, unicodedata

def norm(t):
    t = unicodedata.normalize('NFKC', t)
    t = t.replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"')
    t = re.sub(r'[—–→‑-]+', ' ', t)
    t = t.replace('&', 'and')
    t = re.sub(r'[^a-z0-9 ]', ' ', t.lower())
    return re.sub(r'\s+', ' ', t).strip()

src  = [l.strip() for l in open(SOURCE)  if l.strip()]
ours = [l.strip() for l in open(OURS)     if l.strip()]
ns, no = [norm(x) for x in src], [norm(x) for x in ours]

# A source block also counts as present when it is carried inside one of our
# blocks — our pull-quotes prefix the label onto the quote, so the words are
# all there even though the block boundary differs.
used, rows = set(), []
for i, s0 in enumerate(src):
    key, hit = ns[i], None
    for j, o in enumerate(no):
        if j not in used and o == key: hit = (j, 1.0, 'exact'); break
    if hit is None:
        for j, o in enumerate(no):
            if j in used: continue
            if key and key in o: hit = (j, 1.0, 'contained'); break
    if hit is None:
        for j, o in enumerate(no):
            if key and key in o: hit = (j, 1.0, 'contained'); break
    if hit is None:
        best, bj = 0.0, None
        for j, o in enumerate(no):
            if j in used: continue
            r = difflib.SequenceMatcher(None, key, o).ratio()
            if r > best: best, bj = r, j
        if bj is not None and best >= 0.72: hit = (bj, best, 'near')
    if hit:
        # A containment match does not consume the block: one of our pull-quotes
        # legitimately carries two source blocks (its label and its body).
        if hit[2] != 'contained': used.add(hit[0])
        rows.append({'src': s0, 'ours': ours[hit[0]], 'ratio': hit[1], 'kind': hit[2]})
    else:
        rows.append({'src': s0, 'ours': None, 'ratio': 0.0, 'kind': 'missing'})

# Blocks that carried a source match by containment are accounted for too.
carried = {ours.index(r['ours']) for r in rows if r['kind']=='contained' and r['ours'] in ours}
extra = [ours[j] for j in range(len(ours)) if j not in used and j not in carried]
for r in rows:
    if r['kind'] == 'near':
        a, b = norm(r['src']).split(), norm(r['ours']).split()
        sm = difflib.SequenceMatcher(None, a, b)
        d = []
        for tag,i1,i2,j1,j2 in sm.get_opcodes():
            if tag == 'equal': continue
            d.append(f"{tag}: site[{' '.join(a[i1:i2]) or '-'}] / ours[{' '.join(b[j1:j2]) or '-'}]")
        r['diff'] = d
json.dump({'rows': rows, 'extra': extra}, open(RESULT,'w'), indent=1)

k = lambda n: sum(1 for r in rows if r['kind']==n)
print(f"source blocks : {len(src)}")
print(f"  exact       : {k('exact')}")
print(f"  contained   : {k('contained')}   (source text present inside one of our blocks)")
print(f"  near        : {k('near')}")
print(f"  missing     : {k('missing')}")
print(f"ours-only     : {len(extra)}")
for r in rows:
    if r['kind'] in ('near','missing'):
        print('\n'+r['kind'].upper(), '|', r['src'][:120])
        if r['ours']: print('   ours:', r['ours'][:120])
        for d in r.get('diff', []): print('   ', d)
