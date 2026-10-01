---
name: odoo20-migration-process
description: >-
  Port Odoo 19 custom modules to Odoo 20 (Owl 3, new account-reports frontend, SQL/`_table_query`
  removal, `_sql_constraints` -> `models.Constraint`, `hr.leave.type` removal, BinaryValue, XML
  modifiers, POS patches, assets/manifests) safely and in phases, on a disposable Odoo 20 database.
  Use when asked to "migrate/port <module> to Odoo 20", to make custom Odoo or OCA modules work on
  Odoo 20, to pick or sanitize a reference database for a
  migration, to run `upgrade_code` / the Owl 3 migration, to review a 19->20 diff, to debug an Odoo
  20 module that installs but silently drops a constraint or field, or to plan/estimate an Odoo 20
  migration. Bundles both a static, unexecuted assessment (guide) and the write-up of a real,
  largely-successful executed migration attempt (findings) with concrete code, gates, and lessons —
  prefer the executed findings whenever the two disagree.
---

# Odoo 19 -> Odoo 20 migration process

Two bundled references, read in this order:

1. `docs/MIGRATION_PROBLEMS.md` (real migration, 2026-09-28) — start
   here. It has a table of contents; jump to the section that matches the symptom you're looking at.
   It wins over the guide below wherever they conflict, because it's what actually happened, not an
   assessment.
2. `docs/MIGRATION_GUIDE.md` (866 lines, 2026-09-25) — the static, unexecuted assessment
   this project started from. Still useful for topics the executed findings don't cover (Owl 2->3
   mechanics, POS PaymentScreen, assets). Read a section with
   `sed -n '<from>,<to>p' docs/MIGRATION_GUIDE.md` (line ranges in
   the mapping table below). Every code skeleton in it is unverified — check it against the local
   Odoo 20 source before use.

Static scan: `scripts/scan_odoo19_patterns.sh <addons-root>` (read-only, needs `rg`); per-module rule counts:
`scripts/static_audit20.sh`; import resolver: `scripts/check_imports20.py`; staged official scripts:
`scripts/upgrade_code_staged.sh`. Start with `docs/STATIC_FIRST_PROCEDURE.md`.

## 0. Ground rules (house, not optional)

0. **Pick and freeze the reference database before touching source code (Gate G0).** A migration
   without a pinned, sanitized reference produces no meaningful bug reports or reconciliation
   evidence — this was the single biggest early time-sink in the real migration this skill is built
   from. Select by business domain and actual installed module scope, never by name similarity or
   "whichever DB happens to be on the cluster" (a similarly-named database was tried and rejected for
   exactly this reason). See `docs/MIGRATION_PROBLEMS.md` §1 for the
   full checklist (identity confirmation, SHA256-hashed backups, raw+sanitized restore pair,
   reference totals recorded before any source edit).
1. Read the deployment map for the environment first. **Never test a migration first on production, a cloud
   instance or a customer database**. Keep environment-specific rules outside this public skill.
2. **Odoo 20 runs only on its own stack.** Code: `$ODOO20_ROOT/odoo` (20.0, see memory for the pinned
   commit); Enterprise: `$ODOO20_ROOT/enterprise20_0924` (zip beside it); venv `$ODOO20_ROOT/venv`; config
   `$ODOO20_CONFIG`; PostgreSQL cluster **`18/odoo20` on port 5439** (`sudo pg_ctlcluster 18 odoo20 start`,
   put it back to stopped afterwards). **Never point Odoo 20 code at LOCAL_EE (9099/5437) or LOCAL_CE
   (8099/5438), and never open an Odoo 19 database with Odoo 20 without the upgrade path** - restore a *copy*
   into the 5439 cluster (guide phase 7). Use `PGPASSWORD=... psql` (a bare `psql` waits for a password).
3. **Do not port in place** in `$ODOO19_ROOT/maxdoo_ao` (other sessions use it). Work on your own branch
   `session-<model>-<YYYYMMDD>-<topic>`, in a copy under the Odoo 20 side (`$ODOO20_ROOT/maxdoo_ao_20`,
   `$ODOO20_ROOT/maxdoo_ce_ao_20`, `$ODOO20_ROOT/maxdooctb_ao_20` — see rule 4 below) or in
   `$ODOO19_ROOT/oca_migrated_20/<OCA-repo>/<module>` for OCA ports. Commit only your files by path and
   open the PR, then **stop and ask before merging** (merge only when the user asked for it), and stay
   on your branch afterwards; never touch another session's work.
4. **Every ported module's local directory (and its eventual GitHub repo) gets a `_20` suffix on the
   Odoo 19 repo name** (`maxdoo_ao` -> `maxdoo_ao_20`, `maxdoo_ce_ao` -> `maxdoo_ce_ao_20`,
   `maxdooctb_ao` -> `maxdooctb_ao_20`), decided 2026-09-28. Reason: the Odoo 19 repos of the same
   name already exist on GitHub, and a repo name must be unique per owner — without the suffix, the
   Odoo 20 port has nowhere to go once it's ready to be pushed. This is a **repo/directory naming
   convention only** — the Odoo *module* technical names inside (`l10n_ao`, `max_l10n_ao_partner_base`,
   etc.) stay exactly as they were at Odoo 19, unchanged, for upgrade-path and cross-reference
   continuity. Only the top-level container gets the suffix.
5. **Schema is a release gate:** after any field change run `-u MODULE -d DB --stop-after-init`, verify the
   columns in `information_schema.columns`, `Modules loaded`/`Registry loaded`, no `UndefinedColumn`, and
   check that the module reached `installed` (an exit code 0 can hide skipped modules).
6. **Trust the local Odoo 20 source over the guide.** The guide's code blocks are skeletons ("not a drop-in
   replacement"). Before using one, open the Odoo 20 file that owns the behavior and read the current
   signature. Facts in section 3 below were verified on real Odoo 20 and override the guide where they differ.
7. Access-control default for new modules (privilege with User/Manager/Administrator roles) still applies to
   any *new* model/menu added during a port. Keep LGPL/OCA copyright headers when porting third-party code.
8. **Before hand-deriving a fix for any newly-hit Odoo 20 incompatibility, check in this order — don't
   write a bespoke fix first and check references later.** This was the exact mistake caught mid-session
   porting `maxdooctb_ao`; findings §13 has the full story and the working examples.
   1. **Diff the Odoo 19 source against `maxdoo_ao`'s (and any other already-ported sibling repo's)
      equivalent module** (`diff -rq --exclude=__pycache__ <repo19>/<module> <other-repo19>/<module>`)
      *before* assuming the module needs independent porting work — some modules turn out
      byte-identical across forks even when the repos' overall relationship is "independent rewrite."
   2. **If a sibling fork already has an Odoo 20 "port" of the same file, verify it actually works
      before trusting it** — a registry-load test never executes JS/Owl templates, so a sibling's port
      can look done (clean install) while still being browser-broken (findings §13 point 2 has a real
      example: static `props`/`useState`/`useRef` that don't exist in this build's vendored Owl at all).
   3. **Check whether an official `odoo-bin upgrade_code` script already covers the exact symptom**
      (`grep` the field/method name across `$ODOO20_ROOT/odoo/odoo/upgrade_code/*.py`) before hand-
      writing the transform yourself. Always review its diff and re-check for anything it only
      partially fixes (a script that only converts the *first* match per record is a real example, not
      hypothetical — findings §13).
   4. **Only once 1-3 come up empty, write a bespoke fix — and then grep the whole repo for the same
      pattern before moving to the next error**, instead of fixing one crashing file at a time. Several
      real bugs this session were found in 10+ files at once this way.
   5. **Bump every module's manifest version to the target major-version prefix as the literal first
      step after copying source**, before any install attempt. A stale version string makes Odoo
      silently mark the module `installable=False` at the module-list-scan stage; the resulting error
      shows up much later, unrelated-looking, and costs real time to trace back to a version-string typo
      (findings §13 has the concrete symptom: a chart-template `KeyError` that was actually this).

9. **Static first, install last (owner rule, 2026-09-29).** Update the code from the references and the
   Odoo 20 source *before* any install; never use install-crash-fix loops to discover changes. Follow
   `docs/STATIC_FIRST_PROCEDURE.md` (audit script, import checker, staged official scripts, gates).
   An install that still fails means the checklist has a gap: fix the code, then add the rule.

## 1. Where the guide covers what (mapping)

| Topic / symptom | Guide § | Lines | First action |
|---|---|---|---|
| Scope, risk headline, module inventory and dependency layers, compatibility table | 1-4 | 1-107 | Build the module inventory from manifests; do not trust the layer list as a full dependency graph |
| Owl 2 -> Owl 3 (static props, `useEffect` deps, `t-model`, `t-portal`, directives) | 5 | 108-219 | Run the scan; replace class `static props` with `useProps`; effects read reactive state |
| Account reports frontend (`odoo.define`, `accountReportsWidget.extend`, jQuery) | 6 | 220-303 | Rewrite on `AccountReport`/`AccountReportController` custom components; never only change imports |
| POS patches (`PaymentScreen._postPushOrderResolve`, `pos.data.call`) | 7 | 304-354 | Read the Odoo 20 order-push lifecycle first; test offline/retry/multi-ID |
| SQL reports, `_table_query` removed | 8 | 355-391 | Rebuild with `SQL`/`TableSQL`/`Domain` like Odoo 20 `sale/report/sale_report.py`; validate columns |
| XML `attrs=`/`states=`, `<tree>` -> `<list>`, icons | 9 | 392-456 | Convert to inline expressions, validate each view on a clean DB, check icons in a browser |
| Binary fields / attachments (`BinaryValue`) | 10 | 457-503 | Review every upload/export/controller; test bytes, base64, RPC and download separately |
| ORM/server API review (`_cr`/`_context`/`_uid`, `name_get`, `read_group`, `sudo`) | 11 | 504-532 | Static scan + functional review; scope every `sudo()` |
| Enterprise 19 vs 20 concrete changes (payment patch, sale report, translations) | 12 | 533-580 | Rebase each patch on the Odoo 20 owner class; never merge old files wholesale |
| Assets and manifests | 13 | 581-610 | Rebuild asset declarations from real Odoo 20 files; asset debug + clean browser |
| The phased plan (phases 0-8) | 14 | 611-755 | Follow the phases below |
| Commands (install, upgrade, tests, static scan, schema SQL) | 15 | 756-813 | Adapt to `$ODOO20_CONFIG` and the 5439 cluster |
| Risk register | 16 | 814-828 | Use as the review checklist in the PR |
| Definition of done | 17 | 829-848 | Acceptance criteria before any release proposal |
| Official references | 18 | 849-860 | Odoo 20 docs and the local Owl 3 bridge/account_reports files |
| Final recommendation | 19 | 861-866 | Port `l10n_ao` and shared models first; rebuild report + reconciliation frontend next |

## 2. The process (guide 14), condensed

This matches what was actually executed closely enough to keep following; step 0 in particular is
underspecified here — see the Gate G0 rule above and findings §1/§9 for the reference-database part
that this list glosses over as "back up source DB + filestore."

0. **Freeze and baseline** - dedicated Odoo 20 branch; record the Odoo 19 and Odoo 20 source revisions;
   back up source DB + filestore; export the manifest dependency inventory; record installed versions.
1. **Static inventory** - run `scripts/scan_odoo19_patterns.sh <root>`; classify each hit (JS module system,
   Owl 2, XML modifier, SQL/report, ORM, security, data migration, integration, performance); assign owner + test.
   Comments/docs/tests are false positives only after manual verification.
2. **Localization foundation** - `l10n_ao` (data, taxes, fiscal positions, journals, sequences), then
   `l10n_ao_complete` only when the base works. Verify posting, credit notes, refunds, reports, multi-company, translations.
3. **Shared models** - `max_l10n_ao_partner_base`, mixins, access rules, views/menus, server and scheduled
   actions. Settle field renames, computes, constraints, groups *before* the big frontend work.
4. **Accounting and reporting** - `max_l10n_ao_report`, asset, IVA, dashboards, `max_3panel_reconciliation`;
   rewrite the report frontend and `_table_query` models; compare totals with a fixed Odoo 19 reference dataset.
5. **Sales, stock, HR, payroll** - test workflows end to end (quotation -> delivery -> invoice -> credit note,
   valuation, time off, payslip, generated entries), not just installation.
6. **POS and integrations** - last: open/close, offline, payment retry, fiscal info, sync, duplicates, timeouts,
   secrets. (signing keys are not in the repo; never commit or move them.)
7. **Database migration** - only after clean installs: restore a *copy* into the 5439 cluster, run the supported
   upgrade path, upgrade custom modules, inspect changed columns, reconcile against Odoo 19 exports, test
   filestore/binaries, repeat on a fresh copy until deterministic.
8. **Acceptance and release** - install from empty DB, upgrade from migrated DB, Python + JS tests, browser tours,
   accounting/stock/HR reconciliation, security review with non-admin roles, performance smoke, backup/restore,
   log review with no unexplained traceback; then the guide's definition of done (17). Production only with the
   owner's explicit go and a rehearsal on a production backup.

## 3. Verified facts from the Maxdoo AO executed migration (win over the guide and over §4)

Full detail and working code in `docs/MIGRATION_PROBLEMS.md`; the
headline points, so you recognize the symptom immediately:

- **`_sql_constraints` is a silent-failure API, not a removed one.** Odoo 20 logs a warning and keeps
  loading, but the database constraint is never created — duplicate rows slip through with nothing
  in the log pointing at it. Port to `models.Constraint` (findings §2 has the working pattern) and
  then *prove* the constraint exists in `pg_constraint`; don't trust a clean exit code.
- **`_table_query` -> `_table_sql`.** A pure placeholder virtual model (e.g. a reconciliation widget)
  becomes `_table_sql = SQL("(0)")`; a real backing query needs Odoo 20's `SQL`/query objects built
  from the actual target table, not guessed from the Odoo 19 shape.
- **`hr.leave.type` was removed as a data model, not renamed as an API.** Its role moved to
  `hr.work.entry.type` — this needs an XML-ID/data mapping plus idempotent pre/post migration
  scripts, not a search-and-replace. Findings §3 has the exact schema to verify afterward.
- **The upgrade command's addons_path and the live service's addons_path can silently diverge.** A
  clean one-shot `-u module -d db --stop-after-init` proves nothing about what the browser-facing
  process actually loads if its own config file has a stale or missing path. Verify both separately
  (findings §4).
- **Restored databases carry orphaned `ir.ui.view` rows from modules no longer in the addons path.**
  These fail upgrades even when your current XML is correct. Audit before the first upgrade, not
  after chasing a phantom XML bug (findings §5).
- **A real customer database has modules with no Odoo 20 source at all — expected, not a bug.** Build
  a per-module disposition (port / disable-with-approval / remove-with-documented-cleanup) before
  declaring the database clean; "the target modules load" and "the database is clean" are different
  claims (findings §6).
- **A clean registry load is a technical milestone, not functional acceptance.** It says nothing
  about invoice totals, tax posting, payroll math, or POS sync — require representative business
  scenarios and expected totals from the Odoo 19 reference before calling a module migrated.
- **Some Odoo 20 breakage only exists in the browser.** Removed OWL static component metadata (e.g.
  a Kanban quick-create's static `props`) and renamed QWeb template-inheritance parents (e.g.
  `hr_holidays.CalendarController` -> `web.CalendarController`) produce zero server warning, zero
  upgrade error, zero HTTP failure — just a blank screen or a JS exception. Open every migrated
  screen in a real browser; a green registry load and schema gate are not sufficient (findings §11).
- **A sanitized reference database and its filestore can have their own gaps, separate from the code
  port.** No working admin login (`res.users.group_ids`, not `groups_id`, on Odoo 20), and individual
  `ir.attachment` rows pointing at filestore objects that were never actually restored (a missing app
  icon, here) are both real examples. Verify a real login and a sample of attachments resolve, don't
  just confirm the restore command exited 0 (findings §12).
- **More removed/renamed APIs found porting `maxdooctb_ao`** (findings §13, with working fixes):
  `Query` moved from `odoo.tools` to `odoo.models`; `content_disposition` moved from `odoo.http` to
  `odoo.http.stream`; `res.bank` removed from base entirely (needs a small local compat model);
  `res.company.company_registry` removed (redeclare it locally); `account.report.filter_analytic`
  merged into `filter_analytic_groupby`; `account.report.line.foldable` (Boolean) replaced by
  `foldability` (Selection) — official script exists but only converts the first duplicate per record;
  `account.report.column` now has a real unique `(report_id, expression_label)` DB constraint;
  `ir.actions.report.report_file` removed (usually a redundant duplicate of `report_name`); and a
  genuinely pre-existing data bug where multi-line `engine="domain"` formulas with trailing whitespace
  break Odoo 20's stricter `ast.literal_eval`-based formula validation even though Odoo 19 never
  caught it.

## 4. Verified Odoo 20 porting facts (from the web_responsive port; they win over the guide)

- Official helper: `odoo-bin upgrade_code --script owl3-migration --addons-path <wrapper dir> --glob '<module>/**/*'`
  (`--dry-run` first). Run it **as your own user**. Do not use `--from 19.0` (`19.3-00-account-groups.py` crashes);
  run `19.1-00-t-call`, `19.4-00-ir-access`, `owl3-migration` individually.
- **Review its output.** It imports `useRef`/`useExternalListener` from `@web/owl2/utils` (undefined at runtime),
  emits unused `t-custom-ref`, adds `this.` to `t-as` loop variables in some templates (wrong), swaps
  `useService("ui"/"action")` for plugins (unneeded), **strips XML copyright header comments** (restore them) and
  skips inherit-only templates (hand-convert bare expressions to `this.x`).
- Hand rules: `useState` -> `proxy`; refs -> `x = signal.ref()` + `t-ref="this.x"` read as `this.x()`;
  `useExternalListener` -> `useListener` (from `@odoo/owl`); `t-slot` -> `t-call-slot`.
- **FontAwesome CSS is gone:** use `<i class="oi oi-fw" data-icon="...">` with names already used in core (the
  guide's `<i class="oi" data-icon="check"/>` example omits `oi-fw`; verify the glyph in a browser).
- **QUnit is removed:** Hoot - bundle `web.assets_unit_tests`, files `*.test.js`, `defineMailModels()` for mail
  dependents, run at `/web/tests?headless=1&filter=...`.
- Web-client changes seen: `web.ListView.EditableButtons` merged into `web.ListView.Buttons`;
  `web.FormView.Buttons` holds only "New" (save/discard in `web.FormStatusIndicator`); Chatter moved to
  `@mail/chatter/web_portal_project/chatter`.
- Server: default `http_interface` is `127.0.0.1` (set `0.0.0.0` in containers); `--without-demo=all` warns
  (invalid boolean, treated true); an addons dir with no module is silently skipped from `addons_path`; the Odoo 20
  test env (`BaseCommon`) is not admin - `.sudo()` when creating `ir.actions.*`.
- Compatibility bridge (`$ODOO20_ROOT/odoo/addons/web/static/src/owl2/owl3_compatibility_layer.js`) is a staging
  tool, never the target.

## 5. Test-rig gotchas

- **Full vs. targeted upgrade timing** (calibrate expectations): a full custom-module upgrade took
  ~239s on a zero-worker local instance; a narrowly targeted one- or two-module upgrade took ~17-26s.
  Use targeted upgrades while iterating; save full upgrades for phase/gate boundaries, or the round
  trip will dominate your session.
- Assets are cached as `ir_attachment` (`url like '/web/assets/%'`): after editing static files delete them and
  restart, or you test stale JS.
- Odoo 20 keeps a websocket open: Playwright `networkidle` never fires - wait for `.o_main_navbar`.
- `pkill -f "http-port=NNNN"` matches its own shell; use `sudo pkill -f "[h]ttp-port=NNNN"` in a separate command.
- One-off `-i/-u` against a DB that a multi-worker server also serves can hit Odoo's deliberate 15 s lock timeout:
  check `pg_stat_activity`, then retry; never patch the timeout.

## 6. Deliverables per migrated module (put in the PR)

Static-scan before/after counts, the manifest version change, install-from-empty and upgrade logs (`Modules loaded`,
`Registry loaded`, no `UndefinedColumn`), the changed columns **and constraints** from
`information_schema.columns`/`pg_constraint` (don't just check columns — §3's `_sql_constraints`
finding is exactly a constraint that "loads clean" while silently missing), Python/Hoot/browser test
results, the risk-register rows (guide 16) marked done, and any item skipped with the reason. If the
module touches HR/payroll, external modules, or a restored reference database, also state: the
disposition of any Odoo-19-only dependency it needs (ported/disabled/removed, findings §6), and
whether the target database still has orphaned view records from modules outside the current addons
path (findings §5). Report failures with their output; do not claim a module "ported" from a clean
install alone — a clean registry load is not functional acceptance (findings §8, lesson 10).
