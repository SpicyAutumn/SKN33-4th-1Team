"""Export a sanitized consistent snapshot; restore only to a fresh test schema.

Usage: export --source-env PATH --output FILE
       restore --snapshot FILE --target-env PATH
Requires mysqlclient. Credentials never appear in command arguments or output.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

TABLES = {
    "users", "auth_sessions", "search_records", "search_citations", "search_results",
    "error_reports", "error_report_types", "error_report_quotes", "django_migrations",
    "auth_group", "auth_group_permissions", "auth_permission", "django_content_type",
    "django_admin_log", "django_session",
}
EMPTY_TABLES = {"auth_sessions", "django_session", "django_admin_log"}
TEXT_FIELDS = {"question", "message", "content", "text", "staff_reply", "title", "section"}
ENUMS = {"easy", "general", "advanced", "answered", "needs_clarification", "insufficient_evidence",
         "incorrect_fact", "citation_mismatch", "incomplete_answer", "inappropriate_content", "other",
         "member", "admin", "received", "reviewing", "completed", "in_review", "resolved"}
JSON_KEYS = set(("question audience_level schema_version request_id interaction_id response_type message "
                 "summary clarification premise_correction warnings citations media search_record_id "
                 "reason_code options label value title content text source_url document_id chunk_id "
                 "section retrieval_rank images url corrected_premise original_premise explanation "
                 "article_title id name description start_offset end_offset").split())


def env_file(path: Path) -> dict[str, str]:
    values = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#") and "=" in raw:
            key, value = raw.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    return values


def connect(values):
    import MySQLdb
    return MySQLdb.connect(host=values["MYSQL_HOST"], port=int(values.get("MYSQL_PORT", 3306)),
                           user=values["MYSQL_USER"], passwd=values["MYSQL_PASSWORD"],
                           db=values.get("MYSQL_DATABASE") or "django_project4",
                           charset="utf8mb4", connect_timeout=15)


def scrub_json(value, key=""):
    if isinstance(value, dict):
        return {k if k in JSON_KEYS else f"field_{i}": scrub_json(v, k)
                for i, (k, v) in enumerate(value.items())}
    if isinstance(value, list):
        return [scrub_json(v, key) for v in value]
    if isinstance(value, str):
        if key in {"audience_level", "response_type"} and value in ENUMS:
            return value
        if key == "search_record_id" and re.fullmatch(r"[0-9a-f-]{32,36}", value):
            return value
        if key in {"chunk_id", "document_id", "request_id", "interaction_id"}:
            return hashlib.sha256(value.encode()).hexdigest() if value else ""
        return "x" * len(value)
    return value


def sanitize(table: str, row: dict, json_columns: set[str]) -> dict:
    row = dict(row)
    for key, value in row.items():
        if value is None:
            continue
        if key in json_columns:
            row[key] = json.dumps(scrub_json(json.loads(value)), ensure_ascii=False)
        elif key in TEXT_FIELDS:
            row[key] = "x" * len(str(value))
        elif key in {"chunk_id", "document_id", "rag_request_id", "interaction_id"}:
            row[key] = hashlib.sha256(str(value).encode()).hexdigest() if value else ""
        elif key == "source_url":
            row[key] = "https://example.invalid/test-source"
        elif isinstance(value, (datetime.date, datetime.datetime)):
            row[key] = value.isoformat(sep=" ") if isinstance(value, datetime.datetime) else value.isoformat()
    if table == "users":
        row.update(email=f"test-{row['id']}@example.invalid", name="Test member",
                   password_hash="!" + secrets.token_hex(32))
    if table in {"auth_group", "auth_permission"}:
        row["name"] = f"Test {table} {row['id']}"
    if table == "search_results":
        row["share_token"] = None
        row["guest_token_hash"] = secrets.token_hex(32) if row.get("owner_id") is None else ""
    return row


def export_snapshot(source_env: Path, output: Path):
    if output.exists():
        raise RuntimeError("Refusing to overwrite an existing snapshot")
    values = env_file(source_env)
    db = connect(values)
    snapshot = {"format": 1, "sanitized": True, "tables": {}}
    try:
        with db.cursor() as cursor:
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
            cursor.execute("SHOW FULL TABLES")
            table_rows = cursor.fetchall()
            if any(t not in TABLES or kind != "BASE TABLE" for t, kind in table_rows):
                raise RuntimeError("Unknown table/view: review sanitization before exporting")
            for table, _ in table_rows:
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                ddl = cursor.fetchone()[1]
                if "ENGINE=InnoDB" not in ddl:
                    raise RuntimeError("Consistent export requires InnoDB tables")
                cursor.execute("SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS "
                               "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION", (table,))
                columns = cursor.fetchall()
                names = [c[0] for c in columns]
                json_columns = {name for name, datatype in columns if datatype == "json"}
                # Allow only the audited schema. New fields require an explicit review.
                if set(names) - ALLOWED_COLUMNS[table]:
                    raise RuntimeError(f"Unaudited columns in {table}")
                rows = []
                if table not in EMPTY_TABLES:
                    cursor.execute(f"SELECT * FROM `{table}`")
                    for values_row in cursor.fetchall():
                        rows.append(sanitize(table, dict(zip(names, values_row)), json_columns))
                snapshot["tables"][table] = {"ddl": ddl, "columns": names, "rows": rows}
            cursor.execute("SHOW FULL TABLES")
            if cursor.fetchall() != table_rows:
                raise RuntimeError("Source schema changed during export; retry without concurrent DDL")
            for table, item in snapshot["tables"].items():
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                # AUTO_INCREMENT can advance during ordinary inserts; it is not schema drift.
                normalize = lambda text: re.sub(r" AUTO_INCREMENT=\d+", "", text)
                if normalize(cursor.fetchone()[1]) != normalize(item["ddl"]):
                    raise RuntimeError("Source DDL changed during export; retry")
            cursor.execute("COMMIT")
    finally:
        db.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(snapshot, stream, ensure_ascii=False)
    print("Sanitized snapshot created:", len(snapshot["tables"]), "tables")


ALLOWED_COLUMNS = {
    "users": set("id email password_hash name role is_active created_at updated_at".split()),
    "auth_sessions": set("id token_hash expires_at last_seen_at revoked_at created_at user_id".split()),
    "search_records": set("id rag_request_id interaction_id schema_version question audience_level response_type message clarification premise_correction warnings created_at owner_id".split()),
    "search_citations": set("id ordinal chunk_id document_id title source_url section retrieval_rank content search_record_id".split()),
    "search_results": set("id guest_token_hash payload share_token created_at owner_id".split()),
    "error_reports": set("id category content status staff_reply handled_at created_at updated_at handled_by_id owner_id search_record_id".split()),
    "error_report_types": set("id code created_at error_report_id".split()),
    "error_report_quotes": set("id ordinal text start_offset end_offset created_at error_report_id".split()),
    "django_migrations": set("id app name applied".split()),
    "auth_group": set("id name".split()),
    "auth_group_permissions": set("id group_id permission_id".split()),
    "auth_permission": set("id name content_type_id codename".split()),
    "django_content_type": set("id app_label model".split()),
    "django_admin_log": set("id action_time object_id object_repr action_flag change_message content_type_id user_id".split()),
    "django_session": set("session_key session_data expire_date".split()),
}


def restore_snapshot(snapshot_path: Path, target_env: Path | dict):
    values = env_file(target_env) if isinstance(target_env, Path) else target_env
    if (values.get("INTEGRATION_DATABASE") != "1" or values.get("MYSQL_DATABASE") != "integration"
            or values.get("MYSQL_HOST") not in {"db", "127.0.0.1", "localhost"}):
        raise RuntimeError("Restore is restricted to the isolated integration DB")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("format") != 1 or snapshot.get("sanitized") is not True:
        raise RuntimeError("Only a sanitized export is accepted")
    tables = snapshot["tables"]
    if not set(tables) <= TABLES:
        raise RuntimeError("Unknown snapshot tables")
    # DDL comes from a trusted locally generated snapshot, never user-uploaded SQL.
    for table, item in tables.items():
        if (not item["ddl"].startswith(f"CREATE TABLE `{table}` (") or ";" in item["ddl"]
                or re.search(r"REFERENCES\s+`[^`]+`\s*\.", item["ddl"], re.I)):
            raise RuntimeError("Unexpected DDL")
        if not set(item["columns"]) <= ALLOWED_COLUMNS[table]:
            raise RuntimeError("Unexpected columns")
    db = connect(values)
    try:
        with db.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            if cursor.fetchall():
                raise RuntimeError("Target must be empty; existing test data is never overwritten")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table, item in tables.items():
                cursor.execute(item["ddl"])
            for table, item in tables.items():
                names = item["columns"]
                sql = f"INSERT INTO `{table}` (" + ",".join(f"`{n}`" for n in names) + ") VALUES (" + ",".join(["%s"] * len(names)) + ")"
                if item["rows"]:
                    cursor.executemany(sql, [[row[n] for n in names] for row in item["rows"]])
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            # Re-enabling checks does not validate previously inserted rows.
            cursor.execute("SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME "
                           "FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=DATABASE() "
                           "AND REFERENCED_TABLE_NAME IS NOT NULL")
            for table, column, parent, parent_column in cursor.fetchall():
                if (table not in tables or parent not in tables
                        or column not in ALLOWED_COLUMNS[table]
                        or parent_column not in ALLOWED_COLUMNS[parent]):
                    raise RuntimeError("Unexpected foreign key in restored schema")
                cursor.execute(f"SELECT COUNT(*) FROM `{table}` child LEFT JOIN `{parent}` parent "
                               f"ON child.`{column}`=parent.`{parent_column}` "
                               f"WHERE child.`{column}` IS NOT NULL AND parent.`{parent_column}` IS NULL")
                if cursor.fetchone()[0]:
                    raise RuntimeError(f"Orphaned foreign key in {table}.{column}")
        db.commit()
    finally:
        db.close()
    print("Restored sanitized snapshot; migrations were NOT run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    export = sub.add_parser("export")
    export.add_argument("--source-env", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    restore = sub.add_parser("restore")
    restore.add_argument("--snapshot", type=Path, required=True)
    restore.add_argument("--target-env", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "export":
        export_snapshot(args.source_env, args.output)
    else:
        restore_snapshot(args.snapshot, args.target_env)
