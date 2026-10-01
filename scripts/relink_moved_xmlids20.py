#!/usr/bin/env python3
"""Relink ir_model_data rows whose XML id is now defined by ANOTHER module in the Odoo 20 sources.
Odoo 20 moved/merged records between modules (stock_account -> account, hr_org_chart -> hr, ...). On a restored Odoo 19 DB the
loader then tries to CREATE the record under the new module id and hits unique keys (e.g. ir_act_client_path_unique).
For every row of an installed module whose name is not defined by that module in the sources but is defined by exactly one other
module, the module column is moved (dry-run by default; --apply to write). Data files scanned: XML `id="..."` and CSV first column.
Usage: relink_moved_xmlids20.py DB PORT USER PASSWORD <addons-root>... [--apply]"""
import csv, glob, os, re, subprocess, sys
db, port, user, pw = sys.argv[1:5]; apply = '--apply' in sys.argv
roots = [a for a in sys.argv[5:] if a != '--apply']
env = {'PGPASSWORD': pw, 'PATH': '/usr/bin:/bin'}
def psql(sql):
    r = subprocess.run(['psql', '-h', 'localhost', '-p', port, '-U', user, '-d', db, '-At', '-F', '\t', '-c', sql], capture_output=True, text=True, env=env)
    if r.returncode: raise SystemExit(r.stderr)
    return [l.split('\t') for l in r.stdout.strip().split('\n') if l]
defined = {}          # xmlid name -> set(modules)
rx = re.compile(r'<(?:record|template|menuitem|act_window|report|function)\b[^>]*?\bid="([^"]+)"')
for root in roots:
    for mod in os.listdir(root):
        mp = os.path.join(root, mod)
        if not os.path.exists(os.path.join(mp, '__manifest__.py')): continue
        for p in glob.glob(mp + '/**/*.xml', recursive=True):
            if '/static/' in p or '/tests/' in p: continue
            try: s = open(p, encoding='utf-8').read()
            except OSError: continue
            for n in rx.findall(s):
                n = n.split('.')[-1] if '.' in n and n.split('.')[0] == mod else n
                if '.' not in n: defined.setdefault(n, set()).add(mod)
        for p in glob.glob(mp + '/**/*.csv', recursive=True):
            if '/static/' in p or '/tests/' in p or p.endswith('ir.access.csv') or p.endswith('ir.model.access.csv'): continue
            try:
                for i, row in enumerate(csv.reader(open(p, encoding='utf-8'))):
                    if i and row and '.' not in row[0]: defined.setdefault(row[0], set()).add(mod)
            except (OSError, UnicodeDecodeError, csv.Error): pass
installed = {r[0] for r in psql("select name from ir_module_module where state='installed'")}
rows = psql("select id, module, name, model from ir_model_data where module in (select name from ir_module_module where state='installed') and model not like 'ir.model%' and res_id is not null")
moves = []
for id_, module, name, model in rows:
    mods = defined.get(name)
    if not mods or module in mods: continue
    mods = mods & installed          # only relink towards a module that is installed in this database
    if len(mods) == 1:
        moves.append((id_, module, name, model, next(iter(mods))))
print(f'candidate moved xml ids: {len(moves)}')
by = {}
for m in moves: by.setdefault((m[1], m[4]), []).append(m)
for (a, b), l in sorted(by.items(), key=lambda x: -len(x[1]))[:25]: print(f'  {a} -> {b}: {len(l)}  e.g. {l[0][2]} ({l[0][3]})')
if apply:
    n = 0
    for id_, module, name, model, new in moves:
        exists = psql(f"select 1 from ir_model_data where module='{new}' and name='{name}'")
        if exists: continue
        psql(f"update ir_model_data set module='{new}' where id={id_}"); n += 1
    print('applied', n)
