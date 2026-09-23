"""Migrate only the isolated, persistent integration-test database."""
import os
import sys
from pathlib import Path

sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.management import call_command
from django.db import connection


if (os.environ.get("INTEGRATION_DATABASE") != "1"
        or connection.settings_dict["NAME"] != "integration"
        or connection.settings_dict["HOST"] != "db"):
    raise RuntimeError("This bootstrap is only permitted on the isolated integration database")

with connection.cursor() as cursor:
    cursor.execute("SHOW TABLES")
    tables = {row[0] for row in cursor.fetchall()}

seed = Path("/integration_seed/snapshot.json")
if not tables and seed.is_file():
    import importlib.util
    spec = importlib.util.spec_from_file_location("integration_clone", "/integration_clone.py")
    clone = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clone)
    config = connection.settings_dict
    clone.restore_snapshot(seed, {
        "INTEGRATION_DATABASE": "1", "MYSQL_HOST": config["HOST"],
        "MYSQL_PORT": config["PORT"], "MYSQL_DATABASE": config["NAME"],
        "MYSQL_USER": config["USER"], "MYSQL_PASSWORD": config["PASSWORD"],
    })
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = {row[0] for row in cursor.fetchall()}

with connection.cursor() as cursor:
    # api.0004 imports historical users from this old table. Its current model is
    # unmanaged, so a fresh disposable database needs the empty prerequisite.
    if not tables:
        cursor.execute(
            """CREATE TABLE accounts_user (
                id bigint NOT NULL PRIMARY KEY AUTO_INCREMENT,
                username varchar(150) NOT NULL,
                email varchar(254) NOT NULL,
                password varchar(128) NOT NULL,
                is_active bool NOT NULL DEFAULT 1
            ) ENGINE=InnoDB"""
        )

call_command("migrate", interactive=False)
with connection.cursor() as cursor:
    for table in ("users", "auth_sessions", "search_records", "search_citations", "error_reports"):
        cursor.execute(f"SELECT COUNT(*) FROM {connection.ops.quote_name(table)}")
        cursor.fetchone()

print("Integration migrations and application tables OK")
