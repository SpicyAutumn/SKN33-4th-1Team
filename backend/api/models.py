import uuid

from django.db import models


class ServiceUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=128)
    name = models.CharField(max_length=50)
    role = models.CharField(max_length=20, default="member")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"


class AuthSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(ServiceUser, on_delete=models.CASCADE, related_name="auth_sessions")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auth_sessions"
        indexes = [models.Index(fields=["user", "expires_at"], name="auth_session_user_exp_idx")]


class SearchRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(ServiceUser, on_delete=models.RESTRICT, related_name="search_records")
    rag_request_id = models.CharField(max_length=80, unique=True)
    interaction_id = models.CharField(max_length=80, blank=True, default="")
    schema_version = models.CharField(max_length=30, default="0.3.0-draft")
    question = models.TextField()
    audience_level = models.CharField(max_length=20)
    response_type = models.CharField(max_length=40)
    message = models.TextField()
    clarification = models.JSONField(null=True, blank=True)
    premise_correction = models.JSONField(null=True, blank=True)
    warnings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_records"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "created_at"], name="search_rec_owner_created_idx")]


class SearchCitation(models.Model):
    search_record = models.ForeignKey(SearchRecord, on_delete=models.CASCADE, related_name="citations")
    ordinal = models.PositiveSmallIntegerField()
    chunk_id = models.CharField(max_length=512)
    document_id = models.TextField(default="")
    title = models.TextField()
    source_url = models.TextField(blank=True, default="")
    section = models.TextField(blank=True, default="")
    retrieval_rank = models.PositiveIntegerField(default=1)
    content = models.TextField()

    class Meta:
        db_table = "search_citations"
        ordering = ["ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["search_record", "ordinal"], name="search_citation_record_ordinal_uq"),
            models.UniqueConstraint(fields=["search_record", "chunk_id"], name="search_citation_record_chunk_uq"),
        ]


class ErrorReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(ServiceUser, on_delete=models.RESTRICT, related_name="error_reports")
    search_record = models.ForeignKey(SearchRecord, on_delete=models.RESTRICT, related_name="error_reports")
    content = models.TextField()
    status = models.CharField(max_length=20, default="received")
    staff_reply = models.TextField(null=True, blank=True)
    handled_by = models.ForeignKey(ServiceUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="handled_reports")
    handled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "error_reports"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["owner", "created_at"], name="error_report_owner_created_idx")]


class SearchResult(models.Model):
    """Immutable answer snapshot; public access requires a separate share token."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(ServiceUser, null=True, blank=True, on_delete=models.CASCADE)
    guest_token_hash = models.CharField(max_length=64, blank=True, default="")
    payload = models.JSONField(default=dict)
    share_token = models.UUIDField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_results"


class ErrorReportType(models.Model):
    """One selected error type for an error report.

    This table is the single source of truth for report categories.
    """

    id = models.BigAutoField(primary_key=True)
    error_report = models.ForeignKey(ErrorReport, on_delete=models.CASCADE, related_name="types")
    code = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "error_report_types"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["error_report", "code"], name="error_report_type_uq"),
        ]


class ErrorReportQuote(models.Model):
    """A sentence or passage selected from the answer being reported.

    Offsets make repeated identical wording distinguishable. They are nullable
    so reports created before sentence-selection UI is released remain valid.
    """

    id = models.BigAutoField(primary_key=True)
    error_report = models.ForeignKey(ErrorReport, on_delete=models.CASCADE, related_name="selected_quotes")
    ordinal = models.PositiveSmallIntegerField()
    text = models.TextField()
    start_offset = models.PositiveIntegerField(null=True, blank=True)
    end_offset = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "error_report_quotes"
        ordering = ["ordinal"]
        constraints = [
            models.UniqueConstraint(fields=["error_report", "ordinal"], name="error_report_quote_ordinal_uq"),
        ]
