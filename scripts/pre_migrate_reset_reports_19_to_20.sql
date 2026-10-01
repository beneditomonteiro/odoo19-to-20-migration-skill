-- Odoo 19 -> 20 pre-migration for a RESTORED database: reset the STANDARD accounting report structure (account_reports).
-- Odoo 20 renamed many report line / expression XML ids inside the same module; the loader then re-creates them and hits the unique keys
-- (report_id, code) and (report_line_id, label). Delete standard-module lines/expressions/columns (and their XML ids): the XML recreates them.
-- Variable: std_modules = quoted modules with an Odoo 20 source. Custom (non-standard-module) report lines are kept.
BEGIN;
CREATE TEMP TABLE _l AS SELECT res_id AS id FROM ir_model_data WHERE model='account.report.line' AND module IN (:std_modules)
  AND res_id NOT IN (SELECT account_report_line_id FROM cash_flow_statement WHERE account_report_line_id IS NOT NULL);
DELETE FROM ir_model_data WHERE model='account.report.expression' AND module IN (:std_modules);
DELETE FROM account_report_expression WHERE report_line_id IN (SELECT id FROM _l) OR id NOT IN (SELECT res_id FROM ir_model_data WHERE model='account.report.expression') AND report_line_id IN (SELECT id FROM _l);
DELETE FROM ir_model_data WHERE model='account.report.line' AND res_id IN (SELECT id FROM _l);
DELETE FROM account_report_line WHERE id IN (SELECT id FROM _l);
CREATE TEMP TABLE _c AS SELECT res_id AS id FROM ir_model_data WHERE model='account.report.column' AND module IN (:std_modules);
DELETE FROM ir_model_data WHERE model='account.report.column' AND res_id IN (SELECT id FROM _c);
DELETE FROM account_report_column WHERE id IN (SELECT id FROM _c);
SELECT (SELECT count(*) FROM _l) AS lines_deleted, (SELECT count(*) FROM _c) AS columns_deleted,
       (SELECT count(*) FROM account_report_line) AS lines_left, (SELECT count(*) FROM account_report_expression) AS expr_left;
COMMIT;
