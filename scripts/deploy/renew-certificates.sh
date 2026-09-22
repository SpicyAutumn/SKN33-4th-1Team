#!/usr/bin/env bash
set -Eeuo pipefail
# Share the deployment lock so reload cannot race container replacement.
exec 9>/home/ubuntu/.heritage-deploy.lock
flock -n 9 || exit 0
docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/www/letsencrypt:/var/www/letsencrypt \
  certbot/certbot renew --quiet
docker exec heritage-guide-frontend-1 nginx -t
docker exec heritage-guide-frontend-1 nginx -s reload
