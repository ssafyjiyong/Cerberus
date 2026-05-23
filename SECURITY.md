# Cerberus 보안 아키텍처 가이드 (AWS)

Cerberus는 **ISMS 정보보호 인증 심사**를 주제로 한 프로젝트입니다. 따라서
애플리케이션이 올라가는 배포 환경 자체도 AWS 보안 모범사례를 반영하는 것이
바람직합니다. 이 문서는 어떤 AWS 보안 서비스를 **이 프로젝트에 실제로 적용할
가치가 있는지** 우선순위별로 정리하고, 단계별 적용 방법을 안내합니다.

> 전제: `DEPLOYMENT.md` 에 따라 단일 EC2 + nginx 구성으로 배포된 상태.

---

## 0. 핵심 원칙 — 규모에 맞는 보안

요청된 보안 서비스 목록에는 **단일 애플리케이션용 서비스**와 **조직(다계정)
전체를 관리하는 거버넌스 서비스**가 섞여 있습니다. 데모 앱 하나에 조직용
서비스(Control Tower, Landing Zone 등)를 새로 구축하는 것은 과도하며, 비용과
운영 부담만 늘립니다. 그래서 두 단계로 구분합니다.

| 구분 | 의미 | 이 프로젝트에서 |
|---|---|---|
| **Tier 1** | 단일 앱 배포에 직접 적용하는 보안 | **지금 바로 적용 권장** |
| **Tier 2** | 조직(다계정) 단위 거버넌스 | 회사 전체 AWS 환경이 있을 때만 / 데모 단독은 불필요 |

---

## 1. 적용 대상 요약

| 서비스 | 분류 | 역할 | 권장 |
|---|---|---|---|
| IAM | Tier 1 | 최소 권한 접근 제어 (서비스 간) | ✅ 이미 적용 |
| 관리자 페이지 인증 | Tier 1 | bcrypt 해시 + 8h 베어러 토큰 (앱 관리자) | ✅ 이미 적용 (배포 직후 기본 비밀번호 변경 필수) |
| AWS KMS | Tier 1 | 저장 데이터 암호화 | ✅ 적용 |
| CloudTrail / VPC Flow Logs | Tier 1 | 보안 로그 수집 | ✅ 적용 |
| GuardDuty | Tier 1 | 위협 탐지 | ✅ 적용 (클릭) |
| Security Hub | Tier 1 | 보안 통합 대시보드 | ✅ 적용 (클릭) |
| Amazon Inspector ("Security agent") | Tier 1 | 취약점(CVE) 스캔 | ✅ 적용 (클릭) |
| AWS WAF + CloudFront | Tier 1 | 웹 공격 차단 + HTTPS | ✅ 적용 권장 |
| AWS Shield (DDoS) | Tier 1 | DDoS 방어 | ✅ Standard 자동 |
| DR (재해 복구) | Tier 1 | 백업·복구 | ✅ 적용 |
| AWS Organizations | Tier 2 | 다계정 통합 관리 | ⚪ 다계정 환경 전제 |
| AWS Control Tower | Tier 2 | 멀티계정 랜딩존 자동 구성 | ⚪ 다계정 환경 전제 |
| AWS 랜딩 존 (보안 영역) | Tier 2 | 보안/로그 전용 계정 분리 | ⚪ 다계정 환경 전제 |
| AWS Firewall Manager | Tier 2 | 다계정 방화벽 정책 중앙 관리 | ⚪ Organizations 전제 |
| DLP (Amazon Macie) | 검토 | 민감정보 탐지 | 🔸 현재 PII 미수집, 우선순위 낮음 |

---

# Tier 1 — 지금 바로 적용

## 2.1 IAM — 최소 권한 접근 제어 (이미 적용됨)

이미 적용된 사항:

- 애플리케이션은 `aws/iam-policy.json` 의 **최소 권한 정책**만 사용 (Bedrock 호출 +
  지정된 DynamoDB 테이블 접근만 허용).
- EC2는 액세스 키를 서버에 저장하지 않고 **IAM 역할(`cerberus-ec2-role`)** 로
  권한을 받습니다 (`DEPLOYMENT.md` STEP 2).

추가로 권장하는 계정 위생(hygiene):

- **루트 계정 사용 금지** — 일상 작업은 IAM 사용자/역할로. 루트에는 **MFA** 필수.
- 관리자도 개인별 IAM 사용자 + MFA 사용, 권한은 그룹으로 부여.
- 액세스 키는 만들지 않거나, 만들면 정기적으로 교체(rotate).
- IAM Access Analyzer 활성화 — 의도치 않게 외부에 노출된 권한을 탐지.

### 2.1.1 관리자 페이지 인증

애플리케이션 내부에는 별도의 **관리자 페이지**가 있습니다 (`ADMIN.md` 참고).
이 페이지는 IAM 과는 무관한 자체 인증을 사용합니다.

- **비밀번호 저장:** bcrypt 해시로 DynamoDB `cerberus-leaderboard-config` 테이블에 저장
- **세션:** 8시간 만료 베어러 토큰 (인메모리 — 서버 재시작 시 모두 무효화)
- **🔴 배포 직후 가장 먼저 할 일:** 기본 비밀번호 `mzcadmin` 을 강력한 비밀번호로 변경
  (`ADMIN.md` §5 참고). 게임 자체가 ISMS 통과 기준을 다루므로 관리자 비밀번호도
  동일 기준(8자 이상, 영문·숫자·특수문자 조합, 분기 1회 변경)을 적용하세요.
- **추가 강화:** 관리자 페이지를 사무실 IP 등에서만 사용한다면, 2.7의 CloudFront +
  WAF 구성에 **`/api/admin/*` 경로 한정 IP 화이트리스트 룰**을 추가하는 것을 권장합니다.

## 2.2 AWS KMS — 저장 데이터 암호화

게임 로그·랭킹·관리자 설정 데이터를 **고객 관리형 키(CMK)** 로 암호화합니다.

1. 콘솔 > **KMS** > `Create key` > `Symmetric` > 별칭 `cerberus-key` 생성.
2. 콘솔 > **DynamoDB** > 각 테이블 > `Additional settings` > `Encryption` >
   **"Stored in your account, owned and managed by you"** 선택 > `cerberus-key` 지정.
   대상 테이블 3개: `cerberus-leaderboard`, `cerberus-leaderboard-logs`,
   **`cerberus-leaderboard-config`** (관리자 비밀번호 해시가 저장되므로 특히 권장).
3. EC2의 **EBS 볼륨 암호화** — 인스턴스 생성 시 기본 활성화 권장. (이미 만든
   인스턴스라면, 암호화된 스냅샷에서 새 볼륨을 만들어 교체.)
4. 애플리케이션이 암호화된 테이블을 읽고 쓸 수 있도록, `aws/iam-policy.json` 의
   **`KMSForEncryptedTables`** 구문의 `<KMS_KEY_ARN>` 를 1번에서 만든 키의 ARN으로
   바꾼 뒤 `cerberus-policy` 정책을 업데이트합니다.

> CMK를 쓰지 않아도 DynamoDB는 기본적으로 AWS 소유 키로 암호화됩니다. CMK는
> 키 접근 감사·교체·정책 통제가 필요할 때의 강화 옵션입니다.

## 2.3 보안 로그 수집 — CloudTrail · VPC Flow Logs · CloudWatch

"누가, 언제, 무엇을 했는가"를 기록해 사고 조사와 ISMS 감사 증적을 확보합니다.

- **CloudTrail (필수)** — 모든 AWS API 호출 기록.
  콘솔 > CloudTrail > `Create trail` > 이름 `cerberus-trail` > 로그 저장용 S3 버킷
  생성 > (선택) 로그 파일 무결성 검증 활성화.
- **VPC Flow Logs** — 네트워크 트래픽 기록.
  콘솔 > VPC > 해당 VPC 선택 > `Flow logs` 탭 > `Create flow log` > 대상
  CloudWatch Logs 또는 S3.
- **애플리케이션/웹 로그** — EC2에 CloudWatch Agent를 설치해 백엔드 로그
  (`journalctl`)와 nginx 로그(`/var/log/nginx/*`)를 CloudWatch Logs로 수집하면
  서버에 들어가지 않고도 로그를 조회·알람할 수 있습니다.
- 보안 로그를 담는 S3 버킷은 **퍼블릭 액세스 차단 + KMS 암호화 + 버전 관리**를
  켜고, 객체 잠금(Object Lock)으로 변조를 방지하면 더욱 안전합니다.

## 2.4 GuardDuty — 위협 탐지

CloudTrail·VPC Flow Logs·DNS 로그를 머신러닝으로 분석해 악성 행위(비정상
API 호출, 알려진 악성 IP 통신, 암호화폐 채굴 등)를 자동 탐지합니다.

- 콘솔 > **GuardDuty** > `Enable GuardDuty` — 사실상 클릭 한 번으로 끝.
- 탐지 결과(Findings)는 Security Hub로 자동 전달됩니다(2.5).
- 30일 무료 평가판 제공, 이후 분석량 기반 과금(데모 트래픽은 소액).

## 2.5 Security Hub — 보안 통합 대시보드

GuardDuty·Inspector 등의 탐지 결과를 한 곳에 모으고, **AWS 기초 보안 모범사례
(AWS Foundational Security Best Practices)** 및 **CIS 벤치마크** 기준으로 계정
설정을 자동 점검해 점수화합니다.

- 콘솔 > **Security Hub** > `Go to Security Hub` > 보안 표준 선택 후 활성화.
- "S3 버킷이 공개돼 있음", "MFA 미설정" 같은 항목을 점검표로 보여줍니다 —
  ISMS 점검 항목과 직접 대응되므로 이 프로젝트와 특히 잘 맞습니다.

## 2.6 Amazon Inspector — 취약점 스캔 ("Security agent")

별도의 보안 에이전트 대신, Amazon Linux 2023에 기본 탑재된 **SSM Agent**를
활용해 EC2의 OS·설치 패키지에서 알려진 취약점(CVE)을 지속 스캔합니다.

- 콘솔 > **Inspector** > `Activate Inspector` — EC2를 자동 발견해 스캔.
- 컨테이너 이미지·Lambda로 확장 시에도 동일 콘솔에서 관리.
- (선택) GuardDuty의 **Runtime Monitoring** 을 켜면 런타임 행위 기반 탐지를
  위한 경량 에이전트가 추가됩니다.

## 2.7 AWS WAF + CloudFront — 웹 공격 차단 & HTTPS

> **중요:** AWS WAF는 EC2 인스턴스에 직접 붙지 않습니다. 앞단에 **CloudFront**
> (또는 ALB)가 있어야 합니다. CloudFront를 두면 WAF·HTTPS·DDoS 방어·캐싱을
> 한 번에 얻을 수 있어 권장합니다.

1. **ACM 인증서** — CloudFront용 인증서는 `us-east-1` 리전에서 발급(무료).
2. **CloudFront 배포 생성** — Origin을 EC2의 퍼블릭 DNS로 지정,
   `Viewer protocol policy` 를 `Redirect HTTP to HTTPS` 로 설정.
3. **WAF Web ACL 생성 후 CloudFront에 연결** — 아래 관리형 규칙을 추가:
   - `AWSManagedRulesCommonRuleSet` (XSS 등 일반 공격)
   - `AWSManagedRulesSQLiRuleSet` (SQL 인젝션)
   - `AWSManagedRulesAmazonIpReputationList` (악성 IP 평판)
   - **Rate-based rule** — 단일 IP의 과도한 요청 차단 (L7 DDoS·봇 완화)
4. **오리진 보호** — EC2 보안 그룹의 80번 포트를 `0.0.0.0/0` 대신 CloudFront의
   관리형 프리픽스 목록(`com.amazonaws.global.cloudfront.origin-facing`)으로
   제한하면, 사용자가 CloudFront를 우회해 EC2에 직접 접근하지 못합니다.

## 2.8 AWS Shield — DDoS 방어

- **Shield Standard** — CloudFront·Route 53·ALB에 **자동·무료**로 적용됩니다.
  즉 2.7에서 CloudFront를 도입하면 네트워크 계층(L3/L4) DDoS 방어가 자동 포함됩니다.
- 애플리케이션 계층(L7) 공격은 2.7의 **WAF rate-based rule** 로 보강합니다.
- **Shield Advanced** 는 월 $3,000 수준의 엔터프라이즈 서비스로, 데모에는 불필요합니다.

## 2.9 DR — 재해 복구

서버나 데이터가 손상돼도 빠르게 복구할 수 있도록 준비합니다.

- **데이터(DynamoDB):**
  - **3개 테이블 모두**(`cerberus-leaderboard`, `cerberus-leaderboard-logs`,
    `cerberus-leaderboard-config`) **PITR(Point-in-time recovery)** 활성화 —
    최근 35일 내 임의 시점으로 복구 가능 (콘솔 > 테이블 > `Backups` 탭).
    설정(config) 테이블은 관리자가 편집한 문제·통과 기준이 모두 들어 있으므로
    특히 PITR 적용을 권장합니다.
  - 정기 **온디맨드 백업** 또는 AWS Backup으로 백업 일정 구성.
  - 관리자 페이지의 **JSON 내보내기**(`ADMIN.md` §2.1)로 문제 세트를 별도
    파일로도 백업해 두면 빠른 복구·이관에 유용합니다.
- **서버(EC2):**
  - **AMI(머신 이미지)** 를 정기 생성 — 동일 구성의 서버를 즉시 재기동 가능.
  - **EBS 스냅샷** 자동 일정 구성 (Data Lifecycle Manager).
- **코드/설정:** 코드는 GitHub에 보관(원본). `.env` 는 git에 포함되지 않으므로
  Secrets Manager 또는 안전한 별도 위치에 사본 보관.
- **복구 절차:** 서버 손실 시 `DEPLOYMENT.md` 를 그대로 재실행해 새 EC2를
  구성하고, DynamoDB는 PITR로 복원 → 인메모리 세션 특성상 진행 중이던 게임만
  초기화되고 랭킹·로그는 보존됩니다.
- 데모 기준 목표: **RPO**(데이터 손실 허용폭) 약 24시간, **RTO**(복구 소요시간)
  약 1시간. 요구 수준이 높아지면 다중 AZ·다중 리전 구성을 검토합니다.

---

# Tier 2 — 조직(다계정) 단위 거버넌스

아래 서비스들은 **여러 AWS 계정을 운영하는 조직 전체**를 통제하기 위한
것입니다. Cerberus 데모 하나만을 위해 새로 구축할 필요는 없습니다. 다만 이
프로젝트가 **회사의 표준 AWS 환경에 편입**된다면, 그 환경이 이미 제공하는
정책을 그대로 상속받게 됩니다.

## 3.1 AWS Organizations

여러 AWS 계정을 하나의 조직으로 묶어 통합 결제하고, **SCP(서비스 제어 정책)**
로 계정 전체에 권한 가드레일을 겁니다. 모든 Tier 2 서비스의 전제 조건입니다.
→ *단일 계정 데모에는 불필요. 회사가 다계정을 운영한다면 이미 구성돼 있을 것입니다.*

## 3.2 AWS Control Tower

Organizations 위에서 **모범사례 멀티계정 환경을 자동으로 구성**해 주는
서비스입니다. 보안 가드레일, 로그 집계, 계정 생성 자동화(Account Factory)를 제공합니다.
→ *조직 차원의 클라우드 거버넌스를 처음 세울 때 사용. 데모 범위 밖.*

## 3.3 AWS 랜딩 존 (보안 영역)

"랜딩 존"은 Control Tower가 만들어 내는 **결과물**입니다 — 보안 전용 계정과
로그 아카이브 계정을 분리하고, 네트워크·암호화·로깅의 기준선(baseline)을
적용한 표준 다계정 구조입니다.
→ *Control Tower 도입 시 함께 구성됨. 데모 단독으로는 해당 없음.*

## 3.4 AWS Firewall Manager

Organizations에 속한 **모든 계정·리소스에 WAF/Shield/보안 그룹 정책을 중앙에서
일괄 적용·강제**합니다.
→ *관리 대상이 여러 개일 때 의미가 있음. 이 프로젝트는 2.7처럼 WAF를 직접
연결하면 충분합니다.*

> **요약:** Tier 2는 "Organizations 활성화"가 출발점입니다. Cerberus가 회사
> 표준 AWS 계정 구조 위에 배포된다면, 그 구조의 Control Tower 가드레일과
> Firewall Manager 정책을 자동으로 적용받습니다. **데모만을 위해 별도로 구축할
> 필요는 없습니다.**

---

## 4. DLP (데이터 유출 방지) — 적용 범위 검토

- AWS의 네이티브 DLP 서비스는 **Amazon Macie** 로, 주로 **S3에 저장된** 데이터에서
  개인정보·기밀정보를 자동 탐지·분류합니다. Macie는 DynamoDB는 스캔하지 않습니다.
- 이 프로젝트가 저장하는 잠재적 민감 데이터는 `user_message`(사용자가 입력한
  ISMS 답변)입니다. 현재는 이름·연락처 같은 **개인정보(PII)를 수집하지 않으므로**
  DLP 우선순위는 낮습니다.
- 강화가 필요하다면:
  - 분석 로그를 S3로 내보내는 파이프라인을 만들 경우, 그 버킷에 **Macie** 적용.
  - 또는 `user_message` 저장 전에 민감 패턴(주민번호·이메일 등)을 **마스킹/익명화**.
  - 게임 UI에 "답변에 개인정보를 입력하지 마세요" 안내 문구 추가.

---

## 5. 권장 적용 순서

비용·난이도 대비 효과가 큰 순서입니다. 위에서부터 차례로 적용하면 됩니다.

| 순서 | 작업 | 난이도 | 비용 |
|---|---|---|---|
| 0 | **관리자 페이지 기본 비밀번호 변경** (`mzcadmin` → 강력한 비밀번호) | 매우 쉬움 | 무료 |
| 1 | IAM 최소 권한 · 루트 MFA | (이미 적용) | 무료 |
| 2 | DynamoDB PITR 활성화 (3개 테이블 모두 — DR) | 매우 쉬움 (클릭) | 소액 |
| 3 | GuardDuty 활성화 | 매우 쉬움 (클릭) | 소액 |
| 4 | Security Hub 활성화 | 매우 쉬움 (클릭) | 소액 |
| 5 | CloudTrail 추적(Trail) 생성 | 쉬움 | 소액 (S3 비용) |
| 6 | Amazon Inspector 활성화 | 쉬움 (클릭) | 소액 |
| 7 | KMS 키 생성 + DynamoDB 3개 테이블/EBS 암호화 | 보통 | 소액 |
| 8 | CloudFront + WAF + HTTPS 구성 (가능하면 `/api/admin/*` IP 화이트리스트) | 보통 | 소액~중간 |

> 2~6번은 대부분 콘솔에서 활성화 버튼만 누르면 되며, 효과 대비 비용이 낮아
> 가장 먼저 적용할 것을 권장합니다.

---

## 6. 비용에 대한 참고

Tier 1 서비스 대부분은 데모 수준 트래픽에서 **월 수 달러~수십 달러** 규모입니다
(GuardDuty·Security Hub·Inspector·CloudTrail·CloudFront 합산). Shield Advanced나
Tier 2 거버넌스 서비스처럼 고비용 항목은 이 프로젝트에 포함하지 않았습니다.
정확한 비용은 AWS Pricing Calculator로 사전 산정하고, **AWS Budgets** 로 월
예산 알림을 설정해 두는 것을 권장합니다.
