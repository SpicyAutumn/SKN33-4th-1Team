from django.db import migrations


class Migration(migrations.Migration):
    """Remove v0 tables after their data has been copied into the v1 schema."""

    dependencies = [("api", "0004_service_v1_mysql")]

    operations = [
        migrations.DeleteModel(name="SearchHistory"),
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS accounts_user",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
