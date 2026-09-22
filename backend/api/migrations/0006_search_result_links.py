import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("api", "0005_remove_legacy_account_tables")]
    operations = [migrations.CreateModel(
        name="SearchResult",
        fields=[
            ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
            ("guest_token_hash", models.CharField(max_length=64, blank=True, default="")),
            ("payload", models.JSONField(default=dict)),
            ("share_token", models.UUIDField(null=True, blank=True, unique=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("owner", models.ForeignKey(to="api.serviceuser", null=True, blank=True, on_delete=django.db.models.deletion.CASCADE)),
        ],
        options={"db_table": "search_results"},
    )]
