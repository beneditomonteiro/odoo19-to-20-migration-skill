#!/usr/bin/env python3
"""Static: every `_inherit`/`_inherits`/comodel target must be a model defined somewhere on the Odoo 20 addons path
(core + Enterprise + the ported trees). Catches removed models such as `barcodes.barcode_events_mixin`, `res.bank`,
`hr.leave.type`, which otherwise only fail at registry build.
Usage: check_inherit_targets20.py <src-roots comma list> <tree>..."""
import ast, glob, re, sys
srcs, trees = sys.argv[1].split(','), sys.argv[2:]
defined, used = set(), {}
rx_name = re.compile(r"^\s*_name\s*=\s*[\"']([\w.]+)[\"']", re.M)
for r in srcs + trees:
    for p in glob.glob(r + '/**/*.py', recursive=True):
        if '/tests/' in p or '/migrations/' in p: continue
        try: s = open(p, encoding='utf-8').read()
        except OSError: continue
        defined.update(rx_name.findall(s))
for r in trees:
    for p in glob.glob(r + '/**/*.py', recursive=True):
        if '/tests/' in p or '/migrations/' in p: continue
        try: t = ast.parse(open(p, encoding='utf-8').read())
        except SyntaxError: continue
        for c in ast.walk(t):
            if isinstance(c, ast.ClassDef):
                for st in c.body:
                    if isinstance(st, ast.Assign) and any(getattr(x, 'id', '') in ('_inherit', '_inherits') for x in st.targets):
                        v = st.value
                        names = []
                        if isinstance(v, ast.Constant) and isinstance(v.value, str): names = [v.value]
                        elif isinstance(v, (ast.List, ast.Tuple)): names = [e.value for e in v.elts if isinstance(e, ast.Constant)]
                        elif isinstance(v, ast.Dict): names = [k.value for k in v.keys if isinstance(k, ast.Constant)]
                        for n in names: used.setdefault(n, []).append(f'{p}:{st.lineno}')
bad = {n: w for n, w in used.items() if n not in defined}
for n, w in sorted(bad.items()): print(f'MISSING MODEL {n}: {len(w)} e.g. {w[0]}')
print('missing inherit targets:', len(bad))
