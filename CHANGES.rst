Changelog
=========

2.0.0 (unreleased)
------------------

- PostgreSQL via psycopg2 instead of MySQL. MySQL can come back as a
  further named `ISQLConnector` utility
- Explicit `ISQLRow` adapters instead of mirroring all fields as varchar
- One connection per thread, one database transaction per ZODB
  transaction, committed after the ZODB commit
- Rejected rows are logged and skipped (savepoint per row)
- Connection string from the environment variable
  `SENAITE_SQLMULTIPLEX_DSN`, registry as fallback
- Instance command `sqlmultiplex_resync` writes the rows of existing
  objects in batches, safe to run next to live instances


1.0.0 (unreleased)
------------------

- First version
