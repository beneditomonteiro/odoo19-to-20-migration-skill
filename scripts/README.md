# Migration scripts

These scripts are copied from the migration skill and are intended to run against disposable copies or
source trees. Most scripts are read-only by default. Scripts that write database or source changes require
an explicit `--apply` or are clearly named as fixers.

Before running them:

1. use a disposable database;
2. set `ODOO20_SRC` or pass explicit addon roots;
3. review the diff/output;
4. run the relevant schema, registry, and browser gates afterward.

Never place a password directly in shell history or a committed command. The legacy helper interfaces accept
password arguments for compatibility; prefer a protected environment or secret store when adapting them.
