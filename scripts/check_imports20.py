#!/usr/bin/env python3
"""Resolve, against the real Odoo 20 source and without a database:
  1. every `from odoo[.x] import Name` / `import odoo.x`;
  2. every attribute use `alias.attr` where `alias` came from `from odoo import alias` (e.g. `http.Request`,
     `tools.ormcache`, `api.returns`, `fields.Foo`, `models.Bar`) and one more level for `alias.a.b`
     when `alias.a` is a module.
Usage: check_imports20.py <tree>...   (tests/ excluded; set WITH_TESTS=1 to include them)
Run with the Odoo 20 venv python. Prints every unresolved name with its first location."""
import ast, importlib, os, sys, types, warnings
warnings.filterwarnings('ignore')
ODOO20_SRC = os.environ.get('ODOO20_SRC')
if not ODOO20_SRC:
    raise SystemExit('set ODOO20_SRC to the Odoo 20 source directory')
sys.path.insert(0, ODOO20_SRC)
import odoo  # noqa: E402
try:
    import odoo.init  # noqa: F401,E402  (sets odoo.SUPERUSER_ID, odoo._, odoo.Command ... shortcuts)
except Exception:  # noqa: BLE001
    pass

bad, cache = {}, {}
def mod(name):
    if name not in cache:
        try: cache[name] = importlib.import_module(name)
        except Exception as e: cache[name] = e
    return cache[name]
def note(key, where, why): bad.setdefault(key, []).append((where, why))

def check_from(module, name, where):
    if module.startswith('odoo.addons.'): return
    m = mod(module)
    if isinstance(m, Exception): return note((module, '<module>'), where, type(m).__name__)
    if name != '*' and not hasattr(m, name):
        sub = mod(module + '.' + name)
        if isinstance(sub, Exception): note((module, name), where, 'missing')

for root in sys.argv[1:]:
    for dp, dn, fn in os.walk(root):
        if '__pycache__' in dp or (os.sep + 'tests' in dp and not os.environ.get('WITH_TESTS')): continue
        for f in fn:
            if not f.endswith('.py'): continue
            p = os.path.join(dp, f)
            try: tree = ast.parse(open(p).read())
            except SyntaxError as e: print('SYNTAX', p, e); continue
            alias = {}                       # local name -> dotted odoo path
            for n in ast.walk(tree):
                if isinstance(n, ast.ImportFrom) and n.module and n.level == 0 and n.module.split('.')[0] == 'odoo':
                    for a in n.names:
                        check_from(n.module, a.name, f'{p}:{n.lineno}')
                        alias[a.asname or a.name] = f'{n.module}.{a.name}'
                elif isinstance(n, ast.Import):
                    for a in n.names:
                        if a.name.split('.')[0] == 'odoo' and not a.name.startswith('odoo.addons'):
                            check_from(a.name, '*', f'{p}:{n.lineno}')
                            if a.asname: alias[a.asname] = a.name
            for n in ast.walk(tree):
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in alias:
                    target = alias[n.value.id]
                    if target.startswith('odoo.addons'): continue
                    obj = mod(target)
                    if isinstance(obj, Exception):
                        try: obj = getattr(mod(target.rsplit('.', 1)[0]), target.rsplit('.', 1)[1])
                        except Exception: continue
                    if isinstance(obj, types.ModuleType):
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter('always')
                            present = hasattr(obj, n.attr)
                        dep = [str(w.message) for w in caught if issubclass(w.category, DeprecationWarning)]
                        if dep:
                            note((target, n.attr), f'{p}:{n.lineno}', 'DEPRECATED: ' + dep[0])
                        elif not present:
                            sub = mod(f'{target}.{n.attr}')
                            if isinstance(sub, Exception):
                                note((target, n.attr), f'{p}:{n.lineno}', 'attribute missing')
for (m, name), w in sorted(bad.items()):
    print(f'{m}.{name}: {len(w)} use(s), e.g. {w[0][0]} [{w[0][1]}]')
print('unresolved:', len(bad))
