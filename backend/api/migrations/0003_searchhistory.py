from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_merge_members_into_accounts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.CharField(max_length=500)),
                ("audience_level", models.CharField(max_length=20)),
                ("response_type", models.CharField(default="answered", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(db_column="user_id", on_delete=models.deletion.CASCADE, related_name="search_histories", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "search_history",
                "ordering": ["-created_at", "-id"],
                "indexes": [models.Index(fields=["user", "created_at"], name="search_hist_user_created_idx")],
            },
        ),
    ]
