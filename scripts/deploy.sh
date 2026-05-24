#!/bin/bash
# =============================================================
#  Cerberus 자동 배포 스크립트
#  실행 주체 : AWS SSM Run Command (root 권한)
#  git pull   : 이 스크립트 호출 전에 완료되어 있어야 함
# =============================================================
set -e   # 오류 발생 시 즉시 중단

DEPLOY_DIR=/opt/cerberus
APP_USER=ec2-user
NGINX_HTML=/usr/share/nginx/html

echo ""
echo "================================================"
echo "  Cerberus 자동 배포 시작"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# ── 1. 백엔드 패키지 업데이트 ──────────────────────
echo ""
echo "[1/4] 백엔드 패키지 업데이트..."
sudo -u $APP_USER ${DEPLOY_DIR}/backend/venv/bin/pip install \
  -r ${DEPLOY_DIR}/backend/requirements.txt -q --no-input
echo "  ✓ 완료"

# ── 2. 프론트엔드 빌드 ────────────────────────────
echo ""
echo "[2/4] 프론트엔드 빌드..."
cd ${DEPLOY_DIR}/frontend
sudo -u $APP_USER npm install --silent
sudo -u $APP_USER npm run build
echo "  ✓ 완료"

# ── 3. 정적 파일 배포 ─────────────────────────────
echo ""
echo "[3/4] 정적 파일 배포..."
rm -rf ${NGINX_HTML:?}/*
cp -r ${DEPLOY_DIR}/frontend/dist/* ${NGINX_HTML}/
echo "  ✓ 완료"

# ── 4. 서비스 재시작 ──────────────────────────────
echo ""
echo "[4/4] 서비스 재시작..."
systemctl restart cerberus-backend
systemctl reload nginx
echo "  ✓ 완료"

echo ""
echo "================================================"
echo "  배포 완료! ✅"
echo "================================================"
echo ""
