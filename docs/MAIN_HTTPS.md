# 메인 EC2 HTTPS 유지

대상: `https://skn33heritage.site`, 메인 EC2 `3.34.183.171`.
테스트 EC2와 로컬 개발에는 `docker-compose.aws.yml`을 적용하지 않는다.

## 운영 구성

- `docker-compose.aws.yml`: 80/443 노출, 보안 쿠키, 신뢰 프록시 활성화.
- `deploy/nginx-https.conf`: HTTP 리다이렉트, ACME 검증 경로, HTTPS 화면/API.
- 인증서는 `/etc/letsencrypt`, ACME 파일은 `/var/www/letsencrypt`에 보관한다.
- 인증서·개인 키·`.env`는 Git에 추가하지 않는다.
- 기존 `/etc/heritage/nginx.conf` 대신 저장소의 Nginx 설정을 읽기 전용 마운트한다.
- 배포는 인증서와 Nginx 문법을 확인한 후 컨테이너를 교체하고, 인증서 검증을
  끄지 않은 HTTPS 요청으로 화면과 API의 `status: ok`를 검사한다.

## 최초 전환: 서버 수동 변경 처리

현재 서버의 Compose와 Django 파일은 수동 변경돼 있다. 자동 배포는 이를
덮어쓰지 않고 중단한다. 이 변경을 main에 병합한 뒤 최초 배포 전 처리한다.
진행 중인 배포가 없는지 확인하고, 서버에서 다음을 실행한다.

```bash
cd /home/ubuntu/SKN33-4th-1Team
git status --short
git diff -- docker-compose.aws.yml backend/config/settings.py frontend/nginx.conf
backup_dir=$(mktemp -d /home/ubuntu/heritage-https-backup.XXXXXX)
git diff --binary > "$backup_dir/server-changes.patch"
cp docker-compose.aws.yml "$backup_dir/"
cp backend/config/settings.py "$backup_dir/settings.py"
sudo cp /etc/heritage/nginx.conf "$backup_dir/nginx.conf"
printf 'Backup: %s\n' "$backup_dir"
```

차이가 이번 HTTPS 설정뿐인지 확인한다. 다른 변경이 있으면 복원하지 말고
개별적으로 통합한다. HTTPS 변경만 있는 경우 아래 두 파일을 원래 커밋으로 되돌린다.

```bash
git restore --source=HEAD -- docker-compose.aws.yml backend/config/settings.py
git status --short
```

이 작업은 실행 중인 컨테이너를 재시작하지 않는다. 이어서 GitHub Actions의
`Deploy main to EC2`를 최신 main으로 실행한다. 최초 HTTPS 전환에서 롤백하면
이전 커밋은 HTTP 구성이므로 필요하면 백업한 두 파일을 복원하고 Compose로
다시 시작한다. 전환 이후 HTTPS 커밋 사이에서는 기존 롤백을 사용할 수 있다.

## 갱신 예약

최초 배포 성공 후 서버에서 기존 `heritage-certbot` 예약을 아래 내용으로 교체한다.
기존 예약에 추가하면 중복 실행되므로 같은 파일을 사용한다.

```bash
sudo tee /etc/cron.d/heritage-certbot > /dev/null <<'EOF'
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
17 3,15 * * * root bash /home/ubuntu/SKN33-4th-1Team/scripts/deploy/renew-certificates.sh >> /var/log/heritage-certbot.log 2>&1
EOF
sudo chmod 644 /etc/cron.d/heritage-certbot
sudo systemctl enable --now cron
```

갱신 스크립트는 배포와 같은 잠금을 사용하며, 전체 로그를 기록한다.
기존에 수행한 `certbot renew --dry-run`은 인증서 갱신 경로를 검증한다.
배포 후 HTTP 301, HTTPS 200, API 정상 응답, 로그인·질문 기능을 확인한다.
