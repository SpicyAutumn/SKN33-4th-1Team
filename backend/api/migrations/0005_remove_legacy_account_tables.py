from django.db import migrations


def _quote(identifier):
    return "`" + identifier.replace("`", "``") + "`"


def remove_legacy_account_tables(_apps, schema_editor):
    """Drop v0 tables in dependency order and tolerate a prior failed attempt."""
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        # This table may already have been dropped before a failed migration
        # reached accounts_user. IF EXISTS makes retrying the migration safe.
        cursor.execute("DROP TABLE IF EXISTS `search_history`")

        cursor.execute(
            """
            SELECT TABLE_NAME, CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_SCHEMA = DATABASE()
              AND REFERENCED_TABLE_NAME = 'accounts_user'
              AND CONSTRAINT_NAME IS NOT NULL
            """
        )
        references = cursor.fetchall()
        join_tables = {"accounts_user_groups", "accounts_user_user_permissions"}
        for table_name, constraint_name in references:
            if table_name in join_tables:
                cursor.execute(f"DROP TABLE IF EXISTS {_quote(table_name)}")
            else:
                # Keep unrelated tables such as an old admin log, but remove
                # only their obsolete foreign-key relationship.
                cursor.execute(
                    f"ALTER TABLE {_quote(table_name)} DROP FOREIGN KEY {_quote(constraint_name)}"
                )

        cursor.execute("DROP TABLE IF EXISTS `accounts_user`")


class Migration(migrations.Migration):
    """Remove v0 tables after their data has been copied into the v1 schema."""

    dependencies = [("api", "0004_service_v1_mysql")]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="SearchHistory")],
        ),
        migrations.RunPython(remove_legacy_account_tables, migrations.RunPython.noop),
    ]
