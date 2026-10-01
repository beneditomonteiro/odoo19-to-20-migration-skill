---
name: odoo20-migration-process
description: >-
  Port Odoo 19 custom modules to Odoo 20 (Owl 3, new account-reports frontend, SQL/`_table_query`
  removal, `_sql_constraints` to `models.Constraint`, `hr.leave.type` removal, BinaryValue, XML
  modifiers, POS patches, assets/manifests) safely and in phases, on a disposable Odoo 20 database.
  Use when asked to migrate or port a module to Odoo 20, to make custom Odoo or OCA modules work on
  Odoo 20, to pick or sanitize a reference database for a
  migration, to run `upgrade_code` / the Owl 3 migration, to review a 19-to-20 diff, to debug an Odoo
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
2. `docs/MIGRATION_GUIDE.md` — the public core-artifact migration guide. It covers the static, unexecuted
   assessment: ORM/schema, database metadata, XML/data, views/QWeb, Owl/frontend, POS, assets, and proof
   gates. Every code skeleton in it is unverified — check it against the local Odoo 20 source before use.

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
2. **Odoo 20 runs only on its own stack.** Code, Enterprise addons, virtual environment, config,
   PostgreSQL cluster, HTTP port, filestore, and migrated databases must be isolated from Odoo 19.
   Restore a *copy* into the Odoo 20 cluster; never open an Odoo 19 database directly with Odoo 20.
   Use a protected password source for database commands (a bare `psql` may wait for a password).
3. **Do not port in place** in a shared Odoo 19 source tree. Work on your own branch
   `session-<model>-<YYYYMMDD>-<topic>`, in a dedicated Odoo 20 copy or worktree. Commit only your files by path and
   open the PR, then **stop and ask before merging** (merge only when the user asked for it), and stay
   on your branch afterwards; never touch another session's work.
4. Give the ported source tree and its eventual repository an unmistakable Odoo 20 name, such as
   `<project>_odoo20`. Keep technical module names stable when the upgrade path depends on them;
   the container/repository name and the module technical name are separate decisions.
5. **Schema is a release gate:** after any field change run `-u MODULE -d DB --stop-after-init`, verify the
   columns in `information_schema.columns`, `Modules loaded`/`Registry loaded`, no `UndefinedColumn`, and
   check that the module reached `installed` (an exit code 0 can hide skipped modules).
6. **Trust the local Odoo 20 source over the guide.** The guide's code blocks are skeletons ("not a drop-in
   replacement"). Before using one, open the Odoo 20 file that owns the behavior and read the current
   signature. Facts in section 3 below were verified on real Odoo 20 and override the guide where they differ.
7. Access-control default for new modules (privilege with User/Manager/Administrator roles) still applies to
   any *new* model/menu added during a port. Keep LGPL/OCA copyright headers when porting third-party code.
8. **Before hand-deriving a fix for any newly-hit Odoo 20 incompatibility, check in this order — don't
   write a bespoke fix first and check references later.**
   1. **Diff the Odoo 19 source against any already-ported sibling implementation**
      (`diff -rq --exclude=__pycache__ <repo19>/<module> <sibling>/<module>`)
      before assuming independent porting work is needed.
   2. **If a sibling tree already has an Odoo 20 "port" of the same file, verify it actually works
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
| Scope and inventory | 1-3 | — | Build the module, model, XML-ID, security, asset, and dependency inventory from the source |
| ORM, schema, database metadata | 4.1 | — | Rewrite declarations and prove columns, constraints, indexes, and ownership |
| XML/data, views, QWeb | 4.2-4.3 | — | Convert metadata and validate the complete view/data graph |
| Owl, account reports, POS, assets | 4.4 | — | Rebase frontend behavior on Odoo 20 source and browser-test it |
| Binary values and configuration | 4.5 | — | Verify bytes, filestore, typed parameters, cache, and live configuration |
| Static-first phases and commands | 5-6 | — | Complete source and disposable-database gates before release consideration |
| Definition of done | 7 | — | Use the proof checklist in the review |

## 2. The process (guide 14), condensed

This matches what was actually executed closely enough to keep following; step 0 in particular is
underspecified here — see the Gate G0 rule above and findings §1/§9 for the reference-database part
that this list glosses over as "back up source DB + filestore."

0. **Freeze and baseline** - dedicated Odoo 20 branch; record the Odoo 19 and Odoo 20 source revisions;
   back up source DB + filestore; export the manifest dependency inventory; record installed versions.
1. **Static inventory** - run `scripts/scan_odoo19_patterns.sh <root>`; classify each hit (JS module system,
   Owl 2, XML modifier, SQL/report, ORM, security, data migration, integration, performance); assign owner + test.
   Comments/docs/tests are false positives only after manual verification.
2. **Localization/foundation modules** - data, taxes, fiscal positions, journals, and sequences; verify
   posting, credit notes, refunds, reports, multi-company, and translations.
3. **Shared models** - partner/company extensions, mixins, access rules, views/menus, server and scheduled
   actions. Settle field renames, computes, constraints, and groups before frontend work.
4. **Accounting and reporting** - reports, assets, reconciliation, and financial data; rewrite the report
   frontend and `_table_query` models; compare totals with a fixed Odoo 19 reference dataset.
5. **Sales, stock, HR, payroll** - test workflows end to end (quotation -> delivery -> invoice -> credit note,
   valuation, time off, payslip, generated entries), not just installation.
6. **POS and integrations** - last: open/close, offline, payment retry, fiscal info, sync, duplicates, timeouts,
   secrets. (signing keys are not in the repo; never commit or move them.)
7. **Database migration** - only after clean installs: restore a *copy* into the isolated Odoo 20 cluster, run the supported
   upgrade path, upgrade custom modules, inspect changed columns, reconcile against Odoo 19 exports, test
   filestore/binaries, repeat on a fresh copy until deterministic.
8. **Acceptance and release** - install from empty DB, upgrade from migrated DB, Python + JS tests, browser tours,
   accounting/stock/HR reconciliation, security review with non-admin roles, performance smoke, backup/restore,
   log review with no unexplained traceback; then the guide's definition of done (17). Production only with the
   owner's explicit go and a rehearsal on a production backup.

## 3. Verified facts from an executed Odoo 19 → 20 migration (win over the guide and over §4)

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
- **More removed/renamed APIs found while porting custom modules** (findings §13, with working fixes):
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
