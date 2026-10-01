"""Run inside `odoo-bin shell -d <db>`: compare the effective rights of every group between the Odoo 19
`ir.model.access.csv` (read from a git baseline) and the migrated `ir.access` records in the database.
`19.4-00-ir-access` folds rows into implied groups on purpose, so compare EFFECTIVE rights (closure over
implied_ids), never rows.  Set BASELINE_GIT (repo dir), BASELINE_REV (default HEAD), MODULES (comma list).
Prints every (group, model) where an old right is no longer granted; a domain-restricted new row counts as granted.
"""
import csv, io, os, subprocess
repo = os.environ['BASELINE_GIT']; rev = os.environ.get('BASELINE_REV', 'HEAD')
modules = os.environ['MODULES'].split(',')
Data = env['ir.model.data'].sudo(); Groups = env['res.groups'].sudo()

def ref_id(xmlid, default_module):
    module, _, name = (xmlid if '.' in xmlid else f'{default_module}.{xmlid}').partition('.')
    return Data.search([('module', '=', module), ('name', '=', name)], limit=1)

def closure(group):
    seen, todo = set(), [group]
    while todo:
        g = todo.pop()
        if g.id in seen: continue
        seen.add(g.id); todo += list(g.implied_ids)
    return seen

# old rights: (group_id, model_name) -> set(ops)
old = {}
for m in modules:
    for path in (f'{m}/security/ir.model.access.csv',):
        out = subprocess.run(['git', '-C', repo, 'show', f'{rev}:{path}'], capture_output=True, text=True)
        if out.returncode: continue
        for r in csv.DictReader(io.StringIO(out.stdout)):
            md = ref_id(r['model_id:id'], m)
            if not md: continue
            model = env['ir.model'].sudo().browse(md.res_id).model
            gid = False
            if r['group_id:id']:
                g = ref_id(r['group_id:id'], m)
                if not g: continue
                gid = g.res_id
            ops = ''.join(o for o, k in zip('rcud', ('perm_read', 'perm_create', 'perm_write', 'perm_unlink')) if r[k] == '1')
            old.setdefault((gid, model), set()).update(ops)

# new rights: model -> [(group_id or False, ops)]
new = {}
for a in env['ir.access'].sudo().search([]):
    model = a.model_id.model
    new.setdefault(model, []).append((a.group_id.id if a.group_id else False, set(a.operation or '')))

def effective(gid, model):
    if gid is False:
        return set().union(*[ops for g, ops in new.get(model, []) if g is False] or [set()])
    cl = closure(Groups.browse(gid))
    return set().union(*[ops for g, ops in new.get(model, []) if g in cl] or [set()])

missing = 0
for (gid, model), ops in sorted(old.items(), key=lambda x: (str(x[0][0]), x[0][1])):
    got = effective(gid, model)
    if not ops <= got:
        missing += 1
        gname = Groups.browse(gid).full_name if gid else 'ALL'
        print(f'MISSING {model:45s} {gname:50s} old={"".join(sorted(ops))} new={"".join(sorted(got))}')
print(f'old (group, model) pairs: {len(old)}; not covered: {missing}')

# reverse direction: rights the new rows grant that the Odoo 19 ACL never did (the script turns group_user
# company-isolation rules into per-group PERMISSION rows, which can widen rights)
def old_effective(gid, model):
    cl = closure(Groups.browse(gid))
    return set().union(*[ops for (g, m), ops in old.items() if m == model and g in cl] or [set()])
extra = 0
chain_models = {m for (_, m) in old}
for model, rows in sorted(new.items()):
    if model not in chain_models: continue
    for gid in sorted({g for g, _ in rows if g}):
        got, was = effective(gid, model), old_effective(gid, model)
        if not got <= was:
            extra += 1
            print(f'WIDENED {model:45s} {Groups.browse(gid).full_name:50s} old={"".join(sorted(was))} new={"".join(sorted(got))}')
print(f'(group, model) pairs where the new rows grant MORE than Odoo 19: {extra}')
