#!/usr/bin/env python3
"""After `19.4-00-ir-access`: every Odoo 19 `ir.rule` record must still exist, either as an `ir.access.csv` row
(id == rule id or rule id + `_N`) or as a record still present in the tree. The official script DELETES rules whose
`domain_force` is computed (`eval`, `user.has_group(...)`, `ref(...)`) without writing a replacement: the security rule is
silently gone. Usage: check_rules_preserved20.py <baseline-git-dir> <rev> <module>=<new-module-dir> ...
Prints every lost rule with its domain; each must be ported by hand (ir.access XML record, no group = restriction)
or justified (e.g. a group rule whose domain is [(0,'=',1)] grants nothing)."""
import csv, glob, re, subprocess, sys
from lxml import etree
git, rev, pairs = sys.argv[1], sys.argv[2], sys.argv[3:]
lost = 0
for pair in pairs:
    m, d = pair.split('=')
    files = subprocess.run(['git', '-C', git, 'ls-tree', '-r', '--name-only', rev, m], capture_output=True, text=True).stdout.split()
    rules = []
    for f in files:
        if f.endswith('.xml'):
            x = subprocess.run(['git', '-C', git, 'show', f'{rev}:{f}'], capture_output=True, text=True).stdout
            try: t = etree.fromstring(x.encode())
            except etree.XMLSyntaxError: continue
            for r in t.iter('record'):
                if r.get('model') == 'ir.rule':
                    df = r.find("field[@name='domain_force']")
                    rules.append((r.get('id'), (df.text or df.get('eval') or '')[:90] if df is not None else ''))
    new_ids = {row['id'] for f in glob.glob(d + '/**/ir.access.csv', recursive=True) for row in csv.DictReader(open(f))}
    present = set()
    for f in glob.glob(d + '/**/*.xml', recursive=True):
        present.update(re.findall(r'<record id="([^"]+)" model="ir\.(?:rule|access)"', open(f, encoding='utf-8').read()))
    for rid, dom in rules:
        if not (any(n == rid or n.startswith(rid + '_') for n in new_ids) or rid in present):
            lost += 1; print(f'LOST {m}: {rid}  domain={dom}')
print('lost rules:', lost)
