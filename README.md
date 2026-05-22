# 케르베로스: 어둠의 심사원 (Cerberus: The Dark Auditor)

> ISMS 정보보호 인증 심사를 게이미피케이션한 데모용 웹 게임

깐깐한 AI 심사원 **케르베로스**와 인터뷰(채팅)를 진행하여, 3단계 심사 관문을
제한 시간 안에 통과하는 타임어택 게임입니다. ISMS 인증 심사에 대한 진입장벽과
스트레스를 낮추고 이해도를 높이는 것을 목표로 합니다.

---

## 게임 개요

- **목표:** AI 심사원의 질문에 답하여 3개 심사 영역을 모두 "합격(Pass)" 받기
- **제한 시간:** 5분 (300초) 타임어택
- **3단계 심사 영역 (케르베로스의 세 머리):**

| 레벨 | 난이도 | 심사 영역 |
|---|---|---|
| Level 1 | 하 | 물리적 보안 / 단말기 보안 |
| Level 2 | 중 | 접근 통제 / 계정 관리 |
| Level 3 | 상 | 네트워크 보안 / 침해사고 대응 |

- **점수 산정:** 빠르고 적은 대화 턴으로 통과할수록 고득점
  ```
  Total Score = (제한시간 − 사용시간) × W_time + (최대답변수 − 사용답변수) × W_prompt
  ```
- **랭킹:** 게임 종료 시 상위 10위 안에 들면 명예의 전당(Top 10)에 등록

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React 19 + Vite 7 (아케이드 테마 UI) |
| Backend | Python 3.11+ / FastAPI |
| AI Model | Amazon Bedrock — Claude 3 Haiku (Converse API + Tool Use) |
| Database | Amazon DynamoDB (랭킹 + 분석 로그) |
| 배포 | 단일 EC2 + nginx |

---

## 프로젝트 구조

```
Cerberus/
├── backend/                  FastAPI 백엔드
│   ├── main.py               앱 진입점 (uvicorn)
│   ├── config.py             환경 변수 로드
│   ├── models.py             Pydantic 요청/응답 모델
│   ├── routers/              API 라우터 (game · leaderboard · analytics)
│   ├── services/             핵심 로직 (bedrock · dynamo · game · analytics)
│   ├── prompts/              AI 심사원 프롬프트 & 레벨 설정
│   ├── requirements.txt
│   └── test_bedrock.py       Bedrock 연결 점검 스크립트
├── frontend/                 React + Vite 프론트엔드
│   └── src/
│       ├── components/        화면 컴포넌트 (Start · Game · Result · Leaderboard 등)
│       ├── hooks/             커스텀 훅 (useGameState · useTimer · useKonamiCode)
│       └── utils/             API 통신 · 점수 계산
├── aws/
│   └── iam-policy.json       배포용 IAM 최소 권한 정책
├── .env.example              환경 변수 템플릿
├── PROD.md                   프로젝트 기획서
├── DEPLOYMENT.md             AWS 배포 가이드 (단계별)
├── MAINTENANCE.md            유지보수 · 재배포 가이드
├── SECURITY.md               보안 아키텍처 가이드
└── README.md                 이 문서
```

---

## 로컬 개발 환경 실행

### 1. 사전 준비

- Python 3.11 이상
- Node.js 18 이상
- (AI 기능 사용 시) Amazon Bedrock 접근이 가능한 AWS 자격 증명

### 2. 환경 변수 설정

프로젝트 루트에서 템플릿을 복사합니다.

```bash
cp .env.example .env
```

> AI 심사원(Bedrock)을 실제로 동작시키려면 `.env`에 AWS 자격 증명을 입력해야
> 합니다. 자격 증명이 없으면 게임은 실행되지만 채팅 시 "심사원과의 통신 오류"가
> 발생합니다. 리더보드·분석 로그는 자격 증명이 없어도 mock 모드로 동작합니다.
> 자세한 내용은 `DEPLOYMENT.md` 및 `backend/test_bedrock.py` 참고.

### 3. 백엔드 실행

```bash
cd backend
python -m venv venv

# 가상환경 활성화
source venv/bin/activate          # macOS / Linux
venv\Scripts\activate             # Windows

pip install -r requirements.txt
python main.py
```

백엔드가 `http://localhost:8000` 에서 실행됩니다.
API 문서(Swagger UI)는 `http://localhost:8000/docs` 에서 확인할 수 있습니다.

### 4. 프론트엔드 실행

새 터미널에서:

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 으로 접속합니다.
(Vite 개발 서버가 `/api` 요청을 백엔드 8000번 포트로 자동 프록시합니다.)

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/game/start` | 새 게임 세션 생성, Level 1 질문 반환 |
| POST | `/api/game/chat` | 사용자 답변 전송, AI 심사원 평가 결과 반환 |
| GET | `/api/leaderboard` | Top 10 랭킹 조회 |
| POST | `/api/leaderboard` | 게임 클리어 점수 등록 |
| GET | `/api/analytics/summary` | 레벨별 취약도 분석 요약 |
| GET | `/api/analytics/logs` | 게임 로그 조회 (개발용) |
| GET | `/api/health` | 서버 상태 확인 |

---

## 데이터 분석 (Analytics)

모든 채팅 상호작용과 게임 결과는 DynamoDB 로그 테이블에 적재되어,
**"어떤 심사 항목에 사람들이 취약한지"** 를 분석할 수 있도록 설계되었습니다.

- `level_attempt` — 레벨별 시도 횟수
- `missing_criteria` — AI가 판정한 누락 통과 기준
- `/api/analytics/summary` — 레벨별 **세션 단위 통과율**, 클리어까지 평균 시도
  횟수, 가장 자주 누락된 통과 기준(`weak_criteria`)을 집계

---

## 배포 및 운영

| 문서 | 내용 |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md) | AWS EC2 단계별 배포 가이드 (처음부터 끝까지) |
| [MAINTENANCE.md](MAINTENANCE.md) | 재배포 · 패치 · 롤백 · 로그 확인 |
| [SECURITY.md](SECURITY.md) | 보안 아키텍처 (KMS · GuardDuty · WAF · DR 등) |
| [PROD.md](PROD.md) | 프로젝트 기획서 및 진행 현황 |

---

## 재미 요소 (Easter Egg)

시작 화면에서 아케이드 게임의 전설적인 **코나미 코드** `↑ ↑ ↓ ↓ ← → ← → B A`
를 입력하면 숨겨진 제작 크레딧이 나타납니다.

---

## 제작

**제작: 제프리킴 (Jeffrey Kim)**
