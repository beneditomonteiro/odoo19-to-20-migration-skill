#!/usr/bin/env python3
"""Relink records whose XML id was RENAMED inside the same module in Odoo 20 (natural key: the `code` field).
For a model M (e.g. account.report.line) and each installed module: new ids that the Odoo 20 data files define but the database lacks are
matched to existing records of M that carry no id defined by the new files, IF exactly one old record and one new id share that `code`
(ambiguous codes are printed, never guessed). Dry-run by default.
Usage: relink_renamed_xmlids_by_code20.py DB PORT USER PASSWORD MODEL TABLE <addons-root>... [--apply]"""
import glob, os, re, subprocess, sys
db, port, user, pw, model, table = sys.argv[1:7]; apply = '--apply' in sys.argv
roots = [a for a in sys.argv[7:] if a != '--apply']
env = {'PGPASSWORD': pw, 'PATH': '/usr/bin:/bin'}
def q(sql):
    r = subprocess.run(['psql', '-h', 'localhost', '-p', port, '-U', user, '-d', db, '-At', '-F', '\t', '-c', sql], capture_output=True, text=True, env=env)
    if r.returncode: raise SystemExit(r.stderr)
    return [l.split('\t') for l in r.stdout.strip().split('\n') if l]
installed = {r[0] for r in q("select name from ir_module_module where state='installed'")}
new = {}     # (module, code) -> [xmlid names]
defined = set()
rx = re.compile(r'<record\b[^>]*?\bid="([^"]+)"[^>]*?\bmodel="%s"[^>]*>(.*?)</record>' % re.escape(model), re.S)
rx2 = re.compile(r'<record\b[^>]*?\bmodel="%s"[^>]*?\bid="([^"]+)"[^>]*>(.*?)</record>' % re.escape(model), re.S)
for root in roots:
    for mod in os.listdir(root):
        if mod not in installed: continue
        for p in glob.glob(f'{root}/{mod}/**/*.xml', recursive=True):
            if '/tests/' in p or '/static/' in p: continue
            s = open(p, encoding='utf-8').read()
            for m in list(rx.finditer(s)) + list(rx2.finditer(s)):
                name = m.group(1).split('.')[-1]
                # innermost body only: cut nested records
                body = re.split(r'<record\b', m.group(2))[0]
                c = re.search(r'name="code">([^<]+)<', body)
                defined.add((mod, name))
                if c: new.setdefault((mod, c.group(1).strip()), []).append(name)
have = {(r[0], r[1]) for r in q(f"select module,name from ir_model_data where model='{model}'")}
old = {}
for res_id, module, name, code in q(f"select d.res_id,d.module,d.name,t.code from ir_model_data d join {table} t on t.id=d.res_id where d.model='{model}' and t.code is not null"):
    if (module, name) not in defined and module in installed: old.setdefault((module, code), []).append((res_id, name))
moves = []
for (mod, code), names in new.items():
    missing = [n for n in names if (mod, n) not in have]
    cands = old.get((mod, code), [])
    if len(missing) == 1 and len(cands) == 1: moves.append((cands[0][0], mod, cands[0][1], missing[0]))
    elif missing and cands: print(f'AMBIGUOUS {mod} code={code}: new {missing} vs old {[c[1] for c in cands]}')
print(f'{model}: {len(moves)} unambiguous renames')
for res_id, mod, oldn, newn in moves[:15]: print(f'  {mod}.{oldn} -> {mod}.{newn}')
if apply:
    for res_id, mod, oldn, newn in moves:
        q(f"update ir_model_data set name='{newn}', noupdate=false where model='{model}' and res_id={res_id} and module='{mod}' and name='{oldn}'")
    print('applied', len(moves))
