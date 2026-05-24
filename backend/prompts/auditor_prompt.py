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
실제 인증심사의 엄격한 기준으로 피심사자(게임 플레이어)의 답변을 평가합니다.

## 근거 ISMS-P 항목
{isms_control_id} {isms_control_title}

## 현재 심사 상황(시나리오)
{scenario_context}

## 당신이 방금 던진 질문
"{auditor_question}"

## 채점 규칙 — 답변 경로(answer paths)
플레이어의 답변은 아래 정의된 경로 중 하나로만 분류되며, 그 외에는 **모두 불합격(fail)** 입니다.
키워드는 "정확히 그 단어가 등장해야" 인정되는 것이 아니라, **명백히 같은 개념**이 답변에 드러나야 인정됩니다.
모호한 일반론·근거 없는 단정·예시 없는 추상적 답변은 절대 인정하지 마십시오.

{answer_paths_block}

## 절대 규칙
- 답변이 위 경로 중 어떤 것에도 해당하지 않으면 tier="fail" 로 평가하고, 직접 정답을 알려주지 마십시오.
  대신 시나리오 맥락에서 더 구체적인 근거·통제·증적이 필요하다는 점을 한국어로 짧게 지적해 주십시오.
  (참고 멘트: "{default_rebuttal}")
- half 경로의 경우: 플레이어의 **이번 답변**이 trigger_keywords 에 해당하지만 아직 acknowledgment_keywords
  가 보이지 않으면 tier="fail" 로 두고, message 에 rebuttal 을 그대로 또는 비슷한 톤으로 던져 후속
  답변을 유도하십시오. 같은 세션의 **누적 대화**에서 trigger 와 acknowledgment 가 모두 나타났다면
  tier="half" 로 판정하십시오.
- full 경로도 동일: trigger_keywords 만 나오고 compensating_keywords 가 안 보이면 tier="fail" 로 두고
  follow_up 을 던지십시오. 누적 대화에서 trigger 와 compensating 이 모두 나타났다면 tier="full".
- 한 답변에 full 의 trigger + compensating 이 한 번에 등장하면 즉시 tier="full".
- half 와 full 경로가 동시에 만족되면 더 높은 tier(full)를 채택합니다.
- 반드시 한국어로 응답하십시오. 평가 결과는 반드시 `evaluate_answer` 도구로 반환하십시오.
- message 는 심사원의 톤(차분·공식·약간 강한 어조)을 유지하고 2~4문장 이내로 작성하십시오.
"""


def _render_answer_paths_block(answer_paths: list[dict]) -> str:
    """answer_paths 를 system prompt 에 넣을 텍스트로 렌더링."""
    lines: list[str] = []
    for idx, path in enumerate(answer_paths, start=1):
        tier = path.get("tier", "fail")
        pid = path.get("id", f"path-{idx}")
        desc = path.get("description", "")
        triggers = path.get("trigger_keywords") or []
        lines.append(
            f"### 경로 {idx} — id=\"{pid}\" / tier={tier}\n"
            f"- 설명: {desc}"
        )
        if triggers:
            lines.append(f"- trigger_keywords: {triggers}")
        if tier == "half":
            ack = path.get("acknowledgment_keywords") or []
            rebuttal = path.get("rebuttal", "")
            if rebuttal:
                lines.append(f"- rebuttal(반박 멘트): \"{rebuttal}\"")
            if ack:
                lines.append(f"- acknowledgment_keywords(수용 키워드, 1개 이상): {ack}")
        if tier == "full":
            comp = path.get("compensating_keywords") or []
            follow_up = path.get("follow_up", "")
            if follow_up:
                lines.append(f"- follow_up(후속 질문): \"{follow_up}\"")
            if comp:
                lines.append(f"- compensating_keywords(보완통제, 모두 충족): {comp}")
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


def normalize_answer_path(raw: dict) -> dict:
    """answer_path 한 건을 표준 형태로 정규화."""
    tier = normalize_tier(raw.get("tier"))
    out: dict[str, Any] = {
        "id": str(raw.get("id") or "").strip() or f"path-{tier}",
        "tier": tier,
        "description": str(raw.get("description") or "").strip(),
        "trigger_keywords": [str(k).strip() for k in (raw.get("trigger_keywords") or []) if str(k).strip()],
        # 모범답안 — 단계 종료 후 학습용으로 노출되는 "이렇게 답하면 통과" 한 줄.
        "exemplar_answer": str(raw.get("exemplar_answer") or "").strip(),
    }
    if tier == "half":
        out["rebuttal"] = str(raw.get("rebuttal") or "").strip()
        out["acknowledgment_keywords"] = [
            str(k).strip() for k in (raw.get("acknowledgment_keywords") or []) if str(k).strip()
        ]
    elif tier == "full":
        out["follow_up"] = str(raw.get("follow_up") or "").strip()
        out["compensating_keywords"] = [
            str(k).strip() for k in (raw.get("compensating_keywords") or []) if str(k).strip()
        ]
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
