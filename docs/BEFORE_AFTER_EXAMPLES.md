# Odoo 19 → Odoo 20 before-and-after examples

These examples show the shape of a migration change. They use generic model names and deliberately small
snippets so they can be adapted without exposing project code. The left side is a legacy pattern that may be
present in Odoo 19 custom code; it is not a claim that every standard Odoo 19 module uses it. They are teaching
examples, not drop-in replacements: confirm the exact Odoo 20 signature, import, field, and owning module in
the target source.

The important lesson is that a replacement string is not a migration proof. Every example ends with the
check that should be performed after the code or data change.

## 1. SQL constraints

### Odoo 19 legacy source pattern

```python
class CatalogItem(models.Model):
    _name = "training.catalog.item"

    code = fields.Char(required=True)

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "The code must be unique."),
    ]
```

### Odoo 20 target pattern

```python
class CatalogItem(models.Model):
    _name = "training.catalog.item"

    code = fields.Char(required=True)

    _code_unique = models.Constraint(
        "UNIQUE(code)",
        "The code must be unique.",
    )
```

### Why this is not only a rename

An old declaration may be accepted with a warning while the PostgreSQL constraint is absent. After the
upgrade, query `pg_constraint` and attempt a duplicate create/write in a disposable database. A clean
registry log alone is insufficient.

## 2. SQL-backed or report models

### Odoo 19 legacy source pattern

```python
class ItemSummary(models.Model):
    _name = "training.item.summary"
    _description = "Item summary"
    _auto = False

    item_id = fields.Many2one("training.catalog.item")
    total = fields.Integer()

    _table_query = """
        SELECT item.id AS id,
               item.id AS item_id,
               COUNT(line.id) AS total
          FROM training_catalog_item item
          LEFT JOIN training_item_line line ON line.item_id = item.id
         GROUP BY item.id
    """
```

### Odoo 20 target pattern

```python
from odoo.tools import SQL


class ItemSummary(models.Model):
    _name = "training.item.summary"
    _description = "Item summary"
    _auto = False

    item_id = fields.Many2one("training.catalog.item")
    total = fields.Integer()

    @property
    def _table_sql(self):
        return SQL(
            """
                SELECT item.id AS id,
                       item.id AS item_id,
                       COUNT(line.id) AS total
                  FROM training_catalog_item item
                  LEFT JOIN training_item_line line ON line.item_id = item.id
                 GROUP BY item.id
            """
        )
```

For a model that is only a registry placeholder, the target may instead need a safe empty relation such as
`_table_sql = SQL("(0)")`. For a real report, rebuild the query from the Odoo 20 SQL/query API and verify
every selected column, alias, join, and record rule.

### Proof

Load the registry, query the model, render its list/report view, and compare the returned columns and totals
with the Odoo 19 reference. Do not copy a query unchanged merely because it is valid SQL.

## 3. Access rights and record rules

### Odoo 19 legacy source pattern

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_item_user,item user,model_training_catalog_item,base.group_user,1,1,1,0
```

### Odoo 20 target concept

Odoo 20 represents access as operation rows. The source-to-target mapping must preserve the effective
permission and domain, rather than mechanically copying the old CSV columns:

```xml
<record id="access_item_user_read" model="ir.access">
    <field name="model_id" ref="model_training_catalog_item"/>
    <field name="group_id" ref="base.group_user"/>
    <field name="permission">r</field>
</record>
<record id="access_item_user_write" model="ir.access">
    <field name="model_id" ref="model_training_catalog_item"/>
    <field name="group_id" ref="base.group_user"/>
    <field name="permission">u</field>
</record>
```

The exact target data format must be checked in the installed Odoo 20 security model. A grouped Odoo 19
record rule can be restrictive while a naïve target permission row is permissive. Map each rule as either a
permission or a restriction and test with a non-administrator user.

### Proof

Compare effective create/read/write/delete behavior, domains, group membership, multi-company visibility, and
related-record reads. Include a negative test for an operation that must remain forbidden.

## 4. View modifiers and list tags

### Odoo 19 legacy source pattern

```xml
<tree string="Items">
    <field name="name"/>
    <field name="amount"
           attrs="{'invisible': [('state', '!=', 'draft')]}"/>
</tree>
```

### Odoo 20 target pattern

```xml
<list string="Items">
    <field name="name"/>
    <field name="amount" invisible="state != 'draft'"/>
</list>
```

The same conversion applies to button and field `states` behavior, but the expression must use fields that
exist in the target model. Verify operator precedence and test every state; do not perform a blind textual
conversion of complex domains.

### Proof

Load the complete inherited view tree on an empty target database, then open the form/list as a user who can
see each relevant state. Check that the field is hidden, readonly, required, or enabled exactly as intended.

## 5. QWeb output and Owl slots

### Odoo 19 legacy source pattern

```xml
<span t-esc="record.name"/>
<t t-slot="header"/>
```

### Odoo 20 target pattern

```xml
<span t-out="record.name"/>
<t t-call-slot="header"/>
```

`t-out` is not safe for every object that an older `t-esc` expression happened to stringify. Normalize the
value in Python or explicitly convert it when the value may be a record, mapping, or other object.

### Proof

Render scalar, empty, translated, HTML, report, mail, and portal values. Check escaping and ensure that an
object is not accidentally rendered as an unsafe string.

## 6. Owl state and props

### Odoo 19 legacy source pattern

```javascript
import { Component, useState } from "@odoo/owl";

export class Counter extends Component {
    static template = "training.Counter";
    static props = { initial: Number };

    setup() {
        this.state = useState({ value: this.props.initial });
    }

    increment() {
        this.state.value += 1;
    }
}
```

### Odoo 20 target pattern

```javascript
import { Component, props as defineProps, proxy } from "@odoo/owl";

export class Counter extends Component {
    static template = "training.Counter";
    props = defineProps({ initial: Number });

    setup() {
        this.state = proxy({ value: this.props.initial });
    }

    increment() {
        this.state.value += 1;
    }
}
```

The exact props type syntax can vary with the Owl build bundled by Odoo. Use the helper and type syntax present
in the target source. The migration requirement is explicit props handling and proxy/signal-based state, not a
guessed import path.

### Related template change

```xml
<!-- Odoo 19 -->
<span t-esc="state.value"/>

<!-- Odoo 20 -->
<span t-out="this.state.value"/>
```

### Proof

Open the component in a real browser, click the state-changing action, pass valid and invalid props, and
check the browser console. A server registry test cannot detect most Owl failures.

## 7. Moved imports and changed return shapes

### Imports

```python
# Odoo 19
from odoo.tools import Query
from odoo.http import content_disposition

# Odoo 20
from odoo.models import Query
from odoo.http.stream import content_disposition
```

These imports must be checked against the target source because moving a symbol can also mean that its
signature or lifecycle changed.

### Record-like result to dictionary result

```python
# Odoo 19
seller = product._select_seller(quantity=quantity)
price = seller.price
seller_uom = seller.uom_id

# Odoo 20
seller = product._select_seller(quantity=quantity)
price = seller["price"]
seller_uom = seller["uom_id"]
```

Use the dictionary keys supplied by the target implementation and keep a test for the no-seller case.

### Proof

Run the import checker, exercise the runtime path, and test the result shape with a real record and an empty
selection. Static import success is not enough when a method's return contract changed.

## 8. Typed configuration parameters

### Odoo 19 legacy source pattern

```python
params = self.env["ir.config_parameter"].sudo()
enabled = params.get_param("training.feature_enabled") == "True"
limit = int(params.get_param("training.batch_limit", "50"))
```

### Odoo 20 target pattern

```python
params = self.env["ir.config_parameter"].sudo()
enabled = params.get_bool("training.feature_enabled", default=False)
limit = params.get_int("training.batch_limit", default=50)
```

Choose the getter from the business type, not from the parameter name. Update defaults, XML data, validation,
and callers together.

### Proof

Test missing, empty, false, true, malformed, and boundary values. Verify the stored value and the effective
Python type in the target database.

## 9. Binary attachments

### Odoo 19 legacy source pattern

```python
import base64

payload = base64.b64decode(attachment.datas or b"")
```

### Odoo 20 target pattern

```python
value = attachment.raw
payload = value.content if hasattr(value, "content") else value
```

The target API may return raw bytes or a `BinaryValue`-style wrapper depending on the access path. Do not
decode twice and do not assume an RPC value has the same representation as a server-side ORM read.

### Proof

Upload a file, read it through the ORM, fetch it through RPC, download it through HTTP, and verify the
filestore object, filename, content type, and byte-for-byte content.

## 10. Removed or replaced models are data migrations

### Odoo 19 legacy source pattern

```python
leave_types = self.env["hr.leave.type"].search([])
for leave_type in leave_types:
    self._create_work_entry_type(leave_type.name)
```

### Odoo 20 target pattern

```python
mapping = self._build_leave_type_to_work_entry_type_map()
for old_id, new_id in mapping.items():
    self._relink_xmlid_and_foreign_keys(old_id, new_id)
```

The second snippet is intentionally a migration skeleton. A removed model cannot be handled by changing one
string: map XML IDs, foreign keys, views, reports, and business meaning idempotently. Preserve the old-to-new
map as an auditable artifact.

### Proof

Verify the target registry, XML-ID ownership, foreign-key columns, populated records, and one complete
business workflow that uses the replacement model.

## 11. Example review record

For each ported artifact, keep a short record like this:

```text
Artifact: unique code constraint
Odoo 19: _sql_constraints declaration
Odoo 20: models.Constraint declaration
Source proof: static scan found the old declaration
Target proof: pg_constraint contains the expected rule
Behavior proof: duplicate create is rejected
Browser/business proof: item creation and search still work
Status: complete / deferred / blocked with reason
```

The record connects the before/after code to database and business evidence. That is what makes an example a
migration method rather than a syntax cheat sheet.

## Sources and limits

- Check the Odoo 20 source tree that will actually run the module before copying any snippet.
- For Owl-specific changes, consult the [official Owl 2 → Owl 3 migration guide](https://github.com/odoo/owl/blob/master/doc/v3/owl/migration_owl2_to_owl3.md).
- Use [`CORE_ARTIFACTS.md`](CORE_ARTIFACTS.md) for the artifact matrix and [`MIGRATION_PROBLEMS.md`](MIGRATION_PROBLEMS.md)
  for the observed failure/proof catalog.
