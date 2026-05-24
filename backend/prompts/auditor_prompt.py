"""
Cerberus: The Dark Auditor - 심사원 프롬프트 및 레벨 설정

각 레벨의 심사 영역·질문·통과 기준·통과 판정 방식(AND/OR)·시간/프롬프트 한도를
정의하고, 이를 system prompt 로 렌더링하는 템플릿을 제공합니다.

LEVEL_CONFIGS 는 **코드 기본값**입니다. 관리자 페이지에서 런타임에 수정된
설정이 있으면 `config_service` 가 그 값을 우선 사용하고, 없으면 여기 값으로
시드됩니다.

설계 노트
─────────
- 각 단계는 **독립적인 세션**으로 운영됩니다. 한 단계가 끝나면 화면과
  세션이 모두 초기화되고 다음 단계의 새 세션이 시작됩니다.
- `pass_logic` 으로 각 단계의 통과 판정 방식을 선택할 수 있습니다.
    * "AND" — 모든 통과 기준을 충족해야 합격 (엄격)
    * "OR"  — 통과 기준 중 하나 이상을 충족하면 합격 (관대)
- `time_limit` / `p_max` 가 비어 있으면 전역 game_params 값을 사용합니다.
- Level 3 은 의도적으로 **멀티 프롬프트 (여러 차례의 후속 질문)** 없이는
  통과하기 어렵도록 통과 기준 개수와 p_max 가 설정되어 있습니다.
"""


# ──────────────────────────────────────────────
# System Prompt 템플릿
# ──────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """당신은 ISMS(정보보호관리체계) 인증 심사원 '케르베로스'입니다.
당신의 역할은 엄격하지만 공정한 심사원으로서 피심사자의 답변을 평가하는 것입니다.

## 현재 심사 영역
{domain}

## 심사 질문
{question}

## 통과 기준 (각 항목별로 개별 평가)
{criteria_list}

## 통과 판정 방식
{pass_logic_explanation}

## 절대 규칙
- 절대로 정답이나 통과 기준을 먼저 알려주지 마십시오.
- 피심사자가 부족한 답변을 하면 추가 질문을 통해 보완할 기회를 주십시오.
- 반드시 한국어로 응답하십시오.
- 평가 결과는 반드시 evaluate_answer 도구를 사용하여 구조화된 형식으로 반환하십시오.
- 각 통과 기준에 대해 **개별적으로** 충족 여부를 판단하고, 충족하지 못한 항목의
  번호를 evaluate_answer 도구의 missing_criteria 배열에 담으십시오. 모든 기준을
  충족했으면 빈 배열 [] 을 반환하십시오.
- status 값은 위의 "통과 판정 방식" 규칙을 따라 결정하십시오.
- fail 인 경우 어떤 부분이 부족한지 힌트를 주되, 직접적인 정답은 알려주지 마십시오.
"""

PASS_LOGIC_EXPLANATIONS: dict[str, str] = {
    "AND": (
        "위 통과 기준을 **모두** 충족해야 합격(pass)입니다. "
        "단 하나라도 충족하지 못하면 불합격(fail) 입니다."
    ),
    "OR": (
        "위 통과 기준 중 **하나 이상**을 충족하면 합격(pass)입니다. "
        "모든 기준을 충족하지 못한 경우에만 불합격(fail) 입니다."
    ),
}


def normalize_pass_logic(value: object) -> str:
    """문자열을 'AND' / 'OR' 로 정규화. 알 수 없으면 'AND'."""
    if isinstance(value, str):
        upper = value.strip().upper()
        if upper in ("AND", "OR"):
            return upper
    return "AND"


def render_system_prompt(
    domain: str,
    question: str,
    pass_criteria: list[str],
    pass_logic: str = "AND",
) -> str:
    """레벨 설정으로부터 system prompt 텍스트를 생성합니다."""
    criteria_text = "\n".join(
        f"{i}. {c}" for i, c in enumerate(pass_criteria or [], start=1)
    )
    logic = normalize_pass_logic(pass_logic)
    explanation = PASS_LOGIC_EXPLANATIONS[logic]
    return SYSTEM_PROMPT_TEMPLATE.format(
        domain=domain,
        question=question,
        criteria_list=criteria_text,
        pass_logic_explanation=explanation,
    )


# ──────────────────────────────────────────────
# 레벨별 기본 설정 (관리자가 수정하지 않았을 때의 시드값)
#
# 난이도 곡선:
#   Level 1 — 워밍업.   기준 3개 · AND · 충분한 p_max(10)
#   Level 2 — 본 게임.  기준 4개 · AND · 중간 p_max(8) — 정책 여러 측면 묶음 질문
#   Level 3 — 보스전.   기준 5개 · AND · 빠듯한 p_max(6) — 단일 답변으론 통과 불가,
#                         반드시 여러 차례의 후속 답변(멀티 프롬프트)이 필요.
# ──────────────────────────────────────────────
LEVEL_CONFIGS: dict[int, dict] = {
    # ────────── Level 1: 물리적 보안 / 단말기 보안 ──────────
    1: {
        "domain": "물리적 보안 / 단말기 보안",
        "question": (
            "직원들이 자리를 비울 때 PC 화면 보호 조치는 어떻게 하고 계십니까?"
        ),
        "pass_criteria": [
            "화면 잠금(보호기) 설정 여부",
            "비밀번호를 통한 해제 방식",
            "5분 이내 자동 잠금 설정",
        ],
        "pass_logic": "AND",
        "time_limit": 240,
        "p_max": 10,
    },
    # ────────── Level 2: 접근 통제 / 계정 관리 ──────────
    2: {
        "domain": "접근 통제 / 계정 관리",
        "question": (
            "서버 및 DB 에 접근하는 관리자 계정의 (1) 비밀번호 구성·변경 정책, "
            "(2) 신규 권한 부여 절차, (3) 퇴직·인사이동 발생 시 계정 처리 방식을 "
            "모두 포함하여 설명해 주십시오."
        ),
        "pass_criteria": [
            "영문·숫자·특수문자 조합과 8자 이상 최소 길이를 만족하는 비밀번호 구성",
            "분기 1회 이상 주기적 비밀번호 변경 정책",
            "신규 권한 부여 시 책임자 승인 절차 운영",
            "퇴직·인사이동 발생 시 24시간 이내 계정 비활성화·회수",
        ],
        "pass_logic": "AND",
        "time_limit": 300,
        "p_max": 8,
    },
    # ────────── Level 3: 네트워크 보안 / 침해사고 대응 ──────────
    3: {
        "domain": "네트워크 보안 / 침해사고 대응",
        "question": (
            "개인정보가 저장된 운영 DB 에 대해 다음 세 가지를 **모두** 설명해 "
            "주십시오. (1) 평시 접근 통제·로그 리뷰 정책, (2) 침해사고 의심 시 "
            "초동 대응 절차, (3) 법정 신고 의무와 사후 재발 방지 대책."
        ),
        "pass_criteria": [
            "방화벽·접근제어 솔루션을 통한 네트워크 분리 및 비인가자 차단 정책",
            "독립된 보안 관리자가 DB 접근 로그를 월 1회 이상 정기 리뷰",
            "침해사고 발생 시 즉시 격리·증거 보존(포렌식 대비) 초동 절차",
            "사고 인지 후 24시간 이내 한국인터넷진흥원(KISA) 신고 및 영향받은 이용자 통지",
            "사고 원인 분석 후 재발 방지 대책 수립 및 절차 문서화",
        ],
        "pass_logic": "AND",
        "time_limit": 360,
        "p_max": 6,
    },
}
