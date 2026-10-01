#!/usr/bin/env bash
# Static inventory of Odoo 19 -> 20 migration blockers in a source tree (guide sections 13-15, plus
# the OWL 3 facts verified on the web_responsive port). Read-only. Usage:
#   scan_odoo19_patterns.sh <addons-root> [--files <pattern-name>] [--include-tests]
# Prints, per pattern, the match count per top-level module. A hit is a LEAD, not a verdict: comments,
# docs and tests can match; classify each manually (guide section 14, phase 1).
set -euo pipefail
ROOT="${1:?usage: scan_odoo19_patterns.sh <addons-root> [--files <pattern-name>] [--include-tests]}"; shift || true
FILES_FOR=""; TESTS=0
while [ $# -gt 0 ]; do case "$1" in --files) FILES_FOR="${2:?}"; shift 2;; --include-tests) TESTS=1; shift;; *) echo "unknown $1"; exit 2;; esac; done
command -v rg >/dev/null || { echo "ripgrep (rg) is required"; exit 2; }

# name | area | regex (ripgrep)
PATTERNS='
legacy_js_modules|frontend-critical|odoo\.define|require\(["'"'"']web\.|web\.core|core\.action_registry|core\.qweb
owl2_static_props|owl|static\s+(props|defaultProps)\s*=
owl2_effect_deps|owl|\},\s*\(\)\s*=>\s*\[|useEffect\([^)]*,\s*\(\)\s*=>\s*\[
owl2_state_refs|owl|\buseState\(|\buseRef\(|\buseExternalListener\(
owl_template_directives|owl|t-model|t-portal|t-slot=|t-custom-
jquery_widgets|frontend-critical|\$\(|jQuery|\.extend\(\{|_super\.apply
xml_modifiers|xml|attrs=|\bstates=
xml_tree_tag|xml|<tree[ >]
icons_fontawesome|xml-css|fa fa-|\bfa-[a-z]
sql_table_query|sql-critical|_table_query
raw_sql_interpolation|sql|execute\([^)]*(%s|%\(|\.format\(|f")
orm_deprecated|orm|\bname_get\b|\.read_group\(|\._cr\b|\._context\b|\._uid\b
orm_sudo|security|\.sudo\(\)
binary_fields|binary|fields\.Binary|\.datas\b|b64encode|b64decode
pos_patches|pos|patch\(PaymentScreen|_postPushOrderResolve|pos\.data\.call
qunit_tests|tests-js|QUnit|assets_qunit_tests|QUnit\.
account_reports_legacy|frontend-critical|accountReportsWidget|account_reports\.account_report
'
EXC=(-g '!**/__pycache__/**' -g '!**/i18n/**' -g '!**/.git/**' -g '!**/node_modules/**' -g '!**/*.po' -g '!**/*.pot' -g '!**/*.md' -g '!**/lib/**' -g '!**/static/lib/**')
[ "$TESTS" = 0 ] && EXC+=(-g '!**/tests/**' -g '!**/static/tests/**')
if [ -z "$FILES_FOR" ]; then printf 'Root: %s\n' "$ROOT"; printf '%-26s %-18s %7s  %s\n' PATTERN AREA HITS "TOP MODULES (hits)"; fi
while IFS='|' read -r name area regex; do
  [ -z "${name:-}" ] && continue
  if [ -n "$FILES_FOR" ]; then [ "$name" = "$FILES_FOR" ] && rg -n --no-heading -e "$regex" "${EXC[@]}" "$ROOT" || true; continue; fi
  out=$(rg -c -e "$regex" "${EXC[@]}" "$ROOT" 2>/dev/null || true)
  total=$(printf '%s\n' "$out" | awk -F: 'NF>1{s+=$NF}END{print s+0}')
  top=$(printf '%s\n' "$out" | awk -F: -v r="$ROOT/" 'NF>1{f=$1; sub(r,"",f); split(f,a,"/"); m[a[1]]+=$NF}END{for(k in m) printf "%s %d\n",k,m[k]}' | sort -k2 -nr | head -4 | awk '{printf "%s(%d) ",$1,$2}')
  printf '%-26s %-18s %7s  %s\n' "$name" "$area" "$total" "$top"
done <<< "$PATTERNS"
[ -z "$FILES_FOR" ] && echo "(add --files <pattern> to list every hit; --include-tests to scan tests too)"
