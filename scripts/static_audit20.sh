#!/bin/bash
# Static Odoo 19 -> 20 audit. usage: audit20.sh <module_dir>...   (non-test code only unless TESTS=1)
for m in "$@"; do
 n=$(basename $m); echo "=== $n"
 EX="--exclude-dir=__pycache__ --exclude-dir=tests --exclude-dir=i18n --exclude-dir=lib"
 [ -n "$TESTS" ] && EX="--exclude-dir=__pycache__ --exclude-dir=i18n --exclude-dir=lib"
 c(){ label=$1; shift; k=$(grep -rEn $EX "$@" $m 2>/dev/null | wc -l); [ $k -gt 0 ] && printf "  %-34s %s\n" "$label" "$k"; }
 c "manifest version != 20.0" -e "\"version\": *\"19\." --include=__manifest__.py
 c "_sql_constraints" -e "_sql_constraints" --include=*.py
 c "get_param/set_param" -e "\.(get|set)_param\(|name=\"(get|set)_param\"" --include=*.py --include=*.xml
 c "_table_query" -e "_table_query" --include=*.py
 c "report_file" -e "report_file" --include=*.xml --include=*.py
 c "res.bank inherit" -e "_inherit *= *[\"']res\.bank[\"']" --include=*.py
 c "company_registry" -e "company_registry" --include=*.py --include=*.xml
 c "groups_id (users/reports)" -e "groups_id" --include=*.py --include=*.xml
 c "Query from odoo.tools" -e "from odoo\.tools import.*Query" --include=*.py
 c "content_disposition odoo.http" -e "from odoo\.http import.*content_disposition" --include=*.py
 c "check_method_name" -e "check_method_name" --include=*.py
 c "datas= (attachment->raw)" -e "[\"']datas[\"'] *:|datas *=" --include=*.py
 c "name_get" -e "def name_get|\.name_get\(" --include=*.py
 c "read_group(" -e "\.read_group\(" --include=*.py
 c "self._cr/_context/_uid" -e "self\._(cr|context|uid)\b" --include=*.py
 c "@api.returns/cr/uid" -e "@api\.(returns|cr|uid)" --include=*.py
 c "type='json'" -e "type=[\"']json[\"']" --include=*.py
 c "attrs=/states=" -e " attrs=| states=" --include=*.xml
 c "<tree" -e "<tree[ >]" --include=*.xml
 c "kanban-box" -e "kanban-box" --include=*.xml
 c "oe_chatter" -e "oe_chatter" --include=*.xml
 c "expand= in search" -e "expand=\"[01]\"" --include=*.xml
 c "ir.model.access.csv" -e "." --include=ir.model.access.csv
 c "ir.model.access/ir.rule xml" -e "model=\"ir\.(model\.access|rule)\"" --include=*.xml
 c "t-esc" -e "t-esc=" --include=*.xml
 c "web.assets_qunit / QUnit" -e "QUnit|assets_qunit" --include=*.py --include=*.js
 c "odoo.define (legacy js)" -e "odoo\.define|require\(" --include=*.js
 c "jQuery/\$(" -e "\\\$\(|jQuery|\.extend\(\{" --include=*.js
 c "Owl useState/useRef/useEffect" -e "useState|useRef|useEffect|useExternalListener" --include=*.js
 c "Owl static props/defaultProps" -e "static (props|defaultProps)" --include=*.js
 c "useService(action/ui)" -e "useService\([\"'](action|ui|dialog|notification)[\"']" --include=*.js
 c "t-ref / t-slot (owl2)" -e "t-ref=|<t t-slot|t-slot=" --include=*.xml
 c "FontAwesome fa-" -e "class=\"[^\"]*\bfa[ -]" --include=*.xml --include=*.js
 c "@web/legacy / web.core" -e "@web/legacy|web\.core|web\.Widget" --include=*.js --include=*.py
 c "hr.leave.type/contract" -e "hr\.leave\.type|hr\.contract\b" --include=*.py --include=*.xml
 c "account.report legacy fields" -e "filter_analytic\b|foldable" --include=*.xml --include=*.py
 c "cr.commit()" -e "cr\.commit\(\)" --include=*.py
 c "sudo()" -e "\.sudo\(" --include=*.py
 c "external raw SQL execute" -e "cr\.execute\(" --include=*.py
 c "@odoo-module header" -e "@odoo-module" --include=*.js
done
