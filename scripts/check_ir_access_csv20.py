#!/usr/bin/env python3
"""Static check of every ir.access.csv: `model_id` must be a real model NAME (e.g. `mail.message`), not the old
`model_<name>` / `module.model_<name>` xmlid form that `19.4-00-ir-access` leaves when it cannot resolve a model
(an unresolved value loads as NULL and the install dies with `null value in column "model_id"`).
With --fix, rewrites an unambiguous `model_<name_with_underscores>` to the model whose `_name` matches; ambiguous or
unknown values are reported, never guessed.  Also checks the header and that `operation` only has c/r/u/d.
Usage: check_ir_access_csv20.py [--fix] <src-root>[,<src-root>...] <tree>...
  <src-root> list = where model `_name`s are looked up (for example, Odoo core, Enterprise, and custom addon roots)"""
import csv, glob, io, re, sys
args = [a for a in sys.argv[1:] if a != '--fix']; fix = '--fix' in sys.argv
srcs, trees = args[0].split(','), args[1:]
rx = re.compile(r"^\s*_(?:name|inherit)\s*=\s*[\"']([\w.]+)[\"']", re.M)
rx2 = re.compile(r"^\s*_inherit\s*=\s*\[([^\]]*)\]", re.M)
names = set()
for r in srcs + trees:
    for p in glob.glob(r + '/**/*.py', recursive=True):
        if '/tests/' in p or '/migrations/' in p: continue
        try: s = open(p, encoding='utf-8').read()
        except OSError: continue
        names.update(rx.findall(s))
        for m in rx2.findall(s): names.update(re.findall(r"[\"']([\w.]+)[\"']", m))
byx = {}
for n in names: byx.setdefault('model_' + n.replace('.', '_'), set()).add(n)
bad = 0
for t in trees:
    for p in glob.glob(t + '/**/ir.access.csv', recursive=True):
        rows = list(csv.reader(open(p, newline='')))
        if rows[0] != ['id', 'name', 'model_id', 'group_id/id', 'operation', 'domain']:
            print('HEADER', p, rows[0]); bad += 1; continue
        changed = False
        for i, r in enumerate(rows[1:], 2):
            if set(r[4]) - set('crud') or not r[4]: print('OPERATION', p, i, r[4]); bad += 1
            if r[2] in names: continue
            cand = byx.get(r[2].split('.')[-1], set())
            if fix and len(cand) == 1: r[2] = next(iter(cand)); changed = True
            else: print('MODEL', p, i, r[2], sorted(cand)); bad += 1
        if changed:
            out = io.StringIO(); csv.writer(out, lineterminator='\n').writerows(rows); open(p, 'w', newline='').write(out.getvalue())
print('problems:', bad)
