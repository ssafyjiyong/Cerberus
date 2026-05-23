# Cerberus 관리자 페이지 가이드

데모 진행자가 게임 콘텐츠(문제·통과 기준)와 운영 파라미터를 **재배포 없이
런타임에 제어**할 수 있는 비공개 관리자 페이지의 사용 설명서입니다.

---

## 1. 접근 방법 (이스터에그 트리거)

관리자 페이지는 화면에 노출되지 않습니다. 시작 화면(StartScreen)에서 아래 두
방법 중 하나로 진입할 수 있습니다.

| 트리거 | 설명 |
|---|---|
| **케르베로스 첫 번째 머리를 5회 클릭** | 3초 안에 로고의 왼쪽 머리 영역을 5번 클릭. 입력 필드에 포커스가 있을 때는 무시됨 |
| **키보드 `admin` 입력** | 시작 화면 어디서든 `a → d → m → i → n` 순서로 타이핑 (1.5초 내) |

트리거되면 **비밀번호 입력 모달**이 뜹니다.

### 1.1 최초 비밀번호

```
mzcadmin
```

> ⚠ **배포 직후 반드시 변경하세요.** 운영 탭 > "관리자 비밀번호 변경"
> 섹션에서 즉시 변경할 수 있습니다.

### 1.2 인증 동작 방식

- 비밀번호 검증 성공 시 **8시간 만료 베어러 토큰**이 발급되어 브라우저
  `localStorage` (키: `cerberus_admin_token`)에 저장됩니다.
- 이후 같은 브라우저에서 다시 트리거 진입 시 **로그인 모달을 건너뛰고
  곧바로 패널**로 들어갑니다.
- 다음과 같은 경우 토큰이 무효화됩니다:
  - 비밀번호 변경 직후
  - "기본값으로 복원 + 비밀번호 초기화" 수행 시
  - 백엔드 서버 재시작 시 (인메모리 토큰)
  - 발급 후 8시간 경과

---

## 2. 탭별 기능

관리자 페이지는 6개의 탭으로 구성됩니다.

### 2.1 질문 관리

게임의 핵심 콘텐츠인 **3개 레벨의 심사 문제**를 편집합니다.

각 레벨 카드에서:
- **심사 영역 (Domain)** — 예: "물리적 보안 / 단말기 보안"
- **심사 질문 (Question)** — AI 심사원이 사용자에게 던지는 질문 본문
  - 🤖 **AI 생성** — 현재 Domain을 힌트 삼아 새 질문을 생성
  - ✨ **AI 다듬기** — 입력된 질문을 더 명확하고 자연스럽게 정리
- **통과 기준 (Pass Criteria)** — 합격을 판단하는 항목 목록 (보통 3개)
  - 행마다 ✨ 버튼으로 **그 항목만** AI 다듬기
  - ✕ 버튼으로 행 삭제
  - 🤖 **AI 기준 3개 생성** — 현재 질문을 기반으로 통과 기준 3개를 한 번에 생성
  - **+ 기준 추가** — 빈 행 추가

편집 후 카드 하단의 **💾 저장** 을 눌러야 반영됩니다. 변경된 문제는
**새로 시작하는 게임 세션부터** 적용됩니다.

#### JSON Import / Export

탭 상단 카드에서:
- **📤 JSON 내보내기** — 현재 3개 레벨 설정을 `cerberus-levels-<timestamp>.json` 파일로 다운로드 (백업·공유용)
- **📥 JSON 가져오기** — 위 형식의 JSON 파일을 업로드하여 3개 레벨을 **일괄 교체**. 잘못된 형식이면 거부됩니다 (1·2·3 키 모두 존재 + 각 레벨에 domain·question·pass_criteria 필수)

> 💡 **활용 팁:** 시연 유형(스타트업 대상 / 금융권 대상 등)별 문제 세트를
> 미리 JSON으로 만들어 두고, 행사 시작 전에 가져오기로 빠르게 전환하세요.

### 2.2 게임 설정

게임 규칙·점수 가중치·AI 모델을 조정합니다.

| 항목 | 의미 | 기본값 | 권장 범위 |
|---|---|---|---|
| `TIME_LIMIT` | 제한 시간(초) | 300 | 30~3600 |
| `P_MAX` | 최대 답변 횟수 | 15 | 1~100 |
| `W_TIME` | 점수 — 시간 가중치 | 1 | 0~100 |
| `W_PROMPT` | 점수 — 답변 횟수 가중치 | 10 | 0~1000 |
| `BEDROCK_MODEL_ID` | 사용하는 AI 모델 | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock에서 모델 액세스가 활성화된 ID |

**점수 공식:** `(TIME_LIMIT − time_used) × W_TIME + (P_MAX − prompt_count) × W_PROMPT`

> ⓘ 변경 사항은 **새 게임 세션부터** 적용됩니다. 진행 중인 세션은 생성
> 시점의 파라미터로 끝까지 진행됩니다.

> 🤖 **Bedrock 모델 교체 시 주의:** 새 모델은 AWS 콘솔 > Bedrock > Model
> access 에서 **사전에 액세스가 활성화**되어 있어야 합니다. 또한 일부
> 최신 모델은 단일 모델 ID 대신 **추론 프로파일(inference profile)** ID
> 가 필요할 수 있습니다.

### 2.3 분석·로그

데이터 수집 목표인 **"어떤 항목에 사람들이 취약한지"** 를 한눈에 봅니다.

상단 통계:
- 전체 세션 수 · 전체 채팅 수 · 게임 클리어율

레벨별:
- **도달 / 클리어 세션 수** (세션 단위 지표)
- **clear_rate** — 도달 대비 클리어 비율
- **avg_attempts_to_clear** — 클리어한 세션의 평균 시도 횟수
- **취약 기준 (weak_criteria) 표** — AI가 판정한 누락 기준 번호의 빈도순. *"실패 횟수"가 가장 높은 항목이 사람들이 가장 자주 빠뜨리는 통과 기준*

하단 카드 — 최근 100건 게임 로그 테이블:
- 시각 / 세션 ID(앞 8자) / 레벨 / 시도 / 상태(pass·fail) / 누락 기준 번호 / 사용자 답변 원문

사용자 답변을 직접 읽어 "어떤 표현을 자주 쓰는지", "어떤 부분을 자주 놓치는지" 를 정성적으로도 파악할 수 있습니다.

### 2.4 활성 세션

현재 진행 중인 게임을 **5초마다 자동 갱신**하며 실시간 모니터링합니다.

- 현재 진행 중 세션 수
- 레벨별 분포 (Level 1 / 2 / 3)
- 개별 세션 표 — 세션 ID(앞 12자) · 현재 레벨 · 답변 수 · 경과 시간 · 시간 제한 · 시작 시각(UTC)

시연 행사 중 "지금 몇 명이 어느 단계에서 막혔는지" 를 무대 뒤에서 확인할 때 유용합니다.

### 2.5 리더보드

Top 10 명예의 전당을 관리합니다.

- 전체 항목 조회 (이름 · 점수 · 시간 · 등록일 · ID 앞자리)
- **개별 삭제** — 부적절한 닉네임 등 신속 제거 (확인 다이얼로그)
- **🗑 전체 초기화** — 모든 항목 제거 (확인 다이얼로그). 새 행사 시작 전 정리 용도

> ℹ️ 로컬 mock 모드에서는 데모 항목들에 ID가 없어 개별 삭제 버튼이
> 비활성화됩니다. 전체 초기화는 가능합니다 (인메모리만 비움).

### 2.6 운영

운영 관련 위험 작업을 모은 탭입니다.

#### 유지보수 모드

토글 스위치로 ON/OFF. **ON일 때 `/api/game/start` 가 503**으로 응답해 신규 게임 시작을 차단합니다. 진행 중인 세션은 영향받지 않고 계속 진행됩니다.

용도:
- 점검·재배포 직전에 신규 진입을 막아 진행 중 게임의 마무리를 보장
- 시연이 끝난 뒤 더 이상 새 게임이 시작되지 않게 잠금

#### 기본값으로 복원

레벨 설정과 게임 파라미터를 **코드 기본값(LEVEL_CONFIGS / .env)** 으로 되돌립니다. 잘못 편집한 내용을 한 번에 원복할 때 사용합니다.

- 기본은 **비밀번호 유지** — 다른 모든 설정만 초기화
- 체크박스를 켜면 **관리자 비밀번호도 `mzcadmin` 으로 초기화** — 인수인계나 자격 증명 분실 시. 이 경우 현재 토큰이 무효화되어 재로그인이 필요합니다.

#### 관리자 비밀번호 변경

- 현재 비밀번호 + 새 비밀번호(4자 이상) + 확인. 변경 후 **모든 기존 토큰이 무효화**되어 자동 로그아웃됩니다.

#### 로그아웃

서버에서 현재 토큰을 폐기하고 패널을 닫습니다.

---

## 3. AI 어시스트 동작 원리

관리자 페이지의 AI 버튼은 모두 **Amazon Bedrock Converse API**(`/api/admin/ai/*`)
를 호출합니다.

| 버튼 | 내부 동작 |
|---|---|
| 🤖 AI 생성 (질문) | 현재 Domain 을 힌트로 새 질문 한 문장을 생성 (text completion) |
| ✨ AI 다듬기 (질문/기준) | 입력 문장을 의미 유지한 채 정리. `kind` 파라미터로 질문/기준 어조 차이 |
| 🤖 AI 기준 3개 생성 | 현재 질문을 입력으로 Tool Use 호출 → 구조화된 통과 기준 배열 반환 |

권한 요구사항:
- 백엔드 IAM Role에 `bedrock:InvokeModel` 권한
- AWS 콘솔에서 해당 모델 액세스 활성화
- 게임 설정 탭의 `BEDROCK_MODEL_ID` 와 일치하는 모델

문제가 있을 때:
- **503 (AI 서비스 오류)** → 위 권한 / 모델 액세스 / 리전 확인
- **502 (AI가 생성하지 못함)** — 매우 드묾, 다시 시도

---

## 4. 일반적인 운영 시나리오

### A) 새 시연 행사 준비

1. 운영 탭에서 **비밀번호 변경** (기본 비밀번호인 경우)
2. 질문 관리 탭에서 행사 주제에 맞게 문제 수정
   - 처음부터 만들 때는 **🤖 AI 생성** → ✨ AI 다듬기 순으로 빠르게 초안 작성
   - 통과 기준은 질문 입력 후 **🤖 AI 기준 3개 생성**
3. 게임 설정 탭에서 시간·시도 횟수 조정 (예: 짧은 데모는 `TIME_LIMIT=180`)
4. 리더보드 탭 → 🗑 전체 초기화 (이전 행사 데이터 정리)
5. 질문 관리 탭 → **📤 JSON 내보내기** 로 백업 저장

### B) 시연 진행 중

- 활성 세션 탭을 무대 뒤 모니터에 띄워두고 진행 상황 확인
- 분석·로그 탭으로 **실시간 취약 기준** 확인 → 발표 멘트에 활용

### C) 시연 종료 후

1. 분석·로그 탭에서 결과 검토 (이번 행사의 weak_criteria 패턴)
2. 운영 탭 → 유지보수 모드 ON (신규 진입 차단)
3. 필요 시 JSON 내보내기로 결과 백업

### D) 정기 점검 / 재배포

1. 유지보수 모드 ON
2. `MAINTENANCE.md` 의 재배포 절차 진행
3. 정상 확인 후 유지보수 모드 OFF

---

## 5. 보안 권장 사항

- 🔴 **최초 배포 직후 비밀번호 즉시 변경** (가장 중요)
- 비밀번호는 8자 이상, 영문·숫자·특수문자 조합 권장 (정작 ISMS 게임의
  Level 2 통과 기준과 동일한 정책)
- 분기 1회 이상 정기적으로 변경
- 의심스러운 접근이 감지되면 **비밀번호 변경**으로 기존 토큰을 모두 무효화
- 관리자 페이지는 인증된 운영자만 접근하는 환경(사무실 IP 등)에서 사용 권장. 외부 노출이 우려되면 추가로 CloudFront/WAF의 **IP 화이트리스트 룰**을 `/api/admin/*` 경로에 적용

---

## 6. 문제 해결 (Troubleshooting)

| 증상 | 원인 / 해결 |
|---|---|
| 트리거가 작동하지 않음 | 시작 화면에서만 동작. 게임이 시작된 후에는 불가. 새로 고침 후 다시 시도. |
| 로그인 모달에서 "비밀번호가 올바르지 않습니다" | 기본 비밀번호 `mzcadmin` (변경한 적 있다면 그 비밀번호). 분실 시 §7 참고 |
| AI 버튼이 503 (AI 서비스 오류) | Bedrock 모델 액세스 미설정 또는 IAM 권한 부족. `DEPLOYMENT.md` STEP 1·2 참고 |
| 설정 저장 시 500 오류 | DynamoDB 권한 또는 테이블 이슈. 백엔드 로그(`journalctl -u cerberus-backend`)에서 원인 확인 |
| 패널이 갑자기 로그인 모달로 돌아감 | 토큰 만료(8시간) 또는 백엔드 재시작. 다시 로그인하면 됨 |
| 관리자 페이지가 "404" 또는 응답 없음 | 백엔드가 켜져 있는지 (`curl http://localhost:8000/api/health`) 확인 |

---

## 7. 비밀번호 분실 시 복구 절차

토큰은 인메모리이지만 비밀번호 해시는 DynamoDB에 영구 저장되므로,
비밀번호를 잊었을 때는 다음 절차로 복구할 수 있습니다.

### 방법 1 — DynamoDB 콘솔 (권장)

1. AWS 콘솔 > DynamoDB > Tables > **`cerberus-leaderboard-config`**
2. **Explore table items** 클릭
3. `config_id = MAIN` 항목 선택 → **Delete item**
4. 백엔드 재시작 (`sudo systemctl restart cerberus-backend`)
5. 앱이 다시 시작될 때 기본값(`mzcadmin`)으로 자동 시드 → 그 비밀번호로 로그인 → 운영 탭에서 즉시 변경

### 방법 2 — SSH로 직접 실행

```bash
ssh -i cerberus-key.pem ec2-user@<서버IP>
cd /opt/cerberus/backend
source venv/bin/activate
python -c "from services import config_service; config_service.reset_to_defaults(reset_password=True); print('OK')"
sudo systemctl restart cerberus-backend
```

> ⚠ 두 방법 모두 **다른 설정(레벨 문제·게임 파라미터)도 모두 초기화**됩니다. 미리 JSON 내보내기로 백업해 두는 것이 안전합니다.

---

## 8. 개발자용 — 관리자 API 직접 호출

모든 관리자 엔드포인트는 `/api/admin/*` 경로에 있으며 베어러 토큰이
필요합니다. 전체 명세는 백엔드의 **Swagger UI** (`/docs`) 에서 확인하세요.

빠른 참조 — 로그인 예시 (curl):

```bash
# 토큰 발급
TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"password":"mzcadmin"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 현재 설정 조회
curl -s http://localhost:8000/api/admin/config \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# 유지보수 모드 ON
curl -X PUT http://localhost:8000/api/admin/config/maintenance \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"enabled":true}'
```

주요 엔드포인트:

| 메서드 | 경로 | 용도 |
|---|---|---|
| POST | `/api/admin/auth/login` | 비밀번호 → 토큰 발급 |
| POST | `/api/admin/auth/logout` | 토큰 폐기 |
| POST | `/api/admin/auth/password` | 비밀번호 변경 |
| GET | `/api/admin/config` | 전체 설정 조회 |
| PUT | `/api/admin/config/levels/{level}` | 특정 레벨 수정 |
| POST | `/api/admin/config/levels/import` | JSON 일괄 교체 |
| PUT | `/api/admin/config/game-params` | 게임 파라미터 수정 |
| PUT | `/api/admin/config/maintenance` | 유지보수 모드 |
| POST | `/api/admin/config/reset` | 기본값 복원 |
| POST | `/api/admin/ai/generate-question` | AI 질문 생성 |
| POST | `/api/admin/ai/generate-criteria` | AI 통과 기준 생성 |
| POST | `/api/admin/ai/polish` | AI 문장 다듬기 |
| GET | `/api/admin/analytics/summary` | 분석 요약 |
| GET | `/api/admin/analytics/logs` | 로그 조회 |
| GET | `/api/admin/sessions/active` | 활성 세션 |
| GET | `/api/admin/leaderboard` | 리더보드 전체 조회 |
| DELETE | `/api/admin/leaderboard/{id}` | 항목 삭제 |
| POST | `/api/admin/leaderboard/clear` | 리더보드 초기화 |
