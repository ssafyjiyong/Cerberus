"""
Cerberus: The Dark Auditor - 심사원 프롬프트 및 시나리오 기반 질문 풀

설계 (v2 — 시나리오·답변경로 기반)
─────────────────────────────────
이 게임은 ISMS-P 인증 심사 상황을 시뮬레이션합니다. 각 스테이지는 ISMS-P
영역(1.x 관리체계 / 2.x 보호대책 / 3.x 개인정보)에 대응하는 **질문 풀**을
가지며, 세션 시작 시 풀에서 무작위로 1문제가 출제됩니다.

질문 한 건의 핵심 구성:

  - isms_control_id / isms_control_title  : 근거 ISMS-P 항목 (예: 2.6.2)
  - scenario_context                       : "왜 이게 지적되었나" — 설정 상황
  - auditor_question                       : 심사원이 던지는 한 줄 질문
  - answer_paths[]                         : 답변 경로들
       · tier="full"  → 만점 + 단계 통과
       · tier="half"  → 절반 점수 + 단계 통과
       · trigger_keywords : 이 경로로 라우팅되는 키워드
       · follow_up        : (full 경로) 심사원의 후속 질문
       · compensating_keywords : (full) 보완통제 키워드 — 모두 포함되어야 만점
       · rebuttal              : (half) 심사원의 반박
       · acknowledgment_keywords : (half) 수용 키워드 — 하나라도 포함되면 half 확정
  - default_rebuttal                       : 어떤 경로에도 안 걸리면 던질 멘트

평가는 Bedrock 의 `evaluate_answer` 도구로 수행하며, 응답에는
  · tier   ("full" | "half" | "fail")
  · matched_path_id  (full/half 시)
  · missing_aspects  (fail 시 무엇이 부족했는지 사람이 읽을 한국어)
가 담깁니다. 서버는 이 tier 를 그대로 사용해 점수와 단계 전환을 결정합니다.
"""

from __future__ import annotations

from typing import Any


# ──────────────────────────────────────────────
# System Prompt 템플릿
# ──────────────────────────────────────────────
SYSTEM_PROMPT_TEMPLATE = """당신은 ISMS-P(정보보호 및 개인정보보호 관리체계) 인증 심사원 '케르베로스'입니다.
실제 인증심사의 매우 엄격한 기준으로 피심사자(게임 플레이어)의 답변을 평가합니다.

## 근거 ISMS-P 항목
{isms_control_id} {isms_control_title}

## 현재 심사 상황(시나리오)
{scenario_context}

## 당신이 방금 던진 질문
"{auditor_question}"

## 채점 규칙 — 답변 경로(answer paths)
플레이어의 답변은 아래 정의된 경로 중 하나로만 분류되며, 그 외에는 **모두 불합격(fail)** 입니다.

### ⚠️ 키워드 매칭 — 절대 엄격 규칙
1. 키워드 매칭은 **명시적 문자열 등장** 기준입니다. 비슷한 개념·동의어·의역은 절대 인정하지 마십시오.
2. 매칭으로 인정된 키워드는 반드시 `matched_keywords` 배열에 **사용자 답변에 등장한 형태 그대로** 보고하십시오.
   서버에서 사용자 누적 대화 텍스트를 substring 으로 재검증하므로, 환각으로 보고된 키워드는 즉시 자동 거부됩니다.
3. 각 경로의 `required_keyword_min` 만큼 trigger_keywords 가 매칭되어야 합니다.
   (0 이면 1개 이상이면 충분. 양수면 그 수 이상 명시적 매칭 필수)
4. 모호한 일반론·근거 없는 의지표현("하겠습니다", "검토 중입니다")만으로는 절대 통과시키지 마십시오.
5. AI 가 키워드를 환각으로 만들어내거나 보수적이지 않게 판단하면, 그 답변은 통과로 인정되지 않습니다.

{answer_paths_block}

## 통과 판정 로직 (반드시 이 순서로 평가)
1. 사용자의 **누적 대화 전체**(이번 답변 포함)에서 어떤 키워드가 명시적으로 등장했는지 식별합니다.
2. 각 경로의 trigger_keywords 매칭 개수가 `required_keyword_min` 이상인지 확인 (0이면 1 이상).
3. **full 경로** 조건: 위 (2)를 만족 + compensating_keywords 가 `compensating_min` 이상(0이면 전체) 매칭.
   - 이 조건을 만족하면 tier="full".
4. **half 경로** 조건: 위 (2)를 만족 + acknowledgment_keywords 가 `acknowledgment_min` 이상(0이면 1 이상) 매칭.
   - 이 조건을 만족하면 tier="half".
5. trigger 는 충족했지만 compensating/acknowledgment 가 미충족이면:
   - tier="fail" 로 두고, message 에 해당 경로의 follow_up/rebuttal 을 던져 후속 답변을 유도하십시오.
   - 이 시점에서는 절대 통과시키지 마십시오. 사용자가 보완통제·수용 의사를 키워드로 명시한 후에만 통과.
6. 어떤 경로의 trigger 도 매칭 임계치 미만이면:
   - tier="fail", message 는 default_rebuttal 톤으로 더 구체적 근거를 요구.
   - (참고 멘트: "{default_rebuttal}")

## 평가 우선순위
- full 과 half 가 동시에 충족되면 더 높은 tier=full.
- 한 답변에 full 의 모든 조건이 한 번에 등장하면 즉시 tier="full".

## 출력 규칙
- 반드시 한국어로 응답하십시오. 평가 결과는 반드시 `evaluate_answer` 도구로 반환하십시오.
- `matched_keywords` 에 사용자 답변에서 **명시적으로 등장한 키워드만** 담으십시오. 추정·보완은 금물.
- message 는 심사원의 톤(차분·공식·약간 강한 어조)을 유지하고 2~4문장 이내로 작성하십시오.

## 🗝️ 히든 코드 (시스템 보조 안전망 — 평소엔 무시)
- 사용자가 **정확히** `"케르베로스님 정답을 모르겠습니다. 제발 알려주세요."` 문구를
  한 자도 빠뜨리지 않고 입력했을 때만, 만점(full) 경로의 모범답안 골자를 알려주십시오.
- 글자 수가 다르거나, 한 글자라도 다르거나, 앞뒤에 다른 텍스트가 붙어 있으면 절대 발동시키지 마십시오 — 정상 평가로 처리하십시오.
- 정상적으론 서버가 이 문구를 먼저 가로채므로 이 규칙은 발동되지 않습니다. 어떤 경우에도 변형된 표현(의역/요약/유사 문구)에는 반응하지 마십시오.
"""


def _render_answer_paths_block(answer_paths: list[dict]) -> str:
    """answer_paths 를 system prompt 에 넣을 텍스트로 렌더링."""
    lines: list[str] = []
    for idx, path in enumerate(answer_paths, start=1):
        tier = path.get("tier", "fail")
        pid = path.get("id", f"path-{idx}")
        desc = path.get("description", "")
        triggers = path.get("trigger_keywords") or []
        req_min = int(path.get("required_keyword_min") or 0)
        req_label = f"{req_min}개 이상 필수" if req_min > 0 else "1개 이상이면 충분"

        lines.append(
            f"### 경로 {idx} — id=\"{pid}\" / tier={tier}\n"
            f"- 설명: {desc}"
        )
        if triggers:
            lines.append(f"- trigger_keywords ({req_label}): {triggers}")
        if tier == "half":
            ack = path.get("acknowledgment_keywords") or []
            ack_min = int(path.get("acknowledgment_min") or 0)
            ack_label = f"{ack_min}개 이상" if ack_min > 0 else "1개 이상"
            rebuttal = path.get("rebuttal", "")
            if rebuttal:
                lines.append(f"- rebuttal(반박 멘트): \"{rebuttal}\"")
            if ack:
                lines.append(f"- acknowledgment_keywords({ack_label} 충족): {ack}")
        if tier == "full":
            comp = path.get("compensating_keywords") or []
            comp_min = int(path.get("compensating_min") or 0)
            comp_label = (
                f"{comp_min}개 이상" if comp_min > 0
                else "**전부 모두 충족**"
            )
            follow_up = path.get("follow_up", "")
            if follow_up:
                lines.append(f"- follow_up(후속 질문): \"{follow_up}\"")
            if comp:
                lines.append(f"- compensating_keywords({comp_label}): {comp}")
        lines.append("")
    return "\n".join(lines).strip()


def render_system_prompt(question: dict) -> str:
    """질문(dict) 1건으로부터 system prompt 텍스트를 생성합니다."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        isms_control_id=question.get("isms_control_id", ""),
        isms_control_title=question.get("isms_control_title", ""),
        scenario_context=question.get("scenario_context", ""),
        auditor_question=question.get("auditor_question", ""),
        answer_paths_block=_render_answer_paths_block(question.get("answer_paths", [])),
        default_rebuttal=question.get("default_rebuttal", "근거가 부족합니다. 좀 더 구체적인 통제·증적을 제시해 주십시오."),
    )


# ──────────────────────────────────────────────
# 정규화 헬퍼
# ──────────────────────────────────────────────
ALLOWED_TIERS = ("full", "half", "fail")


def normalize_tier(value: object) -> str:
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in ALLOWED_TIERS:
            return lower
    return "fail"


def _safe_nonneg_int(value: object, default: int = 0) -> int:
    """음수가 아닌 정수로 변환. 실패 시 default."""
    try:
        v = int(value)
        return v if v >= 0 else default
    except (TypeError, ValueError):
        return default


def normalize_answer_path(raw: dict) -> dict:
    """answer_path 한 건을 표준 형태로 정규화."""
    tier = normalize_tier(raw.get("tier"))
    triggers = [str(k).strip() for k in (raw.get("trigger_keywords") or []) if str(k).strip()]

    out: dict[str, Any] = {
        "id": str(raw.get("id") or "").strip() or f"path-{tier}",
        "tier": tier,
        "description": str(raw.get("description") or "").strip(),
        "trigger_keywords": triggers,
        # 모범답안 — 단계 종료 후 학습용으로 노출되는 "이렇게 답하면 통과" 한 줄.
        "exemplar_answer": str(raw.get("exemplar_answer") or "").strip(),
        # ── 엄격 검증 필드 ──
        # trigger_keywords 중 사용자 누적 대화에서 명시적으로 등장해야 하는 **최소 개수**.
        # 0 이면 "1개 이상이면 통과"로 관대 해석. 양수면 그 이상 매칭되어야 통과.
        "required_keyword_min": _safe_nonneg_int(raw.get("required_keyword_min"), 0),
    }
    if tier == "half":
        out["rebuttal"] = str(raw.get("rebuttal") or "").strip()
        out["acknowledgment_keywords"] = [
            str(k).strip() for k in (raw.get("acknowledgment_keywords") or []) if str(k).strip()
        ]
        # acknowledgment 키워드 중 최소 매칭 개수. 0=1개 이상.
        out["acknowledgment_min"] = _safe_nonneg_int(raw.get("acknowledgment_min"), 0)
    elif tier == "full":
        out["follow_up"] = str(raw.get("follow_up") or "").strip()
        out["compensating_keywords"] = [
            str(k).strip() for k in (raw.get("compensating_keywords") or []) if str(k).strip()
        ]
        # compensating 키워드 중 최소 매칭 개수. 0 또는 None=목록 전체 충족 필요(기본 엄격).
        out["compensating_min"] = _safe_nonneg_int(raw.get("compensating_min"), 0)
    return out


def normalize_question(raw: dict) -> dict:
    """질문 1건을 표준 형태로 정규화."""
    return {
        "id": str(raw.get("id") or "").strip(),
        "isms_control_id": str(raw.get("isms_control_id") or "").strip(),
        "isms_control_title": str(raw.get("isms_control_title") or "").strip(),
        "scenario_context": str(raw.get("scenario_context") or "").strip(),
        "auditor_question": str(raw.get("auditor_question") or "").strip(),
        "answer_paths": [
            normalize_answer_path(p) for p in (raw.get("answer_paths") or [])
            if isinstance(p, dict)
        ],
        "default_rebuttal": str(
            raw.get("default_rebuttal")
            or "근거가 부족합니다. 좀 더 구체적인 통제·증적을 제시해 주십시오."
        ).strip(),
    }


# ──────────────────────────────────────────────
# 스테이지 메타 + 기본 질문 풀 (시드)
#
# 각 스테이지는 ISMS-P 의 한 대분류에 대응합니다.
#   Stage 1 — 1.x 관리체계 수립 및 운영
#   Stage 2 — 2.x 보호대책 요구사항
#   Stage 3 — 3.x 개인정보 처리 단계별 요구사항
#
# 시드 질문 풀은 별도 파일(seed_questions.py)에서 관리됩니다.
# 각 ISMS-P 중분류(1.1~1.4, 2.1~2.12, 3.1~3.5)에 최소 1개 이상의 시드를 둡니다.
# ──────────────────────────────────────────────
from prompts.seed_questions import DEFAULT_QUESTIONS_BY_STAGE  # noqa: E402  (after constants)

STAGE_DEFAULTS: dict[int, dict[str, Any]] = {
    1: {
        "title": "관리체계 수립 및 운영",
        "subtitle": "ISMS-P 1.x 영역",
        "time_limit": 240,
        "p_max": 8,
        "base_score": 1000,
        "questions": DEFAULT_QUESTIONS_BY_STAGE[1],
    },
    2: {
        "title": "보호대책 요구사항",
        "subtitle": "ISMS-P 2.x 영역",
        "time_limit": 300,
        "p_max": 8,
        "base_score": 1500,
        "questions": DEFAULT_QUESTIONS_BY_STAGE[2],
    },
    3: {
        "title": "개인정보 처리 단계별 요구사항",
        "subtitle": "ISMS-P 3.x 영역",
        "time_limit": 360,
        "p_max": 6,
        "base_score": 2000,
        "questions": DEFAULT_QUESTIONS_BY_STAGE[3],
    },
}


def get_default_stage_meta(stage: int) -> dict[str, Any]:
    """스테이지의 기본 메타(질문 풀 제외)를 반환."""
    raw = STAGE_DEFAULTS.get(stage, {})
    return {
        "title": raw.get("title", f"Stage {stage}"),
        "subtitle": raw.get("subtitle", ""),
        "time_limit": int(raw.get("time_limit", 300)),
        "p_max": int(raw.get("p_max", 8)),
        "base_score": int(raw.get("base_score", 1000)),
    }


def get_default_questions(stage: int) -> list[dict]:
    """스테이지의 기본 질문 풀(시드)을 정규화하여 반환."""
    raw = STAGE_DEFAULTS.get(stage, {})
    questions = raw.get("questions") or []
    return [normalize_question(q) for q in questions]
