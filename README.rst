SQL Multiplexer for SENAITE
===========================

.. image:: https://img.shields.io/pypi/v/senaite.sqlmultiplex.svg?style=flat-square
   :target: https://pypi.python.org/pypi/senaite.sqlmultiplex

.. image:: https://img.shields.io/github/issues-pr/senaite/senaite.sqlmultiplex.svg?style=flat-square
   :target: https://github.com/senaite/senaite.sqlmultiplex/pulls

.. image:: https://img.shields.io/github/issues/senaite/senaite.sqlmultiplex.svg?style=flat-square
   :target: https://github.com/senaite/senaite.sqlmultiplex/issues

.. image:: https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square
   :target: https://github.com/senaite/senaite.sqlmultiplex

.. image:: https://img.shields.io/badge/Made%20for%20SENAITE-%E2%AC%A1-lightgrey.svg
   :target: https://www.senaite.com


About
-----

SENAITE.SQLMULTIPLEX mirrors SENAITE content into a PostgreSQL database,
e.g. for reporting with Metabase, Grafana or plain SQL.

Which objects end up in which table is decided by `ISQLRow` adapters
provided by other add-ons. Without an adapter, nothing is mirrored.

Version 2.0 is under development and not released yet.


How it works
------------

The multiplexer is a queue processor of the portal catalog. Whenever an
object is indexed, reindexed or unindexed, its `ISQLRow` adapters are
looked up and their rows are written to PostgreSQL.

- One connection per thread, one PostgreSQL transaction per ZODB
  transaction. Rows are committed after the ZODB commit succeeded and
  rolled back when it failed, so the database never holds rows of an
  aborted transaction.
- Tables and missing columns are created on the first write. Existing
  columns are never changed or dropped.
- Database errors do not break SENAITE. A rejected row is logged and
  skipped, the other rows of the transaction are kept (one savepoint per
  row). If the commit fails after the ZODB commit, the rows of that
  transaction are missing in PostgreSQL and the error is logged.


Writing a row adapter
---------------------

Subclass `senaite.sqlmultiplex.row.SQLRow`, define the table and the
columns, and provide one getter per column::

    from bika.lims import api
    from senaite.sqlmultiplex.row import SQLRow


    class SampleRow(SQLRow):
        table = "sample"
        columns = (
            ("uid", "varchar(32)"),
            ("sample_id", "text"),
            ("state", "text"),
            ("created", "timestamptz"),
        )

        def applies(self):
            # objects that do not apply are removed from the table
            return api.get_review_status(self.context) != "invalid"

        def get_sample_id(self):
            return api.get_id(self.context)

        def get_state(self):
            return api.get_review_status(self.context)

        def get_created(self):
            return api.get_creation_date(self.context).asdatetime()

Register it for the content interface::

    <adapter
        for="bika.lims.interfaces.IAnalysisRequest"
        factory=".rows.SampleRow"
        name="myaddon.sample" />

Several named adapters for the same object write into several tables.
Values of `json`/`jsonb` columns may be dicts or lists.

An optional `descriptions` dict (column name to text) is written as
column comment when a column is created. Reporting tools such as
Metabase show it as field description.


Configuration
-------------

Install the add-on and enable the multiplexer in the control panel
("SQL Multiplex settings").

The connection string is read from the environment variable
`SENAITE_SQLMULTIPLEX_DSN`, e.g. in the buildout instance section::

    environment-vars =
        SENAITE_SQLMULTIPLEX_DSN host=localhost dbname=senaite user=senaite password=secret

If the variable is not set, the connection string of the control panel is
used. That one is stored in the ZODB in plain text.

Each Zope thread opens one connection. Plan `max_connections` of the
server accordingly (instances x threads, plus other clients).


Resync
------

Objects are written when they are saved. To fill a new database, or to
repair rows after a failed commit, write the rows of existing objects
with the instance command `sqlmultiplex_resync`::

    bin/instance sqlmultiplex_resync -s senaite \
        -c senaite_catalog_analysis -t Analysis

Options: `-s` site id, `-c` catalog (required), `-t` portal type
(repeatable), `-b` objects per batch (default 200), `-p` seconds to
sleep between batches, `--after` UID to resume an interrupted run.

The resync is safe to run next to live instances:

- It is a separate process (a ZEO client) and uses no request threads
  of the instances. On a busy server start it with `nice -n 19` and a
  pause, e.g. `-p 0.5`.
- It only reads from the ZODB. After every batch it commits the rows
  and ends the ZODB transaction, so each batch reads the current
  state: an object changed during the run is not written from an old
  snapshot.
- Small batches keep the PostgreSQL row locks short. A live save of
  the same object waits until the batch is committed at most.
- Batches are taken in UID order, each one after the last UID of the
  previous batch. Objects added or deleted during the run do not shift
  the batches (new objects are written by the multiplexer anyway).
- An interrupted run keeps the committed batches. The log shows the
  UID to continue with, `--after` resumes there.

Other add-ons can run the resync batch by batch themselves, e.g. from
a view that a browser calls repeatedly: `resync.resync_batch` writes
and commits one batch and returns the UID to continue after.

With a FileStorage instead of ZEO the database is locked by the
running instance; stop it before the resync.


MySQL
-----

Version 1.x targeted MySQL. Version 2.0 supports PostgreSQL only. The
connector is a named `ISQLConnector` utility, selected in the control
panel, so a MySQL connector can be added later without changes to the
processor or the row adapters.


Running the tests
-----------------

The connector tests that need a database are skipped unless
`SENAITE_SQLMULTIPLEX_TEST_DSN` points to a PostgreSQL database::

    createdb sqlmultiplex_test
    SENAITE_SQLMULTIPLEX_TEST_DSN="dbname=sqlmultiplex_test" bin/test -s senaite.sqlmultiplex


Feedback and support
--------------------

* `Community site <https://community.senaite.org/>`_
* `Gitter channel <https://gitter.im/senaite/Lobby>`_
* `Users list <https://sourceforge.net/projects/senaite/lists/senaite-users>`_


License
-------

**SENAITE.sqlmultiplex** Copyright (C) 2020-2026 RIDING BYTES & NARALABS

This program is free software; you can redistribute it and/or modify it under
the terms of the `GNU General Public License version 2
<https://github.com/senaite/senaite.sqlmultiplex/blob/master/LICENSE>`_ as published
by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
