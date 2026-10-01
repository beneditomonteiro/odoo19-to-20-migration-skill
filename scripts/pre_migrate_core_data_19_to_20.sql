-- Odoo 19 -> 20 pre-migration for a RESTORED database: core data conventions that changed. Run after
-- pre_migrate_ir_access_19_to_20.sql, on a COPY, before the first Odoo 20 start.
BEGIN;
-- ir.model.fields.index: Odoo 19 stored 'true'/'false'; Odoo 20 stores 'btree'/'btree_not_null'/'trigram' or NULL.
-- Left as is it fails registry setup: AssertionError in check_indexes.
UPDATE ir_model_fields SET index = 'btree' WHERE index = 'true';
UPDATE ir_model_fields SET index = NULL   WHERE index IN ('false', '');
-- Country states whose XML id was renamed by Odoo 20 while (country, code) stayed: relink, or the base CSV load fails with
-- "The code of the state must be unique by country!" (found: base.state_in_or -> base.state_in_od, Odisha).
UPDATE ir_model_data SET name = 'state_in_od'
 WHERE module='base' AND model='res.country.state' AND name='state_in_or'
   AND NOT EXISTS (SELECT 1 FROM ir_model_data x WHERE x.module='base' AND x.name='state_in_od');
COMMIT;

-- STALE VIEWS of standard modules (run with :std_modules = comma list of quoted module names that have an Odoo 20 source).
-- Odoo 20 validates the whole view tree while `base` loads, against child views still carrying Odoo 19 arch, and never rewrites
-- a view record whose XML id is noupdate, nor clears an inherit_id the new XML no longer sets.
--   psql -v std_modules="'base','mail',..." -f pre_migrate_core_data_19_to_20.sql
BEGIN;
UPDATE ir_model_data SET noupdate = false WHERE model = 'ir.ui.view' AND noupdate AND module IN (:std_modules);
CREATE TABLE IF NOT EXISTS migration_deactivated_views(id int PRIMARY KEY);
-- 1. park every EXTENSION view of a standard module (re-activated after the upgrade, see POST step in the procedure)
INSERT INTO migration_deactivated_views
  SELECT v.id FROM ir_ui_view v JOIN ir_model_data d ON d.res_id = v.id AND d.model = 'ir.ui.view'
  WHERE v.inherit_id IS NOT NULL AND v.active AND d.module IN (:std_modules) ON CONFLICT DO NOTHING;
UPDATE ir_ui_view SET active = false WHERE id IN (SELECT id FROM migration_deactivated_views);
-- 2. forget stale parents: every view record re-sets inherit_id and mode from its own XML when its module loads
UPDATE ir_ui_view v SET inherit_id = NULL, mode = 'primary'
  FROM ir_model_data d WHERE d.res_id = v.id AND d.model = 'ir.ui.view' AND d.module IN (:std_modules) AND v.inherit_id IS NOT NULL;
COMMIT;
-- POST (after `-u all` succeeded):  UPDATE ir_ui_view SET active = true WHERE id IN (SELECT id FROM migration_deactivated_views);
--   then run `-u all` once more: it validates the re-activated views against the new models; deactivate (and fix) any that fail.

-- hr.contract.type was REPLACED by hr.employee.type in Odoo 20 (the Selection hr.version.employee_type merged into it as records).
-- Rename table/model/xml-id models/columns so hr's data files (hr_employee_type_data.xml) find the records as hr.employee.type.
-- Left alone the load dies with KeyError: 'hr.contract.type' (ir_model_data rows of a model no longer in the registry).
-- NOT converted: the old Selection hr_version.employee_type values (kept as an orphan column), AO extension columns on the table.
BEGIN;
ALTER TABLE IF EXISTS hr_contract_type RENAME TO hr_employee_type;
ALTER SEQUENCE IF EXISTS hr_contract_type_id_seq RENAME TO hr_employee_type_id_seq;
UPDATE ir_model SET model = 'hr.employee.type' WHERE model = 'hr.contract.type';
UPDATE ir_model_fields SET model = 'hr.employee.type' WHERE model = 'hr.contract.type';
UPDATE ir_model_fields SET relation = 'hr.employee.type' WHERE relation = 'hr.contract.type';
UPDATE ir_model_data SET model = 'hr.employee.type' WHERE model = 'hr.contract.type';
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='hr_version' AND column_name='contract_type_id')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='hr_version' AND column_name='employee_type_id') THEN
    ALTER TABLE hr_version RENAME COLUMN contract_type_id TO employee_type_id;
    UPDATE ir_model_fields SET name = 'employee_type_id' WHERE model = 'hr.version' AND name = 'contract_type_id';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='hr_job' AND column_name='contract_type_id')
     AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='hr_job' AND column_name='employee_type_id') THEN
    ALTER TABLE hr_job RENAME COLUMN contract_type_id TO employee_type_id;
    UPDATE ir_model_fields SET name = 'employee_type_id' WHERE model = 'hr.job' AND name = 'contract_type_id';
  END IF;
END $$;
COMMIT;

-- Enterprise approvals: approval_category.manager_approval was a Selection ('approver' | 'required' | empty), Odoo 20 makes it a Boolean
-- ("manager is a required approver"). 'approver' has no exact equivalent: mapped to true (stricter, no approval step is lost silently) - REVIEW.
BEGIN;
UPDATE approval_category SET manager_approval = CASE WHEN manager_approval IN ('approver', 'required') THEN 'true' ELSE 'false' END
 WHERE manager_approval IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='approval_category' AND column_name='manager_approval' AND data_type='character varying');
COMMIT;
