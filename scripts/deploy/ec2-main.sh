#!/usr/bin/env bash
# Run as ubuntu through SSM. Never sources, prints or overwrites .env.
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
sha=${1:?Usage: ec2-main.sh COMMIT_SHA}
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid commit SHA'; exit 1; }
cd /home/ubuntu/SKN33-4th-1Team
exec 9>/home/ubuntu/.heritage-deploy.lock
flock -n 9 || { echo 'Another deployment is running'; exit 1; }

[[ -z $(git status --porcelain --untracked-files=no) ]] || {
  echo 'Tracked server files have local edits; resolve them before deploying.'; exit 1;
}
test -f .env
test -s data/processed/aks_bm25_v1.sqlite3
test -f data/processed/aks_article_medias.jsonl
sudo -n docker compose version
git fetch origin main
[[ $(git rev-parse origin/main) == "$sha" ]] || {
  echo 'Requested commit is no longer the tip of main; refusing stale deployment.'; exit 1;
}

previous=$(git rev-parse HEAD)
compose=(sudo -n docker compose -f docker-compose.yml -f docker-compose.aws.yml)
services=(backend frontend)
for service in "${services[@]}"; do
  container=$("${compose[@]}" ps -q "$service")
  [[ -n "$container" ]] || { echo "Existing $service container required for rollback"; exit 1; }
  image=$(sudo -n docker inspect --format '{{.Image}}' "$container")
  sudo -n docker tag "$image" "heritage-guide-$service:rollback"
done

switched=0
recover() {
  code=$?
  trap - ERR
  set +e
  echo 'Deployment failed; restoring previous code and images.'
  git checkout --detach "$previous"
  for service in "${services[@]}"; do
    sudo -n docker tag "heritage-guide-$service:rollback" "heritage-guide-$service:latest"
  done
  if (( switched )); then
    "${compose[@]}" up -d --no-build --force-recreate --wait --wait-timeout 180
    if (( $? != 0 )); then echo 'ROLLBACK FAILED: inspect the EC2 containers manually.'; fi
  fi
  exit "$code"
}
trap recover ERR
git checkout --detach "$sha"
"${compose[@]}" config --quiet
sudo -n test -s /etc/letsencrypt/live/skn33heritage.site/fullchain.pem
sudo -n test -s /etc/letsencrypt/live/skn33heritage.site/privkey.pem
# Validate TLS configuration before replacing either running service.
"${compose[@]}" run --rm --no-deps frontend nginx -t
# Build before replacing the running containers. Database schema is never migrated automatically.
"${compose[@]}" build
"${compose[@]}" run --rm --no-deps backend python manage.py shell -c \
  "from django.db import connection; c=connection.cursor(); c.execute('SELECT 1'); assert c.fetchone()[0] == 1; c.close(); print('DB connection OK')"
switched=1
# Recreate both services so nginx resolves the new backend container address.
"${compose[@]}" up -d --no-build --force-recreate --wait --wait-timeout 180
https_check=(curl --fail --silent --show-error --retry 6 --retry-delay 5 --retry-all-errors
  --connect-timeout 10 --max-time 30 --resolve skn33heritage.site:443:127.0.0.1)
"${https_check[@]}" https://skn33heritage.site/ >/dev/null
"${https_check[@]}" https://skn33heritage.site/api/health | python3 -c \
  'import json,sys; assert json.load(sys.stdin).get("status") == "ok", "Unhealthy HTTPS API"'
trap - ERR
echo "Successfully deployed $sha"
"${compose[@]}" ps
