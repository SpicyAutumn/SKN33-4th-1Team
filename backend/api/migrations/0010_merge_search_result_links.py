from django.db import migrations


class Migration(migrations.Migration):
    """Join already-applied cleanup and result-link histories without rewriting either."""

    dependencies = [
        ("api", "0009_remove_unused_auth_tables"),
        ("api", "0006_search_result_links"),
    ]

    operations = []
