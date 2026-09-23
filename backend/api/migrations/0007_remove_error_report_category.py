from django.db import migrations


def preserve_categories(apps, schema_editor):
    # Some cloned DBs already record 0006 as applied but contain only a subset
    # of its category rows. Reconcile before dropping the only remaining copy.
    Report = apps.get_model("api", "ErrorReport")
    Type = apps.get_model("api", "ErrorReportType")
    alias = schema_editor.connection.alias
    for report in Report.objects.using(alias).exclude(category="").iterator():
        Type.objects.using(alias).get_or_create(error_report_id=report.pk, code=report.category)


class Migration(migrations.Migration):
    """Use error_report_types exclusively; discard the redundant legacy value."""

    dependencies = [("api", "0006_error_report_multi_type_and_quotes")]

    operations = [
        migrations.RunPython(preserve_categories, migrations.RunPython.noop),
        migrations.RemoveField(model_name="errorreport", name="category"),
    ]
