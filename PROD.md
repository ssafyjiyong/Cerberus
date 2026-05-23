# 프로젝트 명세서 (PROD.MD)

## 1. 프로젝트 개요
* **프로젝트명:** 케르베로스: 어둠의 심사원 (Cerberus: The Dark Auditor)
* **목적:** ISMS 심사에 대한 고객의 진입장벽과 스트레스를 낮추고, 이해도를 높이기 위한 데모용 게이미피케이션 프로그램.
* **핵심 컨셉:** 사용자가 깐깐한 AI 심사원(케르베로스)과 인터뷰(채팅)를 진행하여, 프롬프트 인젝션 게임(예: 간달프)처럼 심사원의 기준을 충족시키고 "합격(Pass)"을 받아내는 3단계 관문 통과 게임.
* **제한 시간:** 총 5분 (300초) 타임어택.

---

## 2. 시스템 아키텍처 (AWS 환경)
> 개발 진행에 따라 아래와 같이 기술 스택이 확정되었습니다.

* **Frontend:** React + Vite (호스팅: EC2 nginx 정적 서빙 / 선택적으로 CloudFront)
    * 채팅 기반 UI, 타이머(5분), 실시간 점수 및 Top 10 랭킹 보드 제공.
* **Backend:** Python (FastAPI) — 호스팅: 단일 EC2 인스턴스
    * 세션 관리, AI 통신, 타이머 동기화, 점수 계산 로직 처리.
    * 게임 세션을 인메모리로 관리하므로, 세션이 유실되는 Lambda 대신 단일 EC2를 사용.
* **AI Model:** Amazon Bedrock — Claude 3 Haiku (Converse API + Tool Use)
* **Database:** Amazon DynamoDB
    * Top 10 랭킹 테이블(`cerberus-leaderboard`) 및 분석 로그 테이블(`cerberus-leaderboard-logs`).

---

## 3. 게임 시나리오 및 난이도 (케르베로스의 3개의 머리)
고정된 3개의 시나리오를 순차적으로 클리어해야 함.

### Level 1 (하): 물리적 보안 / 단말기 보안
* **주제:** 사무실 보안 및 PC 화면 잠금
* **심사원 질문:** "직원들이 자리를 비울 때 PC 화면 보호 조치는 어떻게 하고 계십니까?"
* **통과 조건 (Pass Criteria):** 화면 잠금(보호기) 설정, 비밀번호 해제, 일정 시간(예: 5분) 이내 자동 잠금 등의 키워드/맥락 포함.

### Level 2 (중): 접근 통제 / 계정 관리
* **주제:** 관리자 계정 및 비밀번호 관리 정책
* **심사원 질문:** "서버 및 DB에 접근하는 관리자 계정의 비밀번호 복잡도와 주기적인 변경 정책에 대해 설명해 주세요."
* **통과 조건 (Pass Criteria):** 영문/숫자/특수문자 조합, 길이 제한, 주기적(예: 분기 1회) 변경 등의 요건 충족.

### Level 3 (상): 네트워크 보안 / 침해사고 대응
* **주제:** DB 접근 제어 및 로그 리뷰
* **심사원 질문:** "개인정보가 저장된 DB에 대한 접근 통제 및 작업 내역 로그 리뷰는 누가, 얼마나 자주 수행합니까?"
* **통과 조건 (Pass Criteria):** 방화벽/접근제어 솔루션 사용, 비인가자 차단, 독립된 보안 관리자가 주기적(예: 월 1회)으로 리뷰.

---

## 4. AI 프롬프트 엔지니어링 (핵심 로직)
AI는 사용자의 답변을 평가하고 JSON 형태로 백엔드에 결과를 반환해야 함.

* **역할 부여:** 깐깐하지만 공정한 ISMS 인증 심사원. 절대 정답을 먼저 누설하지 않음.
* **출력 형식 (JSON):**
    * 합격 시: `{"status": "pass", "message": "합격 메시지 및 다음 단계 안내"}`
    * 불합격 시: `{"status": "fail", "message": "부족한 부분을 지적하는 꼬리질문"}`

---

## 5. 랭킹 및 점수 산정 시스템 (Scoring)
* **목표:** 빠른 시간 내에, 최소한의 대화 턴(Turn) 수로 정확하게 답변한 사용자에게 높은 점수 부여.
* **점수 산정 공식:**
    Total Score = (300 - T_used) * W_time + (P_max - P_used) * W_prompt
    * `T_used`: 3단계를 모두 클리어하는 데 사용한 총 시간(초)
    * `P_max`: 허용된 최대 답변(채팅) 횟수
    * `P_used`: 사용자가 입력한 실제 답변 횟수
    * `W_time`, `W_prompt`: 시간과 횟수에 대한 가중치(배점)
* **랭커 등록:** 게임 종료 시 최종 점수가 상위 10위 이내일 경우, 이름을 입력하여 명예의 전당(Top 10 Leaderboard)에 등록.

---

## 6. 개발 마일스톤
* **Phase 1 (PoC 및 프로토타이핑):** Streamlit을 활용한 로컬 환경 구축. 프롬프트 엔지니어링 튜닝 및 점수 산정 로직 검증.
* **Phase 2 (AWS 인프라 구축):** Lambda, API Gateway, DynamoDB 세팅 및 백엔드 로직 이관.
* **Phase 3 (프론트엔드 개발 및 연동):** React/Vue.js 기반 UI 구현, 타이머 및 랭킹 시스템 연동, AWS 배포.

---

## 7. 현재 진행 상황 및 추가 예정 기능 (2026-05-23 기준)
* **완료된 작업:**
  * 프론트엔드 (React + Vite): 아케이드 테마 UI (Start, Game, Timer, Result, Leaderboard 등) 및 상태 머신 구현 완료.
  * 백엔드 (FastAPI): Amazon Bedrock (Claude) Converse API 연동, Pydantic 모델, DynamoDB 리더보드 로직, 점수 산정 로직 구현 완료. (로컬 테스트 완료)
  * **이스터에그 (Easter Egg):** StartScreen에서 코나미 코드(↑↑↓↓←→←→BA) 입력 시 "제작: 제프리킴" 레트로 네온 크레딧 화면이 노출되도록 구현. 브라우저 검증 완료.
  * **분석 로그 고도화 (Analytics):** 모든 채팅·게임 결과를 DynamoDB 로그 테이블에 적재. 취약 항목 분석을 위해 레벨별 시도 횟수(`level_attempt`), AI가 판정한 누락 통과 기준(`missing_criteria`)을 수집하고, 세션 단위 통과율·평균 시도 횟수·취약 기준 빈도(`get_analytics_summary`)를 집계하도록 구현. (로컬 테스트 완료)
  * **관리자 페이지 (Admin Panel):** 시작 화면에서 케르베로스 첫 번째 머리 5회 클릭 또는 `admin` 키보드 입력 시 진입하는 비공개 관리 콘솔 구현. bcrypt + 8시간 베어러 토큰 인증, 런타임 동적 설정 저장소(`cerberus-leaderboard-config` 테이블), AI 어시스트(질문/통과 기준 생성·다듬기, Bedrock Converse API), 분석 대시보드, 활성 세션 모니터링(5초 자동 갱신), 리더보드 관리(개별 삭제·전체 초기화), 유지보수 모드(신규 게임 503), JSON Import/Export, 기본값 복원 등 6개 탭·18개 API 엔드포인트. 최초 비밀번호 `mzcadmin` (배포 직후 변경 권장). 자세한 사용법은 `ADMIN.md`.
  * **AWS 배포·유지보수·보안·관리자 문서화:** `DEPLOYMENT.md`(단계별 배포 가이드), `MAINTENANCE.md`(재배포·패치), `SECURITY.md`(보안 아키텍처), `ADMIN.md`(관리자 페이지 가이드), IAM 최소 권한 정책(`aws/iam-policy.json`) 작성 완료.
* **진행 예정 작업 (Next Steps):**
  1. **AWS 실제 배포:** `DEPLOYMENT.md`에 따라 EC2 환경에 배포하고 Bedrock·DynamoDB 실연동 테스트. 배포 직후 관리자 페이지에서 기본 비밀번호(`mzcadmin`) 즉시 변경.
  2. **보안 서비스 적용:** `SECURITY.md`의 Tier 1 항목(KMS 암호화, GuardDuty, Security Hub, CloudTrail, Inspector, WAF+CloudFront, DR) 적용.
  3. **운영 데이터 분석 및 콘텐츠 튜닝:** 실배포 후 수집된 로그로 취약 심사 항목을 분석하고, 관리자 페이지의 AI 어시스트를 활용해 질문·통과 기준을 지속적으로 개선.

---

## 8. 보안 아키텍처 (Security)
ISMS 인증 심사를 주제로 하는 프로젝트인 만큼, 배포 환경 자체도 AWS 보안 모범사례를 반영합니다. 상세 적용 절차는 **`SECURITY.md`** 를 참고하십시오.

* **Tier 1 — 단일 앱 배포에 바로 적용:** IAM 최소 권한, 관리자 페이지 인증(bcrypt + 베어러 토큰, 배포 직후 기본 비밀번호 변경 필수), KMS(저장 데이터 암호화 — 3개 DynamoDB 테이블 포함), CloudTrail·VPC Flow Logs(보안 로그 수집), GuardDuty(위협 탐지), Security Hub(보안 통합 대시보드), Amazon Inspector(취약점 스캔), WAF + CloudFront(웹 공격 차단 — `/api/admin/*` 경로 IP 화이트리스트 옵션), AWS Shield(DDoS 방어), DynamoDB PITR·스냅샷(DR).
* **Tier 2 — 조직(다계정) 단위 거버넌스:** AWS Organizations, Control Tower, 랜딩 존, Firewall Manager. 데모 단독으로는 불필요하며, 회사 표준 AWS 환경에 편입될 경우 해당 환경의 정책을 상속받습니다.
* **DLP:** 현재 개인정보(PII)를 수집하지 않으므로 우선순위가 낮음. 로그를 S3로 내보낼 경우 Amazon Macie 적용을 검토합니다.