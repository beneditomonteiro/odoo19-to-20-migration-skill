-- Odoo 19 -> 20 pre-migration for a RESTORED database: reset the view tree so `base` can load.
-- Variables: std_modules = quoted names of installed modules that HAVE an Odoo 20 source in core/Enterprise;
--            gone_modules = quoted names of installed modules that have NO Odoo 20 source at all.
-- Why: Odoo 20 validates the combined arch of the tree while `base` loads (e.g. ir.cron form vs the server-action form) against
-- parents/children still carrying Odoo 19 arch; stale rows also survive when an XML id is noupdate or the new XML drops inherit_id.
-- What: kept views (modules ported by us) lose their parent link and are PARKED inactive (they re-set inherit_id/mode from their XML
-- when their module updates); standard-module views, views of modules that cannot load, and COW copies (no XML id) are deleted and
-- recreated from XML. Records are listed in migration_deactivated_views / logged: review them.
--   psql -v std_modules="'base',..." -v gone_modules="'max_x',..." -f pre_migrate_reset_views_19_to_20.sql
-- POST (after the first successful `-u all`): UPDATE ir_ui_view SET active = true WHERE id IN (SELECT id FROM migration_deactivated_views);
--   then `-u all` again and deactivate+fix any view that no longer validates.
BEGIN;
CREATE TABLE IF NOT EXISTS migration_deactivated_views(id int PRIMARY KEY);
CREATE TEMP TABLE _del AS
  SELECT v.id FROM ir_ui_view v
  WHERE NOT EXISTS (SELECT 1 FROM ir_model_data d WHERE d.res_id = v.id AND d.model = 'ir.ui.view')
     OR EXISTS (SELECT 1 FROM ir_model_data d WHERE d.res_id = v.id AND d.model = 'ir.ui.view' AND d.module IN (:std_modules, :gone_modules));
-- keep views still referenced through RESTRICT foreign keys (payment providers' forms, report layouts): they refresh on load
DELETE FROM _del WHERE id IN (
  SELECT token_inline_form_view_id FROM payment_provider UNION SELECT express_checkout_form_view_id FROM payment_provider
  UNION SELECT inline_form_view_id FROM payment_provider UNION SELECT redirect_form_view_id FROM payment_provider
  UNION SELECT view_id FROM report_layout);
INSERT INTO migration_deactivated_views SELECT id FROM ir_ui_view WHERE id NOT IN (SELECT id FROM _del) ON CONFLICT DO NOTHING;
UPDATE ir_ui_view SET inherit_id = NULL, mode = 'primary';
UPDATE ir_ui_view SET active = false WHERE id NOT IN (SELECT id FROM _del);
DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN (SELECT id FROM _del);
DELETE FROM ir_ui_view WHERE id IN (SELECT id FROM _del);
SELECT (SELECT count(*) FROM _del) AS deleted, (SELECT count(*) FROM migration_deactivated_views) AS parked;
COMMIT;
