# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.SQLMULTIPLEX.
#
# SENAITE.SQLMULTIPLEX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2020-2026 by it's authors.
# Some rights reserved, see README and LICENSE.

"""PostgreSQL statements

Pure functions that build psycopg2 SQL compositions. Identifiers are
always quoted, values are always passed as parameters.
"""

from psycopg2 import sql


def column_definition(name, sql_type, primary_key=False):
    """Returns the definition of a single column

    The SQL type comes from the adapter (code, not user input) and is
    inserted verbatim.
    """
    parts = [sql.Identifier(name), sql.SQL(sql_type)]
    if primary_key:
        parts.append(sql.SQL("PRIMARY KEY"))
    return sql.SQL(" ").join(parts)


def create_table(table, primary_key, columns):
    """Returns the statement to create the table if it does not exist

    :param columns: sequence of (column name, SQL type) tuples
    """
    definitions = [
        column_definition(name, sql_type, name == primary_key)
        for name, sql_type in columns
    ]
    return sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
        sql.Identifier(table), sql.SQL(", ").join(definitions))


def add_column(table, name, sql_type):
    """Returns the statement to add a column if it does not exist
    """
    return sql.SQL("ALTER TABLE {} ADD COLUMN IF NOT EXISTS {}").format(
        sql.Identifier(table), column_definition(name, sql_type))


def upsert(table, primary_key, names):
    """Returns the statement to insert or update a row

    Takes one parameter per column name, in the given order.
    """
    others = [name for name in names if name != primary_key]
    statement = sql.SQL("INSERT INTO {} ({}) VALUES ({}) ").format(
        sql.Identifier(table),
        sql.SQL(", ").join(map(sql.Identifier, names)),
        sql.SQL(", ").join(sql.Placeholder() * len(names)))
    if not others:
        conflict = sql.SQL("ON CONFLICT ({}) DO NOTHING").format(
            sql.Identifier(primary_key))
        return statement + conflict
    assignments = [
        sql.SQL("{} = EXCLUDED.{}").format(
            sql.Identifier(name), sql.Identifier(name))
        for name in others
    ]
    conflict = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {}").format(
        sql.Identifier(primary_key), sql.SQL(", ").join(assignments))
    return statement + conflict


def delete(table, primary_key):
    """Returns the statement to delete a row by primary key

    Takes the primary key value as the only parameter.
    """
    return sql.SQL("DELETE FROM {} WHERE {} = %s").format(
        sql.Identifier(table), sql.Identifier(primary_key))


def table_columns():
    """Returns the query for the column names of a table

    Takes the table name as the only parameter. Returns no rows if the
    table does not exist.
    """
    return sql.SQL(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s")
