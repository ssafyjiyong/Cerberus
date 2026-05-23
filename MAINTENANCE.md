# Cerberus 유지보수 가이드 (재배포 · 패치)

이 문서는 **이미 `DEPLOYMENT.md` 로 배포를 완료한 상태**에서,
이후 코드를 수정하거나 문제를 고칠 때 사용하는 운영 매뉴얼입니다.

---

## 1. 서버 구성 요약 (먼저 알아두세요)

배포된 서버는 아래와 같이 구성되어 있습니다.

| 구성 요소 | 내용 |
|---|---|
| **코드 위치** | `/opt/cerberus` (GitHub 저장소 클론본) |
| **백엔드** | systemd 서비스 `cerberus-backend` — `uvicorn` 이 `127.0.0.1:8000` 에서 실행 |
| **백엔드 가상환경** | `/opt/cerberus/backend/venv` |
| **환경 변수(코드 기본값)** | `/opt/cerberus/.env` — 관리자 페이지에서 설정한 값이 있으면 그것이 우선 |
| **런타임 설정 저장소** | DynamoDB `cerberus-leaderboard-config` — 관리자 페이지가 사용 (`ADMIN.md`) |
| **프론트엔드 소스** | `/opt/cerberus/frontend` |
| **프론트엔드 배포물** | `/usr/share/nginx/html` (nginx가 제공하는 정적 파일) |
| **웹 서버** | nginx — 설정은 `/etc/nginx/nginx.conf` |

서버 접속 방법 (PowerShell, 키 파일이 있는 폴더에서):

```powershell
ssh -i cerberus-key.pem ec2-user@<서버IP>
```

---

## 2. 가장 자주 쓰는 작업 — 코드 수정 후 재배포

GitHub에 새 코드를 푸시한 뒤, 서버에 반영하는 표준 절차입니다.

### 2-A. 전체 재배포 (백엔드·프론트 모두 바뀐 경우)

서버에 접속한 뒤, 아래를 순서대로 실행합니다.

```bash
# 1) 최신 코드 받기
cd /opt/cerberus
git pull

# 2) 백엔드 업데이트
cd /opt/cerberus/backend
source venv/bin/activate
pip install -r requirements.txt          # 패키지 목록이 바뀌었을 때만 의미 있음 (항상 실행해도 무방)
sudo systemctl restart cerberus-backend

# 3) 프론트엔드 업데이트
cd /opt/cerberus/frontend
npm install                              # package.json 이 바뀌었을 때만 의미 있음
npm run build
sudo rm -rf /usr/share/nginx/html/*
sudo cp -r dist/* /usr/share/nginx/html/

# 4) 확인
sudo systemctl status cerberus-backend
```

마지막으로 브라우저에서 `http://<서버IP>` 를 새로고침(**Ctrl + F5**)해 확인합니다.

### 2-B. 백엔드만 수정한 경우

```bash
cd /opt/cerberus && git pull
sudo systemctl restart cerberus-backend
sudo systemctl status cerberus-backend
```

### 2-C. 프론트엔드만 수정한 경우

```bash
cd /opt/cerberus && git pull
cd frontend
npm run build
sudo rm -rf /usr/share/nginx/html/*
sudo cp -r dist/* /usr/share/nginx/html/
```

> 프론트만 바꿨을 때는 백엔드를 재시작할 필요가 없습니다.
> 화면이 안 바뀌어 보이면 브라우저 캐시 때문이니 **Ctrl + F5** 로 강력 새로고침하세요.

---

## 3. 환경 설정 변경

게임 규칙이나 모델은 **두 가지 방법**으로 바꿀 수 있습니다.

### 3-A. 관리자 페이지 (권장 — 재배포 불필요)

게임 파라미터·문제·통과 기준·Bedrock 모델 등은 **관리자 페이지**(`ADMIN.md` 참고)
에서 런타임에 변경할 수 있고 즉시 반영(다음 게임 세션부터)됩니다.
관리자 페이지의 변경값은 DynamoDB `cerberus-leaderboard-config` 테이블에 저장되어
**`.env` 보다 우선 적용**됩니다.

### 3-B. `.env` 직접 편집 (초기 기본값 변경)

`.env` 는 관리자 페이지에서 설정을 한 번도 변경하지 않은 경우의 **초기 기본값**
역할을 합니다. 코드 기본값 자체를 바꿀 때만 사용합니다.

```bash
nano /opt/cerberus/.env      # 편집 후 Ctrl+O 저장, Ctrl+X 종료
sudo systemctl restart cerberus-backend
```

조정 가능한 주요 값:

| 변수 | 의미 | 기본값 |
|---|---|---|
| `TIME_LIMIT` | 제한 시간(초) | `300` |
| `P_MAX` | 최대 답변 횟수 | `15` |
| `W_TIME` | 점수 — 시간 가중치 | `1` |
| `W_PROMPT` | 점수 — 답변 횟수 가중치 | `10` |
| `BEDROCK_MODEL_ID` | 사용하는 AI 모델 | `anthropic.claude-3-haiku-20240307-v1:0` |

> 주의: `.env` 만 바꿔도 관리자 페이지에서 이미 설정된 값이 있으면 그 값이
> 우선합니다. 강제로 `.env` 기준으로 되돌리려면 관리자 페이지의 **운영 탭 →
> 기본값으로 복원** 을 실행하세요.

---

## 4. 서비스 제어 명령어 모음

```bash
# 백엔드
sudo systemctl start   cerberus-backend     # 시작
sudo systemctl stop    cerberus-backend     # 정지
sudo systemctl restart cerberus-backend     # 재시작
sudo systemctl status  cerberus-backend     # 상태 확인

# nginx
sudo systemctl restart nginx                # 재시작
sudo nginx -t                               # 설정 문법 검사
sudo systemctl reload nginx                 # 설정만 다시 읽기 (무중단)
```

---

## 5. 로그 확인

```bash
# 백엔드 로그 (실시간 — Ctrl+C 로 종료)
journalctl -u cerberus-backend -f

# 백엔드 최근 100줄
journalctl -u cerberus-backend -n 100 --no-pager

# 특정 시간 이후 로그
journalctl -u cerberus-backend --since "1 hour ago"

# nginx 접속/오류 로그
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

---

## 6. 이전 버전으로 되돌리기 (롤백)

새로 배포한 코드에 문제가 있을 때, 직전 상태로 되돌립니다.

```bash
cd /opt/cerberus

# 최근 커밋 이력 확인
git log --oneline -10

# 방법 1) 특정 커밋으로 되돌리기 (해시는 위 목록에서 복사)
git checkout <커밋해시>

# 방법 2) 가장 최근 커밋만 취소
git revert HEAD
```

되돌린 뒤에는 **2-A. 전체 재배포** 절차(빌드 + 재시작)를 다시 실행합니다.

> **권장:** 배포할 때마다 `git tag v1.0`, `git tag v1.1` 처럼 태그를 붙여두면
> 롤백 대상을 찾기 쉽습니다. (`git checkout v1.0`)

---

## 7. AI 모델 교체

다른 Bedrock 모델로 바꾸려면:

1. AWS 콘솔 > Bedrock > **Model access** 에서 새 모델을 활성화 (`DEPLOYMENT.md` STEP 1 참고)
2. `aws/iam-policy.json` 의 `BedrockInvokeClaude` 항목 `Resource` 에 새 모델 ARN을 추가하고,
   IAM 콘솔에서 `cerberus-policy` 정책을 그 내용으로 업데이트
3. `/opt/cerberus/.env` 의 `BEDROCK_MODEL_ID` 를 새 모델 ID로 변경
4. `sudo systemctl restart cerberus-backend`

> 일부 최신 모델은 단일 모델 ID 대신 "추론 프로파일(inference profile)" ID가
> 필요할 수 있습니다. 교체 후 게임이 동작하지 않으면 백엔드 로그를 확인하세요.

---

## 8. DynamoDB 데이터 관리

세 개의 테이블이 있습니다.

- **`cerberus-leaderboard`** — Top 10 랭킹
- **`cerberus-leaderboard-logs`** — 모든 채팅/게임 로그 (취약 항목 분석용)
- **`cerberus-leaderboard-config`** — 관리자 페이지의 동적 설정 (레벨 문제·게임 파라미터·관리자 비밀번호 해시·유지보수 모드). 단일 항목(`config_id="MAIN"`) 구조. 관리자 비밀번호 분실 시 이 항목을 삭제하면 다음 부팅 시 `mzcadmin` 으로 자동 시드됩니다 (자세한 절차는 `ADMIN.md` §7).

### 분석 데이터 확인

배포된 서버에서 분석 요약 API를 바로 호출할 수 있습니다.

```bash
curl http://127.0.0.1:8000/api/analytics/summary
```

응답의 `levels` 항목에서 레벨별 `clear_rate`(세션 단위 통과율),
`avg_attempts_to_clear`(클리어까지 평균 시도 횟수), `weak_criteria`(가장 자주
누락된 통과 기준)를 확인하면 **어떤 심사 항목에 사람들이 취약한지** 파악할 수 있습니다.

원본 로그를 직접 보려면 AWS 콘솔 > DynamoDB > Tables > `cerberus-leaderboard-logs`
> **Explore table items** 에서 조회합니다.

### 데이터 백업 켜기 (권장)

콘솔 > DynamoDB > 각 테이블 > **Backups** 탭 > **Point-in-time recovery (PITR)** 활성화.
실수로 데이터가 삭제돼도 특정 시점으로 복구할 수 있습니다.

### 로그 테이블이 너무 커지면

로그가 계속 쌓여 부담되면, 콘솔에서 테이블에 **TTL(Time to Live)** 속성을
추가해 오래된 항목을 자동 삭제하도록 설정하거나, 분석이 끝난 데이터를
S3로 내보낸 뒤 정리할 수 있습니다.

---

## 9. 서버 재부팅 / 점검

`cerberus-backend` 와 `nginx` 는 `systemctl enable` 되어 있으므로
**서버를 재부팅해도 자동으로 다시 시작**됩니다. 재부팅 후 확인:

```bash
sudo systemctl status cerberus-backend nginx
```

### 정기 점검 체크리스트 (월 1회 권장)

```bash
# 디스크 여유 공간 확인
df -h

# 보안 업데이트 적용
sudo dnf update -y

# 서비스 정상 동작 확인
curl http://127.0.0.1:8000/api/health
```

---

## 10. 알아두면 좋은 주의사항

- **게임 세션은 서버 메모리에 저장됩니다.** 백엔드를 재시작하면 그 시점에
  **진행 중이던 게임은 모두 초기화**됩니다. 가급적 접속자가 적은 시간에
  재배포하세요. 이미 종료된 게임의 랭킹·로그(DynamoDB 저장분)는 영향받지 않습니다.
- **장기 운영 시 메모리 누적:** 종료된 게임 세션도 메모리에 남습니다.
  수만 건 규모로 오래 운영한다면 주기적으로 백엔드를 재시작하거나,
  오래된 세션을 정리하는 로직 추가를 검토하세요.
- **분석 로깅 실패는 게임을 멈추지 않습니다.** DynamoDB 로그 적재에
  실패해도 게임은 정상 진행되며, 실패 내용은 백엔드 로그에만 기록됩니다.

---

## 11. 자주 발생하는 문제

| 증상 | 해결 방법 |
|---|---|
| 재배포 후 **502 Bad Gateway** | 백엔드 시작 실패. `journalctl -u cerberus-backend -n 50` 으로 오류 확인 (대개 코드 문법 오류 또는 패키지 누락) |
| 재배포 후 화면이 **그대로** | 브라우저 캐시. **Ctrl + F5**. 그래도 안 되면 STEP 2-C 의 빌드·복사를 다시 실행 |
| `git pull` 시 **충돌(conflict)** 메시지 | 서버에서 코드를 직접 수정했을 가능성. `git status` 로 확인 후, 서버 수정분이 불필요하면 `git reset --hard HEAD` 로 수정분을 버린 뒤 다시 `git pull` (주의: 서버에서 직접 고친 내용이 사라짐) |
| **디스크 가득 참** (`df -h` 가 100%) | `sudo dnf clean all`, 오래된 로그 정리. `npm` 캐시: `npm cache clean --force` |
| AI 통신만 실패 | Bedrock 모델 액세스/IAM 정책 확인 (`DEPLOYMENT.md` 13번 표 참고) |
| 백엔드가 자꾸 재시작됨 | `journalctl -u cerberus-backend -f` 로 반복되는 오류 원인 확인. systemd가 `Restart=always` 라 비정상 종료 시 3초 후 재시작됩니다 |

---

## 12. 빠른 참조 (Cheat Sheet)

```bash
# 표준 재배포
cd /opt/cerberus && git pull
cd backend && source venv/bin/activate && pip install -r requirements.txt && sudo systemctl restart cerberus-backend
cd ../frontend && npm install && npm run build && sudo rm -rf /usr/share/nginx/html/* && sudo cp -r dist/* /usr/share/nginx/html/

# 상태 점검
sudo systemctl status cerberus-backend nginx
curl http://127.0.0.1:8000/api/health

# 로그
journalctl -u cerberus-backend -f
```
