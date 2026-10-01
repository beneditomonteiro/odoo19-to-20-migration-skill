#!/bin/bash
# Run Odoo's official upgrade_code scripts on a STAGED COPY of the modules, never on the live trees.
# usage: upgrade_code_staged.sh <stage_dir> [extra_lookup_addons_path]
#   <stage_dir> holds copies of the modules to port (git-init it first so the diff can be reviewed).
# Why staged: the scripts walk every addons-path entry (core, Enterprise, OCA, sibling repos) and
# WRITE into any dependency module they touch; a lookup path pointing at a shared tree gets edited.
# domain-dynamic-dates is deliberately NOT run: it rewrites context_today() to 'now' and breaks
# "Today" filters; old-style domains still work on Odoo 20.
set -e
STAGE=$1
ODOO20_ROOT=${ODOO20_ROOT:?set ODOO20_ROOT to the Odoo 20 installation root}
LOOKUP=${2:-$ODOO20_ROOT/enterprise}
ODOO=${ODOO20_ROOT}/odoo/odoo-bin
PY=${ODOO20_PYTHON:-$ODOO20_ROOT/venv/bin/python}
MODS=$(ls "$STAGE" | grep -v '^\.git$')
for s in 17.5-01-tree-to-list 18.1-00-sql-constraint 18.5-00-deprecated-properties 19.1-00-t-call \
         19.3-00-base64-in-xml 19.4-00-ormcache-on-transaction owl3-migration; do
  for m in $MODS; do timeout 100 $PY $ODOO upgrade_code --addons-path "$STAGE" --script $s --glob "$m/**/*" >/dev/null 2>&1 || true; done
  echo "ran $s"
done
for m in $MODS; do   # ir.access needs the dependency closure (Enterprise for approvals etc.)
  timeout 100 $PY $ODOO upgrade_code --addons-path "$STAGE,$LOOKUP" --script 19.4-00-ir-access --glob "$m/**/*" > "$STAGE/../ira_$m.log" 2>&1 || echo "ir-access FAILED for $m (see log)"
done
echo "Now REVIEW: git -C $STAGE diff. Known flaws to fix by hand: stripped <?xml?> headers, &#NNNN; entities,"
echo "  invented ActionManagerPlugin import (real: ActionPlugin), useRef/useLayoutEffect imported from @web/owl2/utils,"
echo "  duplicate const from owl global, 'this.' added to t-as loop vars, inherit-only templates skipped."
