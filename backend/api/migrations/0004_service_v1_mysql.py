import uuid

from django.db import migrations, models


def copy_legacy_data(apps, schema_editor):
    ServiceUser = apps.get_model("api", "ServiceUser")
    SearchRecord = apps.get_model("api", "SearchRecord")
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT id, username, email, password, is_active FROM accounts_user")
        legacy_users = cursor.fetchall()

    user_by_legacy_id = {}
    for legacy_id, username, email, password_hash, is_active in legacy_users:
        normalized_email = str(email).strip().lower()
        if not normalized_email:
            continue
        user, _ = ServiceUser.objects.get_or_create(
            email=normalized_email,
            defaults={
                "id": uuid.uuid4(),
                "name": (str(username).strip() or normalized_email.split("@")[0])[:50],
                "password_hash": password_hash,
                "role": "member",
                "is_active": bool(is_active),
            },
        )
        user_by_legacy_id[legacy_id] = user

    with connection.cursor() as cursor:
        cursor.execute("SELECT id, user_id, question, audience_level, response_type FROM search_history")
        histories = cursor.fetchall()

    for history_id, legacy_user_id, question, audience_level, response_type in histories:
        user = user_by_legacy_id.get(legacy_user_id)
        if user is None:
            continue
        SearchRecord.objects.get_or_create(
            rag_request_id=f"legacy-history-{history_id}",
            defaults={
                "id": uuid.uuid4(),
                "owner": user,
                "schema_version": "legacy-v0",
                "question": question,
                "audience_level": audience_level,
                "response_type": response_type,
                "message": "이 기록은 이전 MVP에서 저장되어 답변과 출처 스냅샷이 없습니다.",
                "warnings": ["legacy_history_without_snapshot"],
            },
        )


class Migration(migrations.Migration):
    dependencies = [("api", "0003_searchhistory")]

    operations = [
        migrations.CreateModel(
            name="ServiceUser",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("password_hash", models.CharField(max_length=128)),
                ("name", models.CharField(max_length=50)),
                ("role", models.CharField(default="member", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "users"},
        ),
        migrations.CreateModel(
            name="AuthSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="auth_sessions", to="api.serviceuser")),
            ],
            options={"db_table": "auth_sessions"},
        ),
        migrations.CreateModel(
            name="SearchRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("rag_request_id", models.CharField(max_length=80, unique=True)),
                ("interaction_id", models.CharField(blank=True, default="", max_length=80)),
                ("schema_version", models.CharField(default="0.3.0-draft", max_length=30)),
                ("question", models.TextField()),
                ("audience_level", models.CharField(max_length=20)),
                ("response_type", models.CharField(max_length=40)),
                ("message", models.TextField()),
                ("clarification", models.JSONField(blank=True, null=True)),
                ("premise_correction", models.JSONField(blank=True, null=True)),
                ("warnings", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=models.deletion.RESTRICT, related_name="search_records", to="api.serviceuser")),
            ],
            options={"db_table": "search_records", "ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="SearchCitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ordinal", models.PositiveSmallIntegerField()),
                ("chunk_id", models.CharField(max_length=512)),
                ("document_id", models.TextField(default="")),
                ("title", models.TextField()),
                ("source_url", models.TextField(blank=True, default="")),
                ("section", models.TextField(blank=True, default="")),
                ("retrieval_rank", models.PositiveIntegerField(default=1)),
                ("content", models.TextField()),
                ("search_record", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="citations", to="api.searchrecord")),
            ],
            options={"db_table": "search_citations", "ordering": ["ordinal"]},
        ),
        migrations.CreateModel(
            name="ErrorReport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("category", models.CharField(max_length=40)),
                ("content", models.TextField()),
                ("status", models.CharField(default="received", max_length=20)),
                ("staff_reply", models.TextField(blank=True, null=True)),
                ("handled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("handled_by", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="handled_reports", to="api.serviceuser")),
                ("owner", models.ForeignKey(on_delete=models.deletion.RESTRICT, related_name="error_reports", to="api.serviceuser")),
                ("search_record", models.ForeignKey(on_delete=models.deletion.RESTRICT, related_name="error_reports", to="api.searchrecord")),
            ],
            options={"db_table": "error_reports", "ordering": ["-created_at", "-id"]},
        ),
        migrations.AddIndex(model_name="authsession", index=models.Index(fields=["user", "expires_at"], name="auth_session_user_exp_idx")),
        migrations.AddIndex(model_name="searchrecord", index=models.Index(fields=["owner", "created_at"], name="search_rec_owner_created_idx")),
        migrations.AddIndex(model_name="errorreport", index=models.Index(fields=["owner", "created_at"], name="error_report_owner_created_idx")),
        migrations.AddConstraint(model_name="searchcitation", constraint=models.UniqueConstraint(fields=("search_record", "ordinal"), name="search_citation_record_ordinal_uq")),
        migrations.AddConstraint(model_name="searchcitation", constraint=models.UniqueConstraint(fields=("search_record", "chunk_id"), name="search_citation_record_chunk_uq")),
        migrations.RunPython(copy_legacy_data, migrations.RunPython.noop),
    ]
