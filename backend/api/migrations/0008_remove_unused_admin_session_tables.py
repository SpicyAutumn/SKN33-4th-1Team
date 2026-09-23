from django.db import migrations


class Migration(migrations.Migration):
    """Built-in admin/session apps are disabled; service auth_sessions remains."""

    dependencies = [("api", "0007_remove_error_report_category")]

    operations = [
        migrations.RunSQL("DROP TABLE IF EXISTS django_admin_log"),
        migrations.RunSQL("DROP TABLE IF EXISTS django_session"),
    ]
