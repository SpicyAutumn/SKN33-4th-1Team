from django.db import migrations, models


def copy_legacy_categories(apps, _schema_editor):
    """Give existing single-type reports one row in the new type table."""
    ErrorReport = apps.get_model("api", "ErrorReport")
    ErrorReportType = apps.get_model("api", "ErrorReportType")
    for report in ErrorReport.objects.exclude(category="").iterator():
        ErrorReportType.objects.get_or_create(
            error_report_id=report.id,
            code=report.category,
        )


class Migration(migrations.Migration):
    dependencies = [("api", "0005_remove_legacy_account_tables")]

    operations = [
        migrations.CreateModel(
            name="ErrorReportQuote",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("ordinal", models.PositiveSmallIntegerField()),
                ("text", models.TextField()),
                ("start_offset", models.PositiveIntegerField(blank=True, null=True)),
                ("end_offset", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("error_report", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="selected_quotes", to="api.errorreport")),
            ],
            options={"db_table": "error_report_quotes", "ordering": ["ordinal"]},
        ),
        migrations.CreateModel(
            name="ErrorReportType",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("error_report", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="types", to="api.errorreport")),
            ],
            options={"db_table": "error_report_types", "ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="errorreportquote",
            constraint=models.UniqueConstraint(fields=("error_report", "ordinal"), name="error_report_quote_ordinal_uq"),
        ),
        migrations.AddConstraint(
            model_name="errorreporttype",
            constraint=models.UniqueConstraint(fields=("error_report", "code"), name="error_report_type_uq"),
        ),
        migrations.RunPython(copy_legacy_categories, migrations.RunPython.noop),
    ]
