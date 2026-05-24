# Cerberus 보안 설정 가이드 (AWS)

이 문서는 **DEPLOYMENT.md 배포 완료 후**, 보안을 강화하는 절차를 단계별로 안내합니다.
위에서부터 순서대로, 한 단계도 건너뛰지 말고 진행하세요.

> **전제:** `DEPLOYMENT.md` 에 따라 EC2 + nginx 구성으로 이미 배포된 상태여야 합니다.

---

## 0. 무엇을 하게 되나요?

| 순서 | 작업 | 난이도 | 비용 |
|---|---|---|---|
| **0** | **관리자 비밀번호 변경 (필수)** | 매우 쉬움 | 무료 |
| **1** | **DynamoDB PITR 활성화** (데이터 백업) | 매우 쉬움 | 소액 |
| **2** | **GuardDuty 활성화** (위협 탐지) | 매우 쉬움 | 소액 |
| **3** | **Security Hub 활성화** (보안 대시보드) | 매우 쉬움 | 소액 |
| **4** | **CloudTrail 추적 생성** (API 로그) | 쉬움 | 소액 |
| **5** | **Amazon Inspector 활성화** (취약점 스캔) | 쉬움 | 소액 |
| **6** | **KMS 키 생성 + DynamoDB/EBS 암호화** | 보통 | 소액 |
| **7** | **CloudFront + WAF + HTTPS 구성** | 보통 | 소액~중간 |
| **추가A** | **AWS Config 활성화** (리소스 설정 변경 이력) | 쉬움 | 소액 |
| **추가B** | **VPC 엔드포인트** (DynamoDB·Bedrock 비공개 통신) | 쉬움 | 소액 |

> 0~5번은 대부분 콘솔에서 활성화 버튼만 누르면 되며, 먼저 적용할수록 좋습니다.

---

## STEP 0 — 관리자 비밀번호 변경 (필수)

배포 직후 기본 비밀번호 `mzcadmin` 이 그대로 노출된 상태입니다. **가장 먼저** 변경하세요.

1. 브라우저에서 사이트 시작 화면으로 이동합니다.
2. **키보드로 `admin` 입력** (또는 케르베로스 첫 번째 머리를 5회 클릭)
3. 비밀번호 입력창에 `mzcadmin` 입력 → 관리자 페이지 진입
4. 상단 탭에서 **운영** 클릭 → 하단 **관리자 비밀번호 변경** 섹션에서 새 비밀번호 설정
   - 8자 이상, 영문 + 숫자 + 특수문자 조합을 권장합니다.
5. **변경** 버튼 클릭 → "비밀번호가 변경되었습니다" 메시지 확인

> 관리자 페이지의 전체 사용법은 `ADMIN.md` 를 참고하세요.

---

## STEP 1 — DynamoDB PITR 활성화 (데이터 백업)

PITR(Point-in-time recovery)을 켜면 최근 35일 이내 어느 시점으로든 데이터를 복구할 수 있습니다.
아래 3개 테이블 모두에 적용합니다.

- `cerberus-leaderboard`
- `cerberus-leaderboard-logs`
- `cerberus-leaderboard-config` ← 문제 세트·관리자 설정이 들어 있으므로 특히 중요

**각 테이블마다 아래 절차를 반복합니다 (3회):**

1. AWS 콘솔 검색창에 **`DynamoDB`** 입력 → DynamoDB로 이동
2. 왼쪽 메뉴 **`Tables`** 클릭 → 테이블 이름 클릭
3. 상단 탭 중 **`Backups`** 클릭
4. **`Enable`** 버튼 클릭 (Point-in-time recovery 항목 옆)
5. "PITR is enabled" 상태가 되면 완료

---

## STEP 2 — GuardDuty 활성화 (위협 탐지)

AWS API 호출·네트워크 트래픽을 머신러닝으로 분석해 비정상 행위(악성 IP 통신, 암호화폐 채굴, 비정상 API 호출 등)를 자동 탐지합니다.

1. AWS 콘솔 검색창에 **`GuardDuty`** 입력 → GuardDuty로 이동
2. 화면 중앙의 **`Get Started`** 버튼 클릭
3. **`Enable GuardDuty`** 버튼 클릭

이것으로 완료입니다. 탐지 결과는 STEP 3의 Security Hub와 자동으로 연동됩니다.

> 30일 무료 평가판이 제공됩니다. 이후 분석 데이터양에 따라 소액 과금됩니다.

---

## STEP 3 — Security Hub 활성화 (보안 통합 대시보드)

GuardDuty·Inspector 등의 탐지 결과를 한 곳에서 보고, 계정 설정의 보안 점수를 자동으로 점검합니다.

1. AWS 콘솔 검색창에 **`Security Hub`** 입력 → Security Hub로 이동
2. **`Go to Security Hub`** 버튼 클릭
3. **보안 표준 선택** 화면에서 아래 항목을 체크합니다.
   - ✅ `AWS Foundational Security Best Practices` (권장)
   - ✅ `CIS AWS Foundations Benchmark` (선택, ISMS 항목과 유사)
4. **`Enable Security Hub`** 버튼 클릭

이후 콘솔에서 보안 점수와 미흡 항목을 확인할 수 있습니다.

---

## STEP 4 — CloudTrail 추적 생성 (API 로그)

"누가, 언제, 무슨 AWS API를 호출했는가"를 기록해 사고 조사와 감사 증적을 확보합니다.

1. AWS 콘솔 검색창에 **`CloudTrail`** 입력 → CloudTrail로 이동
2. 왼쪽 메뉴 **`Trails`** → **`Create trail`** 클릭
3. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Trail name** | `cerberus-trail` |
| **Storage location** | `Create new S3 bucket` 선택 → 이름 자동 생성 또는 직접 입력 (예: `cerberus-trail-로그`) |
| **Log file SSE-KMS encryption** | 일단 `Disabled` (KMS 설정 후 STEP 6에서 활성화 가능) |
| **Log file validation** | `Enabled` ← 로그 무결성 검증, 켜두는 것을 권장 |
| **CloudWatch Logs** | `Enabled` → **New** 선택, 로그 그룹 이름 `cerberus-cloudtrail` → IAM 역할 `New` 선택 → 자동 생성 이름 그대로 사용 |

4. **`Next`** 클릭 → **이벤트 유형 선택** 에서 기본값(`Management events`) 유지 → **`Next`**
5. 설정 요약 확인 후 **`Create trail`** 클릭

---

## STEP 5 — Amazon Inspector 활성화 (EC2 취약점 스캔)

EC2 인스턴스의 OS와 설치된 패키지에서 알려진 취약점(CVE)을 지속 스캔합니다.

1. AWS 콘솔 검색창에 **`Inspector`** 입력 → Amazon Inspector로 이동
2. **`Get started`** 버튼 클릭
3. **`Activate Inspector`** 버튼 클릭

Inspector가 계정 내 EC2 인스턴스를 자동 발견해 스캔을 시작합니다. 탐지 결과는 Security Hub와 자동 연동됩니다.

> Amazon Linux 2023에는 SSM Agent가 기본 설치되어 있어 별도 에이전트 없이 동작합니다.

---

## STEP 6 — KMS 키 생성 + DynamoDB / EBS 암호화

게임 로그·랭킹·관리자 설정 데이터를 **고객 관리형 키(CMK)** 로 암호화합니다.

### 6-1. KMS 키 만들기

1. AWS 콘솔 검색창에 **`KMS`** 입력 → Key Management Service로 이동
2. 왼쪽 메뉴 **`Customer managed keys`** → **`Create key`** 클릭

**[Step 1: Configure key]**

| 항목 | 설정값 |
|---|---|
| **Key type** | `Symmetric` (대칭키 — 암호화·복호화 모두에 사용) |
| **Key usage** | `Encrypt and decrypt` |
| **Advanced options** | 기본값 그대로 유지 (`KMS` / `Single-Region key`) |

**`Next`** 클릭

**[Step 2: Add labels]**

| 항목 | 설정값 |
|---|---|
| **Alias** | `cerberus-key` |
| **Description** | `Cerberus DynamoDB encryption key` (선택 사항) |
| **Tags** | 입력하지 않아도 됩니다 |

**`Next`** 클릭

**[Step 3: Define key administrative permissions]**

이 화면은 "이 키 자체를 관리(삭제·정책 변경 등)할 수 있는 IAM 사용자/역할"을 지정합니다.

1. 검색창에 현재 콘솔에 로그인한 **IAM 사용자 이름**을 입력합니다.
   - 콘솔 오른쪽 위 계정 이름을 클릭하면 현재 IAM 사용자 이름을 확인할 수 있습니다.
   - 루트 계정으로 로그인 중이라면 아무것도 선택하지 않아도 루트는 항상 키를 관리할 수 있습니다.
2. 검색 결과에서 해당 사용자 **체크박스에 체크** 합니다.
3. 하단 **`Allow key administrators to delete this key`** 체크박스는 **체크된 상태 유지**합니다.

> **데모 용도이므로** 별도의 키 관리자 계정이나 조직 정책 연동은 필요 없습니다.
> 현재 작업 중인 IAM 사용자(또는 루트)를 키 관리자로 지정하면 충분합니다.

**`Next`** 클릭

**[Step 4: Define key usage permissions]**

이 화면은 "이 키로 실제 데이터를 암호화·복호화할 수 있는 IAM 사용자/역할"을 지정합니다.
EC2가 DynamoDB에 접근할 때 이 키를 사용해야 하므로, EC2 역할을 추가합니다.

1. 검색창에 **`cerberus-ec2-role`** 을 입력합니다.
2. 검색 결과에서 **`cerberus-ec2-role`** 체크박스에 체크합니다.

**`Next`** 클릭

**[Step 5: Review]**

설정 요약을 확인하고 **`Finish`** 클릭합니다.

완료 후 키 목록에서 **`cerberus-key`** 를 클릭해 상세 페이지를 엽니다.
**`General configuration`** 섹션의 **`Key ARN`** 값을 복사해 메모장에 붙여넣으세요.
(형식 예시: `arn:aws:kms:ap-northeast-2:123456789012:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

---

### 6-2. IAM 정책에 KMS 키 ARN 등록

EC2 서버가 암호화된 DynamoDB 테이블을 읽고 쓸 수 있도록, 기존 IAM 정책을 업데이트합니다.

1. AWS 콘솔에서 **`IAM`** → 왼쪽 **`Policies`** → **`cerberus-policy`** 검색 후 클릭
2. **`Edit`** 버튼 클릭 → **`JSON`** 탭 클릭
3. JSON 본문에서 `"KMSForEncryptedTables"` 구문을 찾아 `<KMS_KEY_ARN>` 부분을
   위에서 복사한 키 ARN으로 교체합니다.
4. **`Next`** → **`Save changes`** 클릭

---

### 6-3. DynamoDB 테이블 암호화 방식 변경

아래 3개 테이블 모두에 적용합니다. **각 테이블마다 반복합니다 (3회).**

1. AWS 콘솔에서 **`DynamoDB`** → **`Tables`** → 테이블 이름 클릭
2. 상단 탭 중 **`Additional settings`** 클릭
3. **`Encryption`** 섹션 → **`Manage encryption`** 클릭
4. 아래와 같이 선택합니다.

| 항목 | 설정값 |
|---|---|
| **Encryption type** | `Stored in your account, owned and managed by you` 선택 |
| **KMS key** | `Choose a different AWS KMS key` → `cerberus-key` 검색 후 선택 |

5. **`Save changes`** 클릭

대상 테이블:
- `cerberus-leaderboard`
- `cerberus-leaderboard-logs`
- `cerberus-leaderboard-config` ← 관리자 비밀번호 해시가 저장되므로 특히 중요

---

### 6-4. EC2 EBS 볼륨 암호화 (선택)

현재 EC2 인스턴스에 연결된 EBS 볼륨이 암호화되어 있는지 확인합니다.

1. AWS 콘솔에서 **`EC2`** → 왼쪽 메뉴 **`Volumes`** 클릭
2. `cerberus-server` 와 연결된 볼륨을 클릭 → **`Encryption`** 항목 확인
   - 이미 암호화되어 있으면 완료입니다.
   - 암호화되어 있지 않으면 아래 절차를 따릅니다.

**암호화되지 않은 기존 볼륨 교체 방법:**

```
① 볼륨 선택 → 우클릭(또는 Actions) → [Create snapshot]
   Snapshot 이름: cerberus-server-snap

② EC2 콘솔 왼쪽 메뉴 [Snapshots] → 방금 만든 스냅샷 선택
   → Actions → [Copy snapshot]
   → [Encryption] 체크 → KMS key: cerberus-key 선택 → [Copy snapshot]

③ 암호화된 새 스냅샷에서 → Actions → [Create volume from snapshot]
   → 원래 볼륨과 동일한 AZ(가용 영역) 선택 → [Create volume]

④ EC2 인스턴스 중지(Stop) → 기존 볼륨 분리(Detach) → 새 볼륨 연결(Attach, /dev/xvda)
   → 인스턴스 시작(Start)
```

> 새 EC2 인스턴스를 만들 때는 **`Advanced`** 설정에서 `Encrypted: Yes` 를 선택하면
> 처음부터 암호화된 볼륨이 생성됩니다.

---

## STEP 7 — CloudFront + WAF + HTTPS 구성

> **중요:** AWS WAF는 EC2에 직접 붙지 않습니다. 앞단에 **CloudFront** 가 있어야 합니다.
> CloudFront를 두면 WAF · HTTPS · DDoS 방어 · 캐싱을 한 번에 얻습니다.

### 7-1. ACM 인증서 발급 (HTTPS용)

> ⚠️ CloudFront용 인증서는 반드시 **`us-east-1 (버지니아 북부)`** 리전에서 발급해야 합니다.
> 이것은 AWS의 고정 사양입니다. 다른 리전에서 발급한 인증서는 CloudFront에 연결되지 않습니다.

1. AWS 콘솔 오른쪽 위 리전 선택 드롭다운에서 **`US East (N. Virginia) us-east-1`** 로 변경합니다.
2. 검색창에 **`Certificate Manager`** 입력 → ACM으로 이동
3. **`Request a certificate`** 클릭
4. **`Request a public certificate`** 선택 → **`Next`**
5. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Fully qualified domain name** | 사용할 도메인 입력 (예: `cerberus.example.com`) |
| **Validation method** | `DNS validation` 권장 |
| **Key algorithm** | `RSA 2048` (기본값 그대로) |

6. **`Request`** 클릭 → 인증서가 `Pending validation` 상태로 생성됨
7. 인증서를 클릭 → **`Domains`** 섹션의 **CNAME 이름 · 값**을 복사해
   도메인 등록 업체의 DNS 관리 화면에서 CNAME 레코드를 추가합니다.
8. DNS 전파 후 (수 분~1시간) 인증서 상태가 **`Issued`** 로 변경됩니다.

> 도메인이 없고 IP 주소만 사용하는 경우, 이 단계를 건너뜁니다.
> CloudFront는 도메인 없이도 생성되며 HTTP→HTTPS 리디렉션만 불가합니다.

### 7-2. CloudFront 배포 생성

> ACM 인증서 발급 후 리전을 다시 **`ap-northeast-2 (서울)`** 로 돌려도 됩니다.
> CloudFront는 글로벌 서비스이므로 어느 리전에서 접근해도 같습니다.

1. AWS 콘솔 검색창에 **`CloudFront`** 입력 → CloudFront로 이동
2. **`Create distribution`** 클릭
3. 아래와 같이 설정합니다.

**Origin 설정:**

| 항목 | 설정값 |
|---|---|
| **Origin domain** | EC2의 퍼블릭 DNS 이름 입력 (예: `ec2-13-x-x-x.ap-northeast-2.compute.amazonaws.com`) |
| **Protocol** | `HTTP only` (EC2 앞단에는 HTTP로 통신, CloudFront가 사용자와의 HTTPS 처리) |
| **HTTP port** | `80` |

**Default cache behavior 설정:**

| 항목 | 설정값 |
|---|---|
| **Viewer protocol policy** | `Redirect HTTP to HTTPS` (HTTP 접속 시 자동으로 HTTPS로 전환) |
| **Allowed HTTP methods** | `GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE` (API 포함이므로 전체 허용) |
| **Cache policy** | `CachingDisabled` (동적 API 서버이므로 캐시 비활성화 권장) |

**Settings:**

| 항목 | 설정값 |
|---|---|
| **Alternate domain name (CNAME)** | 도메인이 있으면 입력 (예: `cerberus.example.com`), 없으면 빈칸 |
| **Custom SSL certificate** | 7-1에서 발급한 ACM 인증서 선택 (도메인이 있는 경우) |
| **Default root object** | `index.html` |

4. **`Create distribution`** 클릭
5. 배포 상태가 **`Enabled`** 가 되면 완료 (최대 10~15분 소요).
   **`Distribution domain name`** (예: `d1234abcd.cloudfront.net`) 을 메모합니다.

### 7-3. WAF Web ACL 생성 및 CloudFront에 연결

1. AWS 콘솔 검색창에 **`WAF`** 입력 → WAF & Shield로 이동
2. 왼쪽 메뉴 **`AWS WAF`** → **`Web ACLs`** → **`Create web ACL`** 클릭
3. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Resource type** | `Amazon CloudFront distributions` |
| **Name** | `cerberus-waf` |
| **Region** | `Global (CloudFront)` (자동 선택됨) |

4. **`Add AWS resources`** 클릭 → 7-2에서 만든 CloudFront 배포 선택 → **`Add`**
5. **`Next`** 클릭 → **규칙 추가** 화면에서 **`Add rules`** → **`Add managed rule groups`** 클릭
6. 아래 관리형 규칙을 펼쳐서 각각 **`Add to web ACL`** 토글을 켭니다.

| 규칙 그룹 | 역할 |
|---|---|
| `AWS managed rule groups` > **`Core rule set`** | XSS 등 일반적인 웹 공격 차단 |
| `AWS managed rule groups` > **`SQL database`** | SQL 인젝션 차단 |
| `AWS managed rule groups` > **`Amazon IP reputation list`** | 악성 IP 평판 기반 차단 |

7. **`Add rules`** 클릭
8. **`Add rules`** 버튼을 다시 클릭 → **`Add my own rules and rule groups`** 선택
9. **`Rate-based rule`** 선택 후 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Name** | `rate-limit-per-ip` |
| **Rate limit** | `1000` (5분간 동일 IP에서 1,000회 이상 요청 차단) |
| **IP address to use for rate limiting** | `Source IP address` |

10. **`Add rule`** → **`Next`** → **`Next`** → **`Next`** → **`Create web ACL`** 클릭

### 7-4. EC2 보안 그룹 — CloudFront 경유 강제

CloudFront를 거치지 않고 EC2 IP 주소로 직접 접속하는 것을 막습니다.

1. AWS 콘솔에서 **`EC2`** → 왼쪽 메뉴 **`Security Groups`** → `cerberus-server` 에 연결된 보안 그룹 클릭
2. **`Inbound rules`** 탭 → **`Edit inbound rules`** 클릭
3. 기존 **HTTP (포트 80)** 규칙을 찾아 **소스(Source)** 를 아래와 같이 변경합니다.

| 유형 | 포트 | 소스 |
|---|---|---|
| HTTP | 80 | `Prefix list` → `com.amazonaws.global.cloudfront.origin-facing` 검색 후 선택 |

4. **`Save rules`** 클릭

이제 사용자는 반드시 CloudFront → WAF를 거쳐야 EC2에 접근할 수 있습니다.

> 도메인이 있다면 DNS의 A 레코드(또는 CNAME)를 CloudFront 도메인으로 변경하세요.

---

## STEP 8 — Shield (DDoS 방어)

별도 설정 없이 **자동 적용**됩니다. CloudFront를 도입하면 AWS Shield Standard(무료)가
네트워크 계층(L3/L4) DDoS 공격을 자동 방어합니다.
애플리케이션 계층(L7) 공격은 STEP 7의 **WAF rate-based rule** 이 보완합니다.

> Shield Advanced(월 $3,000)는 데모 수준에서는 불필요합니다.

---

## 추가A — AWS Config 활성화 (리소스 설정 변경 이력)

CloudTrail이 "누가 무슨 API를 호출했는가"를 기록한다면, **AWS Config**는
"리소스 설정이 언제 어떻게 바뀌었는가"의 이력을 저장하고 컴플라이언스 규칙을
자동 평가합니다. ISMS 감사 증적으로 CloudTrail과 함께 활용하면 좋습니다.

> **CloudTrail과의 차이:**
> - CloudTrail: `ec2-user 가 2025-01-01 14:00에 보안 그룹을 수정하는 API를 호출했다`
> - AWS Config: `보안 그룹 sg-xxx의 인바운드 규칙이 [이전값] → [이후값] 으로 변경됐다`

### A-1. S3 버킷 생성 (Config 로그 저장용)

CloudTrail용 버킷과 분리해서 만들거나, 같은 버킷에 접두사(Prefix)를 달아 저장할 수
있습니다. 여기서는 별도 버킷을 만드는 방법으로 안내합니다.

1. AWS 콘솔 검색창에 **`S3`** 입력 → S3로 이동 → **`Create bucket`** 클릭
2. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Bucket name** | `cerberus-config-logs-<계정ID>` (S3 버킷 이름은 전 세계 고유해야 함) |
| **AWS Region** | `아시아 태평양(서울) ap-northeast-2` |
| **Block Public Access** | 기본값 유지 (모두 차단) |
| **Versioning** | `Enable` 권장 (로그 무결성) |
| **Server-side encryption** | `SSE-S3` 또는 `SSE-KMS` (KMS 설정 완료 시 `cerberus-key` 선택) |

3. **`Create bucket`** 클릭

### A-2. AWS Config 활성화

1. AWS 콘솔 검색창에 **`Config`** 입력 → AWS Config로 이동
2. **`Get started`** 클릭 (처음 사용하는 경우) 또는 왼쪽 메뉴 **`Settings`**
3. 아래와 같이 설정합니다.

**Resource types to record:**

| 항목 | 설정값 |
|---|---|
| **Recording strategy** | `All resource types` 선택 (권장) |
| **Recording frequency** | `Continuous` (변경 발생 즉시 기록) |

**Delivery method (로그 전달 위치):**

| 항목 | 설정값 |
|---|---|
| **Amazon S3 bucket** | `Choose a bucket from your account` → A-1에서 만든 버킷 선택 |
| **S3 key prefix** | `config` 입력 (버킷 내 폴더 구분용, 선택 사항) |
| **Amazon SNS topic** | 일단 `None` (알림 필요 시 나중에 추가) |

**AWS Config rules (선택 — 컴플라이언스 자동 평가):**

규칙을 추가하면 리소스가 기준에 맞는지 자동 검사합니다. 아래 규칙을 추가하면
데모 환경에서 ISMS 관련 항목을 자동 점검할 수 있습니다.

| 규칙 이름 | 점검 내용 |
|---|---|
| `dynamodb-pitr-enabled` | DynamoDB PITR 활성화 여부 |
| `dynamodb-table-encrypted-kms` | DynamoDB KMS 암호화 여부 |
| `cloudtrail-enabled` | CloudTrail 활성화 여부 |
| `guardduty-enabled-centralized` | GuardDuty 활성화 여부 |
| `root-mfa-enabled` | 루트 계정 MFA 설정 여부 |

4. 설정 완료 후 **`Confirm`** 클릭

> Config가 시작되면 현재 리소스 상태를 전부 스냅샷하고 이후 변경을 추적합니다.
> 처음 몇 분간 비용이 다소 높게 나타날 수 있으며, 이후 안정됩니다.

---

## 추가B — VPC 엔드포인트 설정 (서브넷 분리 대안)

### 왜 VPC 엔드포인트인가?

"백엔드를 Private 서브넷으로 분리해야 하지 않나요?" — 완전히 맞는 방향입니다.
그러나 현재 구조(단일 EC2에 nginx + FastAPI 동거)에서 **진짜 Private 서브넷 분리**를
구현하려면 아래가 필요합니다.

```
올바른 Public/Private 분리 구조
────────────────────────────────────────────────
[Public Subnet]
  Application Load Balancer (포트 80/443)
        │
[Private Subnet]
  EC2 (FastAPI만, 인터넷 직접 연결 없음)
  NAT Gateway ← EC2의 외부 통신 경유 (Bedrock, pip, npm, git pull 등)
```

이 구조는 인프라를 새로 설계하는 것이므로 **데모 단독으로는 과도하며**,
NAT Gateway 비용($0.045/시간 ≈ 월 $35)이 고정으로 추가됩니다.

**실용적 대안:** EC2 → DynamoDB, EC2 → Bedrock 통신이 인터넷 공용망을 경유하지 않고
AWS 내부 네트워크를 통하도록 **VPC 엔드포인트** 를 설정합니다. NAT Gateway 없이도
트래픽이 AWS 내부에서 끝납니다.

> **현재 보안 수준 참고:**
> - FastAPI는 이미 `127.0.0.1:8000` 에만 바인딩 → 외부에서 포트 8000 직접 접근 불가
> - 보안 그룹: 포트 80(또는 CloudFront 프리픽스)만 허용
> - VPC 엔드포인트를 추가하면 AWS 서비스 통신 경로까지 비공개화

### B-1. DynamoDB VPC 엔드포인트 생성

1. AWS 콘솔 검색창에 **`VPC`** 입력 → VPC로 이동
2. 왼쪽 메뉴 **`Endpoints`** → **`Create endpoint`** 클릭
3. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Name tag** | `cerberus-dynamo-endpoint` |
| **Service category** | `AWS services` |
| **Services** 검색 | `dynamodb` 입력 → `com.amazonaws.ap-northeast-2.dynamodb` 선택 |
| **Type** | `Gateway` (DynamoDB는 Gateway 타입, 무료) |
| **VPC** | EC2가 속한 VPC 선택 (기본 VPC) |
| **Route tables** | EC2 서브넷의 라우트 테이블 체크 |

4. **`Create endpoint`** 클릭

### B-2. Bedrock VPC 엔드포인트 생성

1. VPC 콘솔 → **`Endpoints`** → **`Create endpoint`** 클릭
2. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Name tag** | `cerberus-bedrock-endpoint` |
| **Service category** | `AWS services` |
| **Services** 검색 | `bedrock-runtime` 입력 → `com.amazonaws.ap-northeast-2.bedrock-runtime` 선택 |
| **Type** | `Interface` (Bedrock은 Interface 타입, 소액 과금) |
| **VPC** | EC2가 속한 VPC 선택 |
| **Subnets** | EC2가 있는 서브넷 선택 |
| **Security groups** | EC2의 보안 그룹 선택 |
| **Private DNS names enabled** | `Enable` 체크 (코드 변경 없이 기존 SDK 엔드포인트 URL 그대로 사용) |

3. **`Create endpoint`** 클릭

> Interface 엔드포인트 비용: ENI당 약 $0.01/시간 ≈ 월 $7 수준.
> "Private DNS enabled" 를 켜면 애플리케이션 코드나 `.env` 변경 없이 즉시 적용됩니다.

---

## 추가C — VPC Flow Logs 설정 (선택)

네트워크 트래픽 기록이 필요하다면 아래 절차로 활성화합니다.

1. AWS 콘솔에서 **`VPC`** 이동 → 왼쪽 메뉴 **`Your VPCs`** → 해당 VPC 선택
2. 하단 탭 **`Flow logs`** → **`Create flow log`** 클릭
3. 아래와 같이 설정합니다.

| 항목 | 설정값 |
|---|---|
| **Filter** | `All` (수락·거부 트래픽 모두 기록) |
| **Destination** | `Send to CloudWatch Logs` 권장 |
| **Log group** | `cerberus-vpc-flow` (새로 생성) |
| **IAM role** | `New IAM role` 선택 → 자동 생성 이름 그대로 사용 |

4. **`Create flow log`** 클릭

---

## 완료 확인 체크리스트

아래 항목을 모두 확인하면 보안 설정이 완료됩니다.

- [ ] STEP 0: 관리자 기본 비밀번호 `mzcadmin` 변경 완료
- [ ] STEP 1: DynamoDB 3개 테이블 모두 PITR `Enabled` 상태 확인
- [ ] STEP 2: GuardDuty 콘솔에서 `Enabled` 상태 확인
- [ ] STEP 3: Security Hub 콘솔에서 보안 점수 확인
- [ ] STEP 4: CloudTrail > Trails 목록에 `cerberus-trail` 존재 확인
- [ ] STEP 5: Inspector 콘솔에서 EC2 인스턴스 스캔 시작 확인
- [ ] STEP 6: KMS `cerberus-key` 생성, DynamoDB 3개 테이블 암호화 유형이 `AWS owned key` → `Customer managed key` 로 변경됨 확인
- [ ] STEP 7: CloudFront 배포 `Enabled`, WAF Web ACL 연결 확인, EC2 보안 그룹 HTTP 소스가 CloudFront 프리픽스로 변경됨 확인
- [ ] 추가A: AWS Config 콘솔에서 리소스 기록 시작 확인, S3 버킷에 로그 파일 생성 확인
- [ ] 추가B: VPC 콘솔 Endpoints 목록에 `cerberus-dynamo-endpoint`(Gateway), `cerberus-bedrock-endpoint`(Interface) 상태 `Available` 확인

---

## 비용 참고

| 서비스 | 데모 수준 예상 비용 |
|---|---|
| GuardDuty | 월 $1~5 (트래픽 소량) |
| Security Hub | 월 $1~3 |
| CloudTrail | S3 저장 비용 월 $1 내외 |
| Inspector | 월 $1~3 |
| KMS (cerberus-key) | 월 $1 (키 1개) |
| DynamoDB PITR | 월 $0.2/GB (데이터 소량) |
| CloudFront | 월 $1~5 (트래픽 소량) |
| WAF | 월 $5~10 (Web ACL + 규칙 기본료) |
| AWS Config | 월 $2~5 (기록 항목 수 기반) |
| VPC 엔드포인트 (Bedrock Interface) | 월 $7 내외 (ENI 1개) |
| VPC 엔드포인트 (DynamoDB Gateway) | 무료 |
| **합계 (추정, 추가 항목 포함)** | **월 $20~50** |

> AWS Budgets에서 월 예산 알림을 설정해 두면 예상치 못한 과금을 방지할 수 있습니다.
> 콘솔 검색창에 `Budgets` 검색 → `Create budget` → `Monthly cost budget` → 한도 금액 입력.
