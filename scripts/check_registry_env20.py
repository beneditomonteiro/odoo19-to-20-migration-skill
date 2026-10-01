#!/usr/bin/env python3
"""Static check: attribute uses on the Registry (`self.pool.X`, `self.env.registry.X`) against the Odoo 20
class. Catches removed helpers such as `registry.clear_all_caches()` (-> `env.transaction.invalidate_ormcache()`).
Instance attributes assigned in `Registry.__init__` (models, _init_modules, ...) are read from the source,
so they are not false positives. Usage: check_registry_env20.py <tree>...   (Odoo 20 venv python)"""
import ast, inspect, os, re, sys, warnings
warnings.filterwarnings('ignore')
ODOO20_SRC = os.environ.get('ODOO20_SRC')
if not ODOO20_SRC:
    raise SystemExit('set ODOO20_SRC to the Odoo 20 source directory')
sys.path.insert(0, ODOO20_SRC)
from odoo.orm import registry as regmod  # noqa: E402
known = set(dir(regmod.Registry)) | set(re.findall(r'self\.(\w+)\s*(?::[^=\n]+)?=', inspect.getsource(regmod)))
bad = {}
def chain(n):
    parts = []
    while isinstance(n, ast.Attribute): parts.append(n.attr); n = n.value
    if isinstance(n, ast.Name): parts.append(n.id)
    return list(reversed(parts))
for root in sys.argv[1:]:
    for dp, dn, fn in os.walk(root):
        if '__pycache__' in dp or (os.sep + 'tests' in dp and not os.environ.get('WITH_TESTS')): continue
        for f in fn:
            if not f.endswith('.py'): continue
            p = os.path.join(dp, f)
            try: t = ast.parse(open(p).read())
            except SyntaxError: continue
            for n in ast.walk(t):
                if isinstance(n, ast.Attribute):
                    c = chain(n)
                    for pre in (['self', 'pool'], ['self', 'env', 'registry'], ['env', 'registry'], ['registry']):
                        if c[:len(pre)] == pre and len(c) == len(pre) + 1 and c[-1] not in known and not c[-1].startswith('__'):
                            bad.setdefault(c[-1], []).append(f'{p}:{n.lineno}')
for name, w in sorted(bad.items()): print(f'Registry.{name}: {len(w)} e.g. {w[0]}')
print('unresolved:', len(bad))
