# Cerberus CI/CD 자동 배포 가이드 (GitHub Actions + AWS)

이 문서는 **master 브랜치에 코드를 push 하면 AWS EC2 서버에 자동으로 배포** 되도록
설정하는 절차를 단계별로 안내합니다.

> **전제:** `DEPLOYMENT.md` 에 따라 EC2 배포가 이미 완료된 상태여야 합니다.

---

## 0. 전체 흐름

```
[개발자 PC]                  [GitHub]                    [AWS]
git push master  ───────▶  워크플로 트리거
                            (configure-aws-credentials)  ──▶  IAM OIDC 토큰 발급
                            (ssm send-command)           ──▶  SSM → EC2
                                                               ① git pull
                                                               ② pip install
                                                               ③ npm build
                                                               ④ nginx 정적 배포
                                                               ⑤ 서비스 재시작
                            ◀── 성공 / 실패 결과 수신
```

**장점:**
- GitHub에 AWS 장기 액세스 키를 저장하지 않습니다. (OIDC 임시 토큰 사용)
- EC2에 SSH 포트(22)를 GitHub에 열 필요 없습니다. (SSM을 통해 명령 전달)
- 배포 결과(로그/성공 여부)를 GitHub Actions 화면에서 바로 확인합니다.

**예상 소요 시간:** 약 20~30분

---

## 1. 사전 확인

- 콘솔 오른쪽 위 **리전이 `아시아 태평양(서울) ap-northeast-2`** 인지 확인합니다.
- 이 가이드의 모든 AWS 작업은 `ap-northeast-2` 기준입니다.

---

## STEP 1 — EC2 역할에 SSM 관리 권한 추가

GitHub Actions가 SSM을 통해 EC2에 명령을 보내려면, EC2 인스턴스가 **SSM 관리형
인스턴스(Managed Instance)** 로 등록되어 있어야 합니다. 기존 `cerberus-ec2-role`
에 AWS 관리형 정책 `AmazonSSMManagedInstanceCore` 를 추가합니다.

1. AWS 콘솔 검색창에 **`IAM`** 입력 → IAM으로 이동
2. 왼쪽 메뉴 **`Roles`** → 검색창에 **`cerberus-ec2-role`** 입력 → 클릭
3. **`Permissions`** 탭 → **`Add permissions`** → **`Attach policies`** 클릭
4. 검색창에 **`AmazonSSMManagedInstanceCore`** 입력 → 체크박스 체크
5. **`Add permissions`** 클릭

**확인:** 잠시 후 AWS 콘솔에서 **`SSM`** → 왼쪽 메뉴 **`Fleet Manager`** 로 이동합니다.
`cerberus-server` 가 목록에 **`SSM Agent ping status: Online`** 으로 보이면 완료입니다.

> Amazon Linux 2023에는 SSM Agent가 기본 설치되어 있어 별도 설치가 필요 없습니다.

---

## STEP 2 — GitHub OIDC 공급자 등록 (IAM)

GitHub Actions가 AWS에 로그인할 때 사용하는 **OIDC(OpenID Connect) 공급자**를
AWS 계정에 한 번만 등록합니다. 이미 등록된 경우 이 단계를 건너뜁니다.

1. IAM → 왼쪽 메뉴 **`Identity providers`** 클릭
2. 기존 목록에 `token.actions.githubusercontent.com` 이 있으면 **이 단계 건너뜁니다.**
3. 없으면 **`Add provider`** 클릭 후 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Provider type** | `OpenID Connect` |
| **Provider URL** | `https://token.actions.githubusercontent.com` |
| **Audience** | `sts.amazonaws.com` |

4. **`Add provider`** 클릭

---

## STEP 3 — GitHub Actions용 IAM 역할 생성

GitHub Actions 워크플로에서 사용할 전용 IAM 역할을 만듭니다.
이 역할은 "SSM으로 EC2에 명령을 보내는 것" 만 허용합니다.

### 3-1. 내 AWS 계정 ID 확인

AWS 콘솔 오른쪽 위 계정 이름 클릭 → **12자리 숫자 계정 ID** 메모
(예: `123456789012`)

### 3-2. EC2 인스턴스 ID 확인

AWS 콘솔 **`EC2`** → **`Instances`** → `cerberus-server` 클릭 →
**`Instance ID`** 값 메모 (예: `i-0a1b2c3d4e5f67890`)

### 3-3. 권한 정책(Permission Policy) 만들기

1. IAM → 왼쪽 메뉴 **`Policies`** → **`Create policy`**
2. **`JSON`** 탭 클릭 → 입력창 내용을 모두 지우고, 저장소의
   **`aws/github-deploy-policy.json`** 파일 내용을 붙여넣습니다.
3. 붙여넣은 내용에서 아래 두 자리표시자를 교체합니다.

| 자리표시자 | 교체할 값 |
|---|---|
| `<ACCOUNT_ID>` | 3-1에서 확인한 12자리 계정 ID |
| `<EC2_INSTANCE_ID>` | 3-2에서 확인한 인스턴스 ID (예: `i-0a1b2c3d4e5f67890`) |

4. **`Next`** → 정책 이름에 **`cerberus-github-deploy-policy`** 입력 → **`Create policy`**

### 3-4. 역할(Role) 만들기

1. IAM → 왼쪽 메뉴 **`Roles`** → **`Create role`**
2. **`Trusted entity type`**: **`Web identity`** 선택

3. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Identity provider** | `token.actions.githubusercontent.com` (STEP 2에서 등록한 것) |
| **Audience** | `sts.amazonaws.com` |
| **GitHub organization** | GitHub 사용자명 입력 (예: `ssafyjiyong`) |
| **GitHub repository** | 저장소 이름 입력 (예: `Cerberus`) |
| **GitHub branch** | `master` |

4. **`Next`** 클릭
5. 권한 목록에서 방금 만든 **`cerberus-github-deploy-policy`** 검색 후 체크 → **`Next`**
6. 역할 이름에 **`cerberus-github-deploy-role`** 입력 → **`Create role`**

> **보안 포인트:** `GitHub branch: master` 조건 덕분에 master 브랜치의 워크플로에서만
> 이 역할을 사용할 수 있습니다. 다른 브랜치나 fork된 저장소에서는 사용 불가합니다.

---

## STEP 4 — GitHub Secrets 등록

GitHub Actions 워크플로가 사용할 민감한 값을 저장소 Secrets에 등록합니다.

1. GitHub 저장소 페이지 → 상단 **`Settings`** 탭 클릭
2. 왼쪽 메뉴 **`Secrets and variables`** → **`Actions`** 클릭
3. **`New repository secret`** 버튼을 클릭해 아래 2개를 순서대로 등록합니다.

**첫 번째 Secret:**

| 항목 | 값 |
|---|---|
| **Name** | `AWS_ACCOUNT_ID` |
| **Secret** | 3-1에서 확인한 12자리 계정 ID (예: `123456789012`) |

**`Add secret`** 클릭

**두 번째 Secret:**

| 항목 | 값 |
|---|---|
| **Name** | `EC2_INSTANCE_ID` |
| **Secret** | 3-2에서 확인한 인스턴스 ID (예: `i-0a1b2c3d4e5f67890`) |

**`Add secret`** 클릭

완료 후 Secrets 목록에 `AWS_ACCOUNT_ID` 와 `EC2_INSTANCE_ID` 두 항목이 보이면 됩니다.

---

## STEP 5 — 저장소에 배포 파일 확인

아래 두 파일이 저장소에 이미 포함되어 있는지 확인합니다.
(이 가이드를 따라오셨다면 이미 추가된 상태입니다.)

```
Cerberus/
├── .github/
│   └── workflows/
│       └── deploy.yml        ← GitHub Actions 워크플로 정의
└── scripts/
    └── deploy.sh             ← EC2에서 실행될 실제 배포 스크립트
```

**`deploy.yml`** 이 하는 일:
1. master 브랜치 push 감지
2. OIDC로 AWS 인증
3. SSM을 통해 EC2에 명령 전송
4. 완료 대기 후 결과 로그 출력

**`deploy.sh`** 이 하는 일 (EC2 서버 내):
1. 백엔드 패키지 업데이트 (`pip install`)
2. 프론트엔드 빌드 (`npm run build`)
3. 빌드 결과물을 nginx 서빙 디렉터리에 복사
4. 서비스 재시작 (`cerberus-backend`, `nginx`)

---

## STEP 6 — 첫 번째 자동 배포 실행

모든 설정이 완료되었습니다. 코드를 push 해서 첫 번째 자동 배포를 실행합니다.

### 6-1. 배포 파일 커밋 및 push

로컬 PC의 터미널에서:

```bash
cd <로컬_저장소_경로>

# 새 파일 스테이징
git add .github/workflows/deploy.yml scripts/deploy.sh aws/github-deploy-policy.json

# 커밋
git commit -m "ci: GitHub Actions 자동 배포 설정 추가"

# push — 이 순간 자동 배포가 트리거됩니다
git push origin master
```

### 6-2. 배포 진행 상황 확인

1. GitHub 저장소 페이지 → 상단 **`Actions`** 탭 클릭
2. 방금 push한 커밋에 해당하는 워크플로 실행이 목록에 나타납니다.
3. 클릭하면 각 단계별 진행 상황을 실시간으로 볼 수 있습니다.

| 단계 | 내용 |
|---|---|
| `AWS 자격 증명 구성` | OIDC 토큰 발급 (수 초) |
| `SSM 배포 명령 전송` | EC2에 명령 전달 (수 초) |
| `배포 완료 대기` | EC2의 빌드·배포 완료 대기 (1~3분) |
| `배포 로그 출력` | EC2 서버의 실행 로그 출력 |
| `배포 성공 여부 검사` | `✅ 배포 성공!` 메시지 확인 |

### 6-3. 정상 배포 확인

- 워크플로 모든 단계가 **초록색 체크** 이면 배포 성공입니다.
- 브라우저에서 서버 주소로 접속해 게임이 정상 동작하는지 확인합니다.

---

## 문제 해결

| 증상 | 원인 및 해결 방법 |
|---|---|
| `Error assuming role` | OIDC 공급자 미등록(STEP 2) 또는 역할 신뢰 정책에서 GitHub 사용자명/저장소명 오탈자. STEP 3-4의 신뢰 정책 조건을 재확인 |
| `An error occurred (InvalidInstanceId)` | EC2 인스턴스 ID 오류 또는 인스턴스가 중지 상태. EC2_INSTANCE_ID Secret 값 확인 |
| `배포 완료 대기` 단계에서 타임아웃 | ① EC2 역할에 `AmazonSSMManagedInstanceCore` 미부여(STEP 1 재확인) ② SSM Fleet Manager에서 인스턴스가 Online 상태인지 확인 |
| `배포 로그`에서 `Permission denied` | `scripts/deploy.sh` 에 실행 권한 없음. EC2에서 `chmod +x /opt/cerberus/scripts/deploy.sh` 실행 |
| `배포 로그`에서 `git pull` 오류 | 저장소가 비공개인 경우, 아래 '비공개 저장소 인증 설정' 참고 |
| `npm: command not found` | Node.js 미설치. EC2에서 `DEPLOYMENT.md` STEP 5 재실행 |
| `배포 성공 여부 검사` 에서 `Failed` | 위 단계의 로그에서 오류 내용 확인 후 수정하여 재push |

**EC2에서 직접 로그 확인:**

```bash
# 마지막으로 실행된 SSM 명령 로그
sudo cat $(ls -t /var/lib/amazon/ssm/*/document/orchestration/*/awsrunShellScript/0.awsrunShellScript/stdout 2>/dev/null | head -1)

# 백엔드 서비스 로그
journalctl -u cerberus-backend -n 50

# nginx 오류 로그
sudo tail -20 /var/log/nginx/error.log
```

---

## (선택) 비공개(Private) 저장소 인증 설정

저장소가 비공개인 경우, EC2의 `git pull` 이 GitHub에 인증할 방법이 필요합니다.
아래 중 한 가지를 선택하세요.

### 방법 A — 배포 키(Deploy Key) 사용 (권장)

EC2 서버에서 한 번 설정하면 영구적으로 사용할 수 있습니다.

**① EC2 서버에서 SSH 키 쌍 생성**

```bash
sudo -u ec2-user ssh-keygen -t ed25519 \
  -f /home/ec2-user/.ssh/github_deploy \
  -C "cerberus-deploy-key" \
  -N ""
```

**② 공개 키 복사**

```bash
cat /home/ec2-user/.ssh/github_deploy.pub
```

출력된 내용(한 줄) 전체를 복사합니다.

**③ GitHub에 배포 키 등록**

1. GitHub 저장소 → **`Settings`** → **`Deploy keys`** → **`Add deploy key`**
2. Title: `cerberus-ec2-deploy`
3. Key: 위에서 복사한 공개 키 붙여넣기
4. `Allow write access`: **체크 안 함** (읽기 전용으로 충분)
5. **`Add key`** 클릭

**④ EC2 SSH 설정 파일 수정**

```bash
cat >> /home/ec2-user/.ssh/config << 'EOF'
Host github.com
    IdentityFile ~/.ssh/github_deploy
    StrictHostKeyChecking no
EOF
sudo chown ec2-user:ec2-user /home/ec2-user/.ssh/config
sudo chmod 600 /home/ec2-user/.ssh/config
```

**⑤ git remote URL을 SSH 방식으로 변경**

```bash
cd /opt/cerberus
sudo -u ec2-user git remote set-url origin git@github.com:ssafyjiyong/Cerberus.git
```

**⑥ 동작 확인**

```bash
sudo -u ec2-user git pull origin master
```

오류 없이 `Already up to date.` 또는 변경 내용이 pull 되면 완료입니다.

---

### 방법 B — Personal Access Token (PAT) 사용

GitHub 토큰을 EC2 git 설정에 저장하는 방법입니다.

**① GitHub에서 PAT 발급**

1. GitHub → 오른쪽 위 프로필 → **`Settings`**
2. 왼쪽 메뉴 맨 아래 **`Developer settings`** → **`Personal access tokens`** → **`Tokens (classic)`**
3. **`Generate new token (classic)`** 클릭
4. Note: `cerberus-ec2-pull`, Expiration: `No expiration` (또는 원하는 기간)
5. 권한 범위: **`repo`** 체크 (비공개 저장소 접근)
6. **`Generate token`** 클릭 → 발급된 토큰(`ghp_...`) 복사 (페이지를 벗어나면 다시 볼 수 없음)

**② EC2에 저장**

```bash
# <TOKEN> 을 위에서 복사한 토큰으로 교체
sudo -u ec2-user git -C /opt/cerberus remote set-url origin \
  https://<TOKEN>@github.com/ssafyjiyong/Cerberus.git
```

**③ 동작 확인**

```bash
sudo -u ec2-user git -C /opt/cerberus pull origin master
```

---

## 이후 배포 방법

설정이 완료되면, 앞으로 배포는 단 한 줄입니다.

```bash
git push origin master
```

GitHub Actions가 자동으로 감지하고, 약 2~4분 후 EC2 서버에 반영됩니다.
배포 상태는 저장소의 **Actions** 탭에서 언제든지 확인할 수 있습니다.
