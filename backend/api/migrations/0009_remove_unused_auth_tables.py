from django.db import migrations


class Migration(migrations.Migration):
    """Remove disabled Django auth metadata in foreign-key dependency order.

    Service users and sessions are independent of these tables. The auth and
    contenttypes apps must stay disabled so post_migrate cannot recreate them.
    Old django_migrations entries are retained as historical records.
    """

    dependencies = [("api", "0008_remove_unused_admin_session_tables")]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS auth_group_permissions"),
        migrations.RunSQL("DROP TABLE IF EXISTS auth_permission"),
        migrations.RunSQL("DROP TABLE IF EXISTS auth_group"),
        migrations.RunSQL("DROP TABLE IF EXISTS django_content_type"),
    ]
