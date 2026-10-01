-- Odoo 19 -> 20 pre-migration for a RESTORED database: ir.model.access + ir.rule  ->  ir.access.
-- Odoo 20 core ships no migration for this (the hosted upgrade service does it). Without it `-u all` dies with
-- "For external id base.access_x ... found record of different model ir.model.access".
-- Run once, on a COPY, BEFORE the first Odoo 20 start. Semantics mirror the official 19.4-00-ir-access source script:
--   ir.model.access row            -> permission row (group, operation from perms, no domain)
--   ir.rule with groups            -> one permission row per group, with the rule domain
--   ir.rule global (no group)      -> restriction row (no group), with the rule domain
-- XML ids are moved to the new rows (first row keeps the id), so each module's new ir.access.csv updates them in place;
-- rows no module claims again are removed by Odoo at the end of the upgrade (verify with check_access_equivalence20.py).
BEGIN;
CREATE TABLE IF NOT EXISTS ir_access (
    id serial PRIMARY KEY,
    create_uid integer REFERENCES res_users(id) ON DELETE SET NULL,
    create_date timestamp, write_uid integer REFERENCES res_users(id) ON DELETE SET NULL, write_date timestamp,
    name varchar NOT NULL, active boolean, model_id integer NOT NULL REFERENCES ir_model(id) ON DELETE CASCADE,
    group_id integer REFERENCES res_groups(id) ON DELETE CASCADE, operation varchar NOT NULL, domain varchar);
CREATE INDEX IF NOT EXISTS ir_access_model_id_index ON ir_access(model_id);
CREATE INDEX IF NOT EXISTS ir_access_group_id_index ON ir_access(group_id);

CREATE TEMP TABLE _acc_map(old_model text, old_id int, new_id int);

-- 1. model access
WITH ins AS (
  INSERT INTO ir_access(create_uid, create_date, write_uid, write_date, name, active, model_id, group_id, operation, domain)
  SELECT create_uid, create_date, write_uid, write_date, coalesce(name, 'access ' || id), active, model_id, group_id,
         concat(CASE WHEN perm_create THEN 'c' END, CASE WHEN perm_read THEN 'r' END,
                CASE WHEN perm_write THEN 'u' END, CASE WHEN perm_unlink THEN 'd' END), NULL
  FROM ir_model_access
  WHERE perm_create OR perm_read OR perm_write OR perm_unlink
  ORDER BY id RETURNING id, name, model_id, group_id)
SELECT count(*) AS model_access_rows_converted FROM ins;

-- map old -> new for model access (same order of insertion)
INSERT INTO _acc_map
SELECT 'ir.model.access', o.id, n.id FROM
  (SELECT id, row_number() OVER (ORDER BY id) rn FROM ir_model_access WHERE perm_create OR perm_read OR perm_write OR perm_unlink) o
  JOIN (SELECT id, row_number() OVER (ORDER BY id) rn FROM ir_access ORDER BY id) n ON n.rn = o.rn;

-- 2. rules: one row per (rule, group) or a single group-less row
CREATE TEMP TABLE _rule_rows AS
SELECT r.id AS rule_id, g.group_id, coalesce(r.name, 'rule ' || r.id) AS name, r.active, r.model_id, r.domain_force,
       concat(CASE WHEN r.perm_create THEN 'c' END, CASE WHEN r.perm_read THEN 'r' END,
              CASE WHEN r.perm_write THEN 'u' END, CASE WHEN r.perm_unlink THEN 'd' END) AS op,
       r.create_uid, r.create_date, r.write_uid, r.write_date,
       row_number() OVER (PARTITION BY r.id ORDER BY g.group_id NULLS FIRST) AS nth
FROM ir_rule r LEFT JOIN rule_group_rel g ON g.rule_group_id = r.id
WHERE r.perm_create OR r.perm_read OR r.perm_write OR r.perm_unlink;

CREATE TEMP TABLE _rule_new AS
WITH ins AS (
  INSERT INTO ir_access(create_uid, create_date, write_uid, write_date, name, active, model_id, group_id, operation, domain)
  SELECT create_uid, create_date, write_uid, write_date, name, active, model_id, group_id, op, domain_force
  FROM _rule_rows ORDER BY rule_id, nth RETURNING id)
SELECT id FROM ins;

INSERT INTO _acc_map
SELECT 'ir.rule', rr.rule_id, rr.new_id FROM (
  SELECT a.rule_id, a.nth, n.id AS new_id FROM
    (SELECT rule_id, nth, row_number() OVER (ORDER BY rule_id, nth) rn FROM _rule_rows) a
    JOIN (SELECT id, row_number() OVER (ORDER BY id) rn FROM _rule_new) n ON n.rn = a.rn) rr WHERE rr.nth = 1;

-- 3. move the XML ids to the new rows (rows without a mapping lose their id: they had no permission at all)
UPDATE ir_model_data d SET model = 'ir.access', res_id = m.new_id
FROM _acc_map m WHERE d.model = m.old_model AND d.res_id = m.old_id;
DELETE FROM ir_model_data WHERE model IN ('ir.model.access', 'ir.rule');
SELECT (SELECT count(*) FROM ir_access) AS ir_access_rows, (SELECT count(*) FROM ir_model_data WHERE model='ir.access') AS with_xmlid;
COMMIT;
