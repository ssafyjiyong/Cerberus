"""
Cerberus: The Dark Auditor - 심사원 프롬프트 및 레벨 설정

각 레벨의 심사 영역·질문·통과 기준을 정의하고, 이를 system prompt 로
렌더링하는 템플릿(`SYSTEM_PROMPT_TEMPLATE`, `render_system_prompt`)을
제공합니다.

LEVEL_CONFIGS 는 **코드 기본값**입니다. 관리자 페이지에서 런타임에 수정된
설정이 있으면 `config_service` 가 그 값을 우선 사용하고, 없으면 여기 값으로
시드됩니다.
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

## 통과 기준 (아래 내용을 모두 충족해야 합격)
{criteria_list}

## 절대 규칙
- 절대로 정답이나 통과 기준을 먼저 알려주지 마십시오.
- 피심사자가 부족한 답변을 하면 추가 질문을 통해 보완할 기회를 주십시오.
- 반드시 한국어로 응답하십시오.
- 평가 결과는 반드시 evaluate_answer 도구를 사용하여 구조화된 형식으로 반환하십시오.
  도구 호출 시 status는 'pass' 또는 'fail'이어야 하며, message에 피드백을 작성하십시오.
- 답변이 모든 통과 기준을 충족하면 status를 'pass'로, 그렇지 않으면 'fail'로 설정하십시오.
- fail인 경우 어떤 부분이 부족한지 힌트를 주되, 직접적인 정답은 알려주지 마십시오.
- fail인 경우, 위 통과 기준 중 충족하지 못한 항목의 번호를 evaluate_answer 도구의 missing_criteria 배열에 담으십시오. pass인 경우 missing_criteria는 빈 배열 []로 두십시오.
"""


def render_system_prompt(
    domain: str, question: str, pass_criteria: list[str]
) -> str:
    """레벨 설정(domain·question·pass_criteria)으로부터 system prompt 텍스트를 생성합니다."""
    criteria_text = "\n".join(
        f"{i}. {c}" for i, c in enumerate(pass_criteria or [], start=1)
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        domain=domain,
        question=question,
        criteria_list=criteria_text,
    )


# ──────────────────────────────────────────────
# 레벨별 기본 설정 (관리자가 수정하지 않았을 때의 시드값)
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
    },
    # ────────── Level 2: 접근 통제 / 계정 관리 ──────────
    2: {
        "domain": "접근 통제 / 계정 관리",
        "question": (
            "서버 및 DB에 접근하는 관리자 계정의 비밀번호 복잡도와 "
            "주기적인 변경 정책에 대해 설명해 주세요."
        ),
        "pass_criteria": [
            "영문, 숫자, 특수문자를 조합한 비밀번호 구성",
            "최소 길이 제한(예: 8자 이상 또는 그에 준하는 기준)",
            "분기 1회 이상 주기적 비밀번호 변경",
        ],
    },
    # ────────── Level 3: 네트워크 보안 / 침해사고 대응 ──────────
    3: {
        "domain": "네트워크 보안 / 침해사고 대응",
        "question": (
            "개인정보가 저장된 DB에 대한 접근 통제 및 "
            "작업 내역 로그 리뷰는 누가, 얼마나 자주 수행합니까?"
        ),
        "pass_criteria": [
            "방화벽 또는 접근제어 솔루션을 통한 접근 통제",
            "비인가자 접근 차단 정책 운영",
            "독립된 보안 관리자가 월 1회 이상 로그 리뷰 수행",
        ],
    },
}
