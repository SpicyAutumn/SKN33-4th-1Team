#!/usr/bin/env python3
"""Build and publish the common integration site on its dedicated EC2 host.

This controller is sent over SSM by a trusted GitHub Actions workflow.  It never
receives GitHub or AWS credentials, and it only reads the test server's local
API configuration.  The production EC2, production .env, and production MySQL
are deliberately outside this program's reach.
"""
from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request


ROOT = Path("/srv/heritage-test")
REPO_URL = "https://github.com/SpicyAutumn/SKN33-4th-1Team.git"
PROJECT = "heritage-integration"
SHA = re.compile(r"[0-9a-f]{40}")
PR_NUMBER = re.compile(r"[1-9][0-9]*")
ENV_KEY = re.compile(r"[A-Z][A-Z0-9_]*")
API_KEYS = {
    "AKS_API_KEY", "AKS_API_BASE_URL", "OPENAI_API_KEY", "OPENAI_CHAT_MODEL",
    "OPENAI_EMBEDDING_MODEL", "PINECONE_API_KEY", "PINECONE_INDEX_NAME",
    "PINECONE_NAMESPACE", "RAG_TOP_K", "RAG_MIN_RETRIEVAL_SCORE",
    "LANGSMITH_TRACING", "LANGSMITH_ENDPOINT", "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT", "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_KEEP_ALIVE",
    "ADMIN_DASHBOARD_PASSWORD",
}


def select_deployment() -> None:
    """Use the host's explicit clone-lab selection, retaining its existing DB."""
    global ROOT, PROJECT
    config_path = ROOT / "deployment.json"
    if not config_path.exists():
        return
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config != {"deployment": "clone-lab"}:
        raise RuntimeError("Unsupported test deployment selection")
    target = ROOT / "clone-lab"
    if target.is_symlink() or not (target / ".test-server").is_file():
        raise RuntimeError("Selected test deployment is missing its dedicated marker")
    ROOT = target
    PROJECT = "heritage-db-clone"


def command(*args: str, cwd: Path | None = None, capture: bool = False) -> str:
    completed = subprocess.run(
        args, cwd=cwd, check=True, text=True, timeout=1800,
        stdout=subprocess.PIPE if capture else None,
    )
    return completed.stdout.strip() if capture else ""


def compose(release: Path, *args: str) -> None:
    command("sudo", "-n", "docker", "compose", "-p", PROJECT, "-f", str(release / "compose.json"), *args)


def private_file(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def parse_api_environment(path: Path) -> dict[str, str]:
    """Return only explicitly permitted, single-line values from test-api.env."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in API_KEYS and ENV_KEY.fullmatch(key):
            values[key] = value.strip().strip("'\"")
    return values


def validate_payload(raw: object) -> tuple[str, list[tuple[int, str]]]:
    if not isinstance(raw, dict) or set(raw) != {"main_sha", "prs"}:
        raise ValueError("Invalid integration payload")
    main_sha = raw["main_sha"]
    prs = raw["prs"]
    if not isinstance(main_sha, str) or not SHA.fullmatch(main_sha) or not isinstance(prs, list):
        raise ValueError("Invalid integration revision")
    selected: list[tuple[int, str]] = []
    previous = 0
    for item in prs:
        if not isinstance(item, dict) or set(item) != {"number", "sha"}:
            raise ValueError("Invalid pull request entry")
        number, sha = item["number"], item["sha"]
        if not isinstance(number, int) or not PR_NUMBER.fullmatch(str(number)) or not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Invalid pull request revision")
        if number <= previous:
            raise ValueError("Pull requests must be in ascending unique order")
        selected.append((number, sha))
        previous = number
    return main_sha, selected


def guarded_remove(path: Path) -> None:
    releases = ROOT / "releases"
    if path.parent != releases or not re.fullmatch(r"[0-9a-f]{16}", path.name) or path.is_symlink():
        raise RuntimeError("Refusing to remove an unexpected path")
    if path.exists():
        shutil.rmtree(path)


def create_source(release: Path, main_sha: str, prs: list[tuple[int, str]]) -> Path:
    source = release / "source"
    source.mkdir()
    command("git", "init", "-q", str(source))
    command("git", "remote", "add", "origin", REPO_URL, cwd=source)
    command("git", "fetch", "--no-tags", "origin", "refs/heads/main", cwd=source)
    fetched = command("git", "rev-parse", "FETCH_HEAD", cwd=source, capture=True)
    if fetched != main_sha:
        raise RuntimeError("main moved while the integration deployment was being prepared")
    command("git", "checkout", "--detach", "-q", main_sha, cwd=source)
    command("git", "config", "user.name", "Integration Test Bot", cwd=source)
    command("git", "config", "user.email", "integration-test@localhost", cwd=source)
    for number, sha in prs:
        command("git", "fetch", "--no-tags", "origin", f"refs/pull/{number}/head", cwd=source)
        fetched = command("git", "rev-parse", "FETCH_HEAD", cwd=source, capture=True)
        if fetched != sha:
            raise RuntimeError(f"PR #{number} moved while the integration deployment was being prepared")
        command("git", "merge", "--no-ff", "--no-edit", "--no-verify", sha, cwd=source)
    return source


def compose_config(release: Path, public_ip: str) -> dict[str, object]:
    source = release / "source"
    common = {
        "restart": "unless-stopped",
        "security_opt": ["no-new-privileges:true"],
        "logging": {"driver": "json-file", "options": {"max-size": "10m", "max-file": "2"}},
    }
    return {
        "services": {
            "db": {
                **common, "image": "mysql:8.4", "mem_limit": "1g", "cpus": 1.0,
                "env_file": [str(release / "mysql.env")], "networks": ["database"],
                "volumes": ["db:/var/lib/mysql"],
                "healthcheck": {"test": ["CMD-SHELL", "mysqladmin ping -h localhost --silent"],
                                "interval": "5s", "timeout": "3s", "retries": 40},
            },
            "backend": {
                **common, "image": f"heritage-integration-backend:{release.name}",
                "build": {"context": str(source), "dockerfile": "backend/Dockerfile"},
                "mem_limit": "2g", "cpus": 1.5, "env_file": [str(release / "app.env")],
                "networks": ["default", "database"],
                "volumes": [
                    f"{ROOT}/data/aks_bm25_v1.sqlite3:/data/aks_bm25_v1.sqlite3:ro",
                    f"{ROOT}/data/aks_article_medias.jsonl:/data/aks_article_medias.jsonl:ro",
                    f"{release}/bootstrap_db.py:/integration_bootstrap.py:ro",
                    f"{release}/clone_database.py:/integration_clone.py:ro",
                    f"{ROOT}/seed:/integration_seed:ro",
                ],
                "depends_on": {"db": {"condition": "service_healthy"}},
                "healthcheck": {"test": ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"],
                                "interval": "5s", "timeout": "3s", "retries": 30},
            },
            "frontend": {
                **common, "image": f"heritage-integration-frontend:{release.name}",
                "build": {"context": str(source), "dockerfile": "frontend/Dockerfile"},
                "mem_limit": "256m", "cpus": 0.5, "ports": ["80:80"], "networks": ["default"],
                "depends_on": {"backend": {"condition": "service_healthy"}},
            },
        },
        "volumes": {"db": {"name": f"{PROJECT}_db"}},
        "networks": {"default": {}, "database": {"internal": True}},
    }


def configure_release(release: Path, public_ip: str) -> None:
    api = parse_api_environment(ROOT / "test-api.env")
    # Credentials must survive releases just like the persistent volume.
    stable = ROOT / "mysql.env"
    if not stable.exists():
        previous = active_release()
        if previous:
            content = (previous / "mysql.env").read_text(encoding="utf-8")
        else:
            # Never guess credentials for an orphaned, existing data volume.
            found = command("sudo", "-n", "docker", "volume", "ls", "--format", "{{.Name}}", capture=True)
            if f"{PROJECT}_db" in found.splitlines():
                raise RuntimeError("Existing test volume has no credentials; recover ROOT/mysql.env first")
            content = "\n".join(("MYSQL_DATABASE=integration", "MYSQL_USER=integration",
                                  f"MYSQL_PASSWORD={secrets.token_hex(24)}",
                                  f"MYSQL_ROOT_PASSWORD={secrets.token_hex(32)}", ""))
        private_file(stable, content)
    content = stable.read_text(encoding="utf-8")
    values = dict(line.split("=", 1) for line in content.splitlines() if "=" in line)
    if (values.get("MYSQL_DATABASE") != "integration" or values.get("MYSQL_USER") != "integration"
            or not values.get("MYSQL_PASSWORD") or not values.get("MYSQL_ROOT_PASSWORD")):
        raise RuntimeError("Invalid persistent test database configuration")
    password = values["MYSQL_PASSWORD"]
    private_file(release / "mysql.env", content)
    api.update({
        "MYSQL_HOST": "db", "MYSQL_PORT": "3306", "MYSQL_DATABASE": "integration",
        "MYSQL_USER": "integration", "MYSQL_PASSWORD": password, "INTEGRATION_DATABASE": "1",
        "DJANGO_SECRET_KEY": secrets.token_hex(32), "DJANGO_DEBUG": "false",
        "DJANGO_COOKIE_SECURE": "false", "DJANGO_ALLOWED_HOSTS": f"localhost,127.0.0.1,backend,{public_ip}",
        "AKS_BM25_INDEX_PATH": "/data/aks_bm25_v1.sqlite3",
        "AKS_MEDIA_JSONL_PATH": "/data/aks_article_medias.jsonl",
    })
    private_file(release / "app.env", "\n".join(f"{key}={value}" for key, value in sorted(api.items())) + "\n")
    private_file(release / "compose.json", json.dumps(compose_config(release, public_ip)))


def backup_database(release: Path) -> None:
    """Snapshot the stopped test application's DB before any migration runs."""
    backup = release / "before-migrate.sql"
    with backup.open("xb") as output:
        backup.chmod(0o600)
        try:
            subprocess.run([
                "sudo", "-n", "docker", "compose", "-p", PROJECT,
                "-f", str(release / "compose.json"), "exec", "-T", "db", "sh", "-c",
                'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysqldump -uroot '
                '--single-transaction --quick --skip-lock-tables --no-tablespaces '
                '--set-gtid-purged=OFF --hex-blob integration',
            ], stdout=output, check=True, timeout=600)
        except Exception:
            backup.unlink(missing_ok=True)
            raise


def start_release(release: Path, public_ip: str) -> None:
    compose(release, "up", "-d", "--wait", "--wait-timeout", "240", "db")
    # Retry connection readiness only. Never blindly retry partially applied DDL.
    for attempt in range(12):
        try:
            compose(release, "exec", "-T", "db", "sh", "-c",
                    'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; mysql -uroot integration -e "SELECT 1"')
            break
        except subprocess.CalledProcessError:
            if attempt == 11:
                raise
            time.sleep(5)
    backup_database(release)
    private_file(ROOT / "database-review-required.json", json.dumps({
        "release": release.name, "backup": str(release / "before-migrate.sql"),
    }))
    compose(release, "run", "--rm", "--no-deps", "backend", "python", "/integration_bootstrap.py")
    compose(release, "up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
    for path in ("/", "/api/health"):
        request = urllib.request.Request(f"http://127.0.0.1{path}", headers={"Host": public_ip})
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"Integration HTTP check failed for {path}")


def active_release() -> Path | None:
    state = ROOT / "active.json"
    if not state.is_file():
        return None
    release_id = json.loads(state.read_text(encoding="utf-8")).get("release")
    candidate = ROOT / "releases" / str(release_id)
    if re.fullmatch(r"[0-9a-f]{16}", str(release_id)) and candidate.is_dir() and not candidate.is_symlink():
        return candidate
    return None


def stop_active() -> None:
    release = active_release()
    if release:
        compose(release, "down", "--remove-orphans")
    # Keep active.json and mysql.env so later deployments can adopt this DB.


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: server.py BASE64_JSON_PAYLOAD")
    import base64
    payload = json.loads(base64.b64decode(sys.argv[1], validate=True))
    main_sha, prs = validate_payload(payload)
    if not (ROOT / ".test-server").is_file():
        raise RuntimeError("Dedicated test-server marker is missing")
    if not (ROOT / "data" / "aks_bm25_v1.sqlite3").is_file() or not (ROOT / "data" / "aks_article_medias.jsonl").is_file():
        raise RuntimeError("Integration search data files are missing")
    config = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    public_ip = str(ipaddress.IPv4Address(config["public_ip"]))
    if not (ROOT / "test-api.env").is_file():
        raise RuntimeError("test-api.env is missing")
    releases = ROOT / "releases"
    releases.mkdir(mode=0o700, exist_ok=True)
    # fcntl is available on the Ubuntu deployment host; importing it here keeps
    # the pure payload/environment validation helpers testable on Windows too.
    import fcntl

    with (ROOT / ".integration.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (ROOT / "database-review-required.json").exists():
            raise RuntimeError("Prior deployment needs database review; do not start old code against changed schema")
        previous = active_release()
        # With no preview PRs, keep the latest main available against the same DB.
        release = releases / secrets.token_hex(8)
        release.mkdir(mode=0o700)
        switched = False
        try:
            create_source(release, main_sha, prs)
            shutil.copy2(Path(__file__).with_name("bootstrap_db.py"), release / "bootstrap_db.py")
            shutil.copy2(Path(__file__).with_name("clone_database.py"), release / "clone_database.py")
            (ROOT / "seed").mkdir(mode=0o700, exist_ok=True)
            configure_release(release, public_ip)
            compose(release, "build")
            # Builds have succeeded; replace application containers, keeping data.
            if previous:
                compose(previous, "down", "--remove-orphans")
            switched = True
            start_release(release, public_ip)
        except Exception:
            if switched:
                try:
                    compose(release, "down", "--remove-orphans")
                except Exception:
                    pass
                # Schema changes may be irreversible. Preserve data and backup,
                # leave the app stopped, and require an explicit recovery.
                if not (ROOT / "database-review-required.json").exists():
                    private_file(ROOT / "database-review-required.json", json.dumps({"release": release.name}))
            raise
        private_file(ROOT / "active.json", json.dumps({"release": release.name, "main_sha": main_sha,
                                                         "prs": [{"number": n, "sha": s} for n, s in prs]}) + "\n")
        (ROOT / "database-review-required.json").unlink(missing_ok=True)
        # Keep previous source and database backups for manual recovery.
        print("INTEGRATION_RESULT=" + json.dumps({"state": "ready", "url": f"http://{public_ip}",
                                                     "main_sha": main_sha, "prs": [n for n, _ in prs]}))


if __name__ == "__main__":
    select_deployment()
    main()
