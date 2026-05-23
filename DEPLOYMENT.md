# Cerberus 배포 가이드 (AWS EC2)

이 문서는 **AWS를 처음 다뤄보는 분도 그대로 따라 하면 배포가 완료되도록** 작성되었습니다.
위에서부터 순서대로, 한 단계도 건너뛰지 말고 진행하세요.

---

## 0. 무엇을 하게 되나요?

GitHub에 올라간 Cerberus 코드를 AWS 서버(EC2) 1대에 올려서, 누구나
인터넷 주소로 접속해 게임을 할 수 있게 만듭니다.

- **예상 소요 시간:** 약 40~60분
- **예상 비용:** EC2 `t3.small` 기준 월 약 $15 + Bedrock 호출 비용(소액) + DynamoDB(거의 무료 수준). 데모 용도면 월 $20 안팎입니다.
- **최종 결과물:** `http://<서버주소>` 로 접속하면 게임 화면이 뜹니다.

---

## 1. 사전 준비물

아래 3가지가 준비되어 있어야 합니다.

1. **AWS 계정** — 신용카드 등록까지 완료된 상태
2. **GitHub 저장소** — Cerberus 코드가 업로드되어 있어야 합니다 (저장소 주소를 알아두세요)
3. **SSH 접속 도구** — Windows 10/11에는 기본 내장되어 있습니다 (별도 설치 불필요)

---

## 2. 전체 구조 한눈에 보기

```
[사용자 브라우저]
       │  http (80번 포트)
       ▼
┌──────────────────────── EC2 서버 1대 ────────────────────────┐
│  nginx (80번 포트)                                            │
│    ├─ "/"      → React 정적 파일 (게임 화면)                  │
│    └─ "/api/*" → 백엔드로 전달 ──┐                            │
│                                  ▼                            │
│  uvicorn + FastAPI 백엔드 (127.0.0.1:8000)                    │
└───────────────┬───────────────────────────┬──────────────────┘
                │                           │
                ▼                           ▼
        Amazon Bedrock              Amazon DynamoDB
        (AI 심사원)                 (랭킹 + 분석 로그)
```

> **왜 EC2인가요?** 백엔드는 게임 진행 상태를 서버 메모리에 보관합니다.
> Lambda 같은 서버리스 환경은 요청마다 실행 환경이 달라져 게임 세션이
> 끊기므로, 한 대의 EC2에서 계속 실행하는 방식이 가장 안정적입니다.

---

## 3. STEP 1 — Bedrock(AI 모델) 사용 권한 켜기

AI 심사원은 Amazon Bedrock의 Claude 모델을 씁니다. 이 모델은 기본적으로
꺼져 있어서, 먼저 활성화해야 합니다.

1. AWS 콘솔 오른쪽 위에서 **리전을 `미국 동부(버지니아 북부) us-east-1`** 로 변경합니다.
   (이 가이드는 전부 `us-east-1` 기준입니다. 다른 리전을 쓰면 모든 단계의 리전을 맞춰야 합니다.)
2. 검색창에 **`Bedrock`** 입력 → Amazon Bedrock 으로 이동
3. 왼쪽 메뉴 맨 아래 **`Model access`** 클릭
4. **`Manage model access`** (또는 `Enable specific models`) 버튼 클릭
5. 목록에서 **`Claude 3 Haiku`** 를 체크
6. **`Save changes`** 클릭 → 상태가 **`Access granted`** 로 바뀌면 완료 (보통 즉시)

> 이 단계를 건너뛰면 게임에서 "심사원과의 통신 중 오류" 가 발생합니다.

---

## 4. STEP 2 — 권한(IAM) 만들기

서버가 Bedrock과 DynamoDB를 사용하려면 권한이 필요합니다.

### 4-1. 내 AWS 계정 ID 확인

AWS 콘솔 오른쪽 위 계정 이름을 클릭하면 나오는 **12자리 숫자**가 계정 ID입니다.
(예: `123456789012`) 메모해 두세요.

### 4-2. 정책(Policy) 만들기

1. 콘솔 검색창에 **`IAM`** 입력 → IAM 으로 이동
2. 왼쪽 메뉴 **`Policies`** → **`Create policy`**
3. **`JSON`** 탭 클릭 → 입력창 내용을 모두 지우고, 저장소의
   **`aws/iam-policy.json`** 파일 내용을 그대로 붙여넣기
4. 붙여넣은 내용에서 **`<ACCOUNT_ID>`** 글자를 전부(총 6군데) 4-1에서 확인한
   12자리 계정 ID로 바꿉니다.
5. **`Next`** → 정책 이름에 **`cerberus-policy`** 입력 → **`Create policy`**

### 4-3. 역할(Role) 만들기

1. IAM 왼쪽 메뉴 **`Roles`** → **`Create role`**
2. **`Trusted entity type`**: `AWS service` 선택
3. **`Use case`**: `EC2` 선택 → **`Next`**
4. 권한 목록에서 방금 만든 **`cerberus-policy`** 검색 후 체크 → **`Next`**
5. 역할 이름에 **`cerberus-ec2-role`** 입력 → **`Create role`**

> 이 역할을 EC2에 연결하면, 서버에 비밀번호(액세스 키)를 따로 저장하지
> 않아도 AWS 서비스를 안전하게 사용할 수 있습니다.

---

## 5. STEP 3 — EC2 서버 만들기

1. 콘솔 검색창에 **`EC2`** → EC2 로 이동 → **`Launch instance`** 클릭
2. 항목을 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Name** | `cerberus-server` |
| **AMI (운영체제)** | `Amazon Linux 2023` (기본 선택값) |
| **Instance type** | `t3.small` 권장 (`t2.micro`는 메모리 부족 위험) |
| **Key pair** | `Create new key pair` 클릭 → 이름 `cerberus-key` → 유형 `RSA`, 형식 `.pem` → 생성하면 파일이 다운로드됩니다. **이 파일을 잃어버리면 서버에 접속할 수 없으니 잘 보관하세요.** |

3. **Network settings** 의 `Edit` 클릭 → **Security group(방화벽)** 규칙을 아래처럼 만듭니다.

| 유형 | 포트 | 소스 | 설명 |
|---|---|---|---|
| SSH | 22 | `My IP` | 서버 관리 접속용 (본인 IP만 허용) |
| HTTP | 80 | `Anywhere (0.0.0.0/0)` | 게임 접속용 (누구나 허용) |

4. **Advanced details** 펼치기 → **`IAM instance profile`** 에서 STEP 2에서 만든
   **`cerberus-ec2-role`** 선택
5. 오른쪽 **`Launch instance`** 클릭

잠시 후 인스턴스 목록에서 `cerberus-server`의 상태가 **`Running`** 이 되면,
그 행을 클릭해 **`Public IPv4 address`** (예: `13.x.x.x`)를 메모합니다.
앞으로 이 주소를 **`<서버IP>`** 라고 부르겠습니다.

---

## 6. STEP 4 — 서버에 접속하기

1. 다운로드한 `cerberus-key.pem` 파일이 있는 폴더에서 PowerShell을 엽니다.
2. 처음 한 번만, 키 파일 권한을 설정합니다.

```powershell
icacls cerberus-key.pem /inheritance:r
icacls cerberus-key.pem /grant:r "$($env:USERNAME):(R)"
```

3. 서버에 접속합니다. (`<서버IP>` 를 실제 주소로 바꾸세요.)

```powershell
ssh -i cerberus-key.pem ec2-user@<서버IP>
```

처음 접속 시 `Are you sure you want to continue connecting?` 가 나오면 `yes` 입력.
프롬프트가 `[ec2-user@ip-... ~]$` 로 바뀌면 접속 성공입니다.
**이제부터의 명령어는 모두 이 서버 안에서 실행합니다.**

---

## 7. STEP 5 — 서버에 필요한 프로그램 설치

서버 안에서 아래 명령을 순서대로 실행합니다. (복사해서 붙여넣으면 됩니다.)

```bash
# 시스템 최신화
sudo dnf update -y

# Git, Python 3.11, nginx 설치
sudo dnf install -y git python3.11 python3.11-pip nginx

# Node.js 20 설치 (프론트엔드 빌드용)
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs

# 설치 확인 (버전 숫자가 출력되면 정상)
python3.11 --version
node --version
```

---

## 8. STEP 6 — 코드 내려받기

```bash
# /opt/cerberus 위치에 코드를 받습니다 (<GITHUB_저장소_주소>를 실제 주소로 교체)
sudo git clone <GITHUB_저장소_주소> /opt/cerberus

# 폴더 소유자를 현재 사용자로 변경 (이후 작업이 편해집니다)
sudo chown -R ec2-user:ec2-user /opt/cerberus

cd /opt/cerberus
```

---

## 9. STEP 7 — 백엔드 설정 및 실행

### 9-1. 파이썬 패키지 설치

```bash
cd /opt/cerberus/backend

# 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate

# 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt
```

### 9-2. 환경 변수 파일(.env) 만들기

```bash
cp /opt/cerberus/.env.example /opt/cerberus/.env
```

> **중요:** EC2 서버에서는 `.env`에 AWS 액세스 키를 **넣지 않습니다.**
> STEP 2에서 연결한 IAM 역할(`cerberus-ec2-role`)이 자동으로 권한을
> 제공하기 때문입니다. `.env`의 AWS 키 줄은 주석(`#`) 처리된 채로 두세요.
> `AWS_REGION=us-east-1` 만 맞으면 됩니다.

### 9-3. 백엔드를 항상 실행되는 서비스로 등록

서버가 재부팅돼도 백엔드가 자동으로 켜지도록 systemd 서비스로 등록합니다.
아래 명령을 **통째로** 복사해 붙여넣으세요.

```bash
sudo tee /etc/systemd/system/cerberus-backend.service > /dev/null <<'EOF'
[Unit]
Description=Cerberus Backend (FastAPI)
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/opt/cerberus/backend
ExecStart=/opt/cerberus/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
```

서비스를 시작합니다.

```bash
sudo systemctl daemon-reload
sudo systemctl enable cerberus-backend
sudo systemctl start cerberus-backend

# 상태 확인 — 초록색 'active (running)' 이 보이면 정상
sudo systemctl status cerberus-backend
```

> 백엔드가 처음 실행될 때, 3개의 DynamoDB 테이블(`cerberus-leaderboard`,
> `cerberus-leaderboard-logs`, `cerberus-leaderboard-config`)이 **자동으로 생성**됩니다.
> 로그로 확인하려면: `journalctl -u cerberus-backend --no-pager | tail -20`
> ("테이블 생성 완료" 메시지가 보이면 성공)
>
> `cerberus-leaderboard-config` 테이블은 관리자 페이지가 사용하는 동적 설정
> 저장소이며, 첫 실행 시 기본 관리자 비밀번호 `mzcadmin` 의 bcrypt 해시가
> 자동으로 시드됩니다.

---

## 10. STEP 8 — 프론트엔드 빌드

```bash
cd /opt/cerberus/frontend

# 패키지 설치
npm install

# 정적 파일 빌드 (frontend/dist 폴더가 생성됩니다)
npm run build

# 빌드 결과물을 nginx가 제공하는 폴더로 복사
sudo rm -rf /usr/share/nginx/html/*
sudo cp -r dist/* /usr/share/nginx/html/
```

---

## 11. STEP 9 — nginx 설정

nginx가 게임 화면을 보여주고, `/api` 요청은 백엔드로 전달하도록 설정합니다.
아래 명령을 **통째로** 복사해 붙여넣으세요. (기존 nginx 설정을 통째로 교체합니다.)

```bash
sudo tee /etc/nginx/nginx.conf > /dev/null <<'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" "$http_user_agent"';
    access_log /var/log/nginx/access.log main;

    sendfile on;
    keepalive_timeout 65;

    server {
        listen 80 default_server;
        server_name _;

        # React 정적 파일 (게임 화면)
        root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ /index.html;
        }

        # 백엔드 API 프록시
        location /api/ {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_read_timeout 60s;
        }
    }
}
EOF
```

nginx가 백엔드로 연결할 수 있도록 보안 설정(SELinux)을 허용하고, 시작합니다.

```bash
# nginx → 백엔드 연결 허용 (Amazon Linux 보안 설정)
sudo setsebool -P httpd_can_network_connect 1

# 설정 문법 검사 — 'syntax is ok' 가 보여야 함
sudo nginx -t

# nginx 시작 및 자동 실행 등록
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 12. STEP 10 — 동작 확인

웹 브라우저 주소창에 **`http://<서버IP>`** 를 입력합니다.

- ✅ 케르베로스 게임 시작 화면이 보이면 성공입니다.
- ✅ `PRESS START` 를 눌러 실제로 AI 심사원과 대화가 되는지 확인하세요.
- ✅ AWS 콘솔 > DynamoDB > Tables 에서 `cerberus-leaderboard` 와
  `cerberus-leaderboard-logs` 테이블이 생성되었는지 확인하세요.

문제가 있으면 아래 **13. 문제 해결**을 참고하세요.

---

## 13. 문제 해결 (Troubleshooting)

| 증상 | 원인 및 해결 방법 |
|---|---|
| 브라우저에 **502 Bad Gateway** | 백엔드가 꺼져 있음. `sudo systemctl status cerberus-backend` 확인 → `journalctl -u cerberus-backend -n 50` 으로 오류 확인 |
| **화면이 하얗게** 나옴 | 프론트 빌드물 복사 누락. STEP 8을 다시 실행 |
| 페이지는 뜨는데 게임 시작 시 **"심사원과의 통신 오류"** | ① STEP 1의 Bedrock 모델 액세스 미설정 ② IAM 역할/정책 문제. `journalctl -u cerberus-backend -n 50` 에서 `AccessDenied` 여부 확인 |
| 사이트 접속 자체가 안 됨 | EC2 보안 그룹에 HTTP(80) 규칙이 있는지 확인 (STEP 3) |
| `nginx -t` 에서 오류 | STEP 11의 설정 블록을 다시 정확히 붙여넣기 |
| DynamoDB 테이블이 안 생김 | IAM 정책의 `<ACCOUNT_ID>` 치환 누락 또는 리전 불일치. 정책을 다시 확인 후 `sudo systemctl restart cerberus-backend` |

로그를 보는 기본 명령:

```bash
# 백엔드 로그 (실시간)
journalctl -u cerberus-backend -f

# nginx 오류 로그
sudo tail -f /var/log/nginx/error.log
```

---

## 14. (선택) 도메인 연결 및 HTTPS 적용

IP 주소 대신 도메인(예: `cerberus.example.com`)과 자물쇠(HTTPS)를 쓰려면:

1. 보유한 도메인의 DNS에 **A 레코드**를 추가해 `<서버IP>` 를 가리키게 합니다.
2. 서버에서 무료 인증서를 발급합니다.

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cerberus.example.com
```

3. EC2 보안 그룹에 **HTTPS(443)** 규칙을 추가합니다 (소스: Anywhere).

certbot이 nginx 설정을 자동으로 수정하고 인증서를 90일마다 갱신합니다.

---

## 15. 배포 완료 후 — 가장 먼저 할 일

축하합니다. 배포가 끝났습니다. 곧바로 아래 두 가지를 진행하세요.

### 15-1. 🔴 관리자 비밀번호 변경 (필수)

배포 직후 **관리자 페이지의 기본 비밀번호(`mzcadmin`)가 그대로 노출**되어
있는 상태입니다. 즉시 변경해야 합니다.

1. 브라우저에서 사이트 시작 화면으로 이동
2. **키보드로 `admin` 입력** (또는 케르베로스 첫 번째 머리를 5회 클릭)
3. 비밀번호 입력 모달에 `mzcadmin` 입력 → 관리자 페이지 진입
4. **운영 탭** → **관리자 비밀번호 변경** 섹션에서 새 비밀번호 설정

관리자 페이지의 전체 사용법은 **`ADMIN.md`** 를 참고하세요.

### 15-2. 추가 문서 안내

- 이후 코드를 수정하고 다시 반영하는 방법: **`MAINTENANCE.md`**
- 운영 환경의 보안을 강화하는 방법(데이터 암호화 · 위협 탐지 · DDoS 방어 등): **`SECURITY.md`**
- 관리자 페이지로 문제·설정을 운영 중에 변경하는 방법: **`ADMIN.md`**
