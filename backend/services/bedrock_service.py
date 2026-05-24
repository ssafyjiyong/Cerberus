"""
Cerberus: The Dark Auditor - Amazon Bedrock 서비스

Bedrock Converse API + Tool Use 로 ISMS-P 심사원 AI 의 답변 평가를 수행합니다.

새 평가 모델 (v2 — tier 기반):
    tier ∈ { "full", "half", "fail" }
    - full : 정의된 full 경로의 trigger + compensating 키워드를 누적 대화에서 모두 충족
    - half : 정의된 half 경로의 trigger + acknowledgment 키워드를 누적 대화에서 모두 충족
    - fail : 위 어디에도 해당하지 않거나 trigger 만 나오고 보완이 없음

서버는 AI 의 tier 를 그대로 사용하되, matched_path_id 의 유효성과 trigger 키워드의
실제 등장 여부를 후처리로 검증해 환각(hallucination)을 줄입니다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION
from prompts.auditor_prompt import normalize_tier, render_system_prompt
from services import config_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Bedrock 클라이언트 초기화
# ──────────────────────────────────────────────
try:
    _bedrock_client = boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
    )
    logger.info("Bedrock 클라이언트가 성공적으로 초기화되었습니다. (리전: %s)", AWS_REGION)
except Exception as exc:
    logger.warning("Bedrock 클라이언트 초기화 실패: %s", exc)
    _bedrock_client = None

# ──────────────────────────────────────────────
# Tool Use 스키마 정의 (v2 — tier 기반)
# ──────────────────────────────────────────────
EVALUATE_ANSWER_TOOL: dict[str, Any] = {
    "toolSpec": {
        "name": "evaluate_answer",
        "description": (
            "피심사자의 답변을 시나리오 기반 answer_paths 에 따라 평가하고 결과를 "
            "구조화 JSON 으로 반환합니다."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "string",
                        "enum": ["full", "half", "fail"],
                        "description": (
                            "평가 결과 등급. full=만점 통과, half=절반 점수 통과, fail=불합격."
                        ),
                    },
                    "matched_path_id": {
                        "type": "string",
                        "description": (
                            "tier 가 full/half 일 때 충족한 answer_path 의 id. "
                            "fail 일 때는 빈 문자열 또는 가장 근접했던 path id."
                        ),
                    },
                    "message": {
                        "type": "string",
                        "description": (
                            "심사원의 피드백 메시지(한국어). half/full 진입을 위해 후속 답변이 "
                            "필요하면 해당 rebuttal/follow_up 을 톤에 맞춰 던지십시오. "
                            "fail 이면 default_rebuttal 톤으로 부족한 지점을 짚어 주십시오."
                        ),
                    },
                    "missing_aspects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "fail 시 무엇이 부족했는지 사람이 읽을 한국어 요약 항목들. "
                            "예: ['보완통제(위험평가/경영진 승인) 미언급']. pass 시 빈 배열."
                        ),
                    },
                },
                "required": ["tier", "matched_path_id", "message", "missing_aspects"],
            }
        },
    }
}


def evaluate_answer(question: dict, conversation_history: list[dict]) -> dict:
    """
    Bedrock Converse API 를 호출하여 피심사자의 답변을 평가합니다.

    Args:
        question: 세션 스냅샷의 질문 dict (auditor_prompt.normalize_question 결과)
        conversation_history: [{"role": "user"|"assistant", "content": "..."}, ...]

    Returns:
        {
          "tier": "full"|"half"|"fail",
          "matched_path_id": "...",
          "message": "...",
          "missing_aspects": [...]
        }
    """
    if _bedrock_client is None:
        raise RuntimeError(
            "Bedrock 클라이언트가 초기화되지 않았습니다. AWS 자격 증명을 확인하세요."
        )

    if not question:
        raise ValueError("질문(question) 이 비어있습니다.")

    system_prompt = render_system_prompt(question)

    messages: list[dict[str, Any]] = []
    for entry in conversation_history:
        messages.append(
            {
                "role": entry["role"],
                "content": [{"text": entry["content"]}],
            }
        )

    try:
        response = _bedrock_client.converse(
            modelId=config_service.get_bedrock_model_id(),
            system=[{"text": system_prompt}],
            messages=messages,
            toolConfig={
                "tools": [EVALUATE_ANSWER_TOOL],
                "toolChoice": {
                    "tool": {"name": "evaluate_answer"},
                },
            },
            inferenceConfig={
                "temperature": 0.2,
                "maxTokens": 1024,
            },
        )
        parsed = _parse_tool_use_response(response)

        # ── 후처리 검증: matched_path_id 가 실제 정의된 경로인지 확인 ──
        valid_path_ids = {p["id"] for p in question.get("answer_paths", [])}
        tier = normalize_tier(parsed.get("tier"))
        matched_id = str(parsed.get("matched_path_id") or "").strip()

        if tier in ("full", "half"):
            if matched_id not in valid_path_ids:
                logger.warning(
                    "AI가 보고한 matched_path_id '%s' 가 정의된 경로에 없음 → fail 처리",
                    matched_id,
                )
                tier = "fail"
                matched_id = ""
            else:
                # 경로 tier 와 보고된 tier 가 일치하는지 검증 (downgrade 만 허용)
                target_path = next(
                    (p for p in question["answer_paths"] if p["id"] == matched_id), None
                )
                if target_path:
                    path_tier = normalize_tier(target_path.get("tier"))
                    # full 경로 → half 보고는 이상하지만 그대로 두고,
                    # half 경로 → full 보고는 path 정의를 신뢰하여 half 로 강등.
                    if path_tier == "half" and tier == "full":
                        tier = "half"
                    if path_tier == "fail":
                        tier = "fail"

        parsed["tier"] = tier
        parsed["matched_path_id"] = matched_id
        # 호환 필드: 기존 호출자가 status 를 기대할 수 있어 함께 채움
        parsed["status"] = "fail" if tier == "fail" else "pass"
        return parsed

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_msg = exc.response["Error"]["Message"]
        logger.error("Bedrock API 호출 실패 [%s]: %s", error_code, error_msg)
        raise RuntimeError(f"Bedrock API 오류: {error_code} - {error_msg}") from exc


def _parse_tool_use_response(response: dict) -> dict:
    """Converse API 응답에서 tool_use 결과를 추출합니다."""
    try:
        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        for block in content_blocks:
            if "toolUse" in block:
                tool_input = block["toolUse"].get("input", {})
                tier = normalize_tier(tool_input.get("tier"))
                msg = tool_input.get("message", "평가를 완료할 수 없습니다.")
                matched_id = str(tool_input.get("matched_path_id") or "").strip()
                missing_raw = tool_input.get("missing_aspects") or []
                missing = [str(x).strip() for x in missing_raw if str(x).strip()]
                return {
                    "tier": tier,
                    "matched_path_id": matched_id,
                    "message": msg,
                    "missing_aspects": missing,
                }

        # toolUse 가 없으면 텍스트 응답 파싱 시도
        for block in content_blocks:
            if "text" in block:
                text = block["text"]
                logger.warning("toolUse 블록 없음. 텍스트 응답에서 파싱 시도: %s", text[:120])
                try:
                    parsed = json.loads(text)
                    return {
                        "tier": normalize_tier(parsed.get("tier")),
                        "matched_path_id": str(parsed.get("matched_path_id") or "").strip(),
                        "message": str(parsed.get("message") or text),
                        "missing_aspects": [
                            str(x).strip() for x in (parsed.get("missing_aspects") or []) if str(x).strip()
                        ],
                    }
                except json.JSONDecodeError:
                    return {
                        "tier": "fail",
                        "matched_path_id": "",
                        "message": text,
                        "missing_aspects": [],
                    }

        logger.error("Bedrock 응답에 유효한 콘텐츠가 없습니다: %s", response)
        return {
            "tier": "fail",
            "matched_path_id": "",
            "message": "심사원의 응답을 처리할 수 없습니다. 다시 시도해 주세요.",
            "missing_aspects": [],
        }

    except (KeyError, TypeError) as exc:
        logger.error("Bedrock 응답 파싱 오류: %s", exc)
        return {
            "tier": "fail",
            "matched_path_id": "",
            "message": "응답 처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
            "missing_aspects": [],
        }


# ──────────────────────────────────────────────
# AI 어시스트 (관리자 페이지 — 문제 생성/다듬기)
# ──────────────────────────────────────────────
def _simple_text_call(user_msg: str, system_msg: str, max_tokens: int = 512) -> str:
    """단순 텍스트 응답을 받는 Converse 호출 헬퍼."""
    if _bedrock_client is None:
        raise RuntimeError("Bedrock 클라이언트가 초기화되지 않았습니다.")

    response = _bedrock_client.converse(
        modelId=config_service.get_bedrock_model_id(),
        system=[{"text": system_msg}],
        messages=[{"role": "user", "content": [{"text": user_msg}]}],
        inferenceConfig={"temperature": 0.6, "maxTokens": max_tokens},
    )
    for block in response.get("output", {}).get("message", {}).get("content", []):
        if "text" in block:
            return block["text"].strip()
    return ""


def generate_scenario(isms_control_id: str, isms_control_title: str, hint: str = "") -> str:
    """주어진 ISMS-P 항목에 대해 자연스러운 심사 시나리오 1문단을 생성."""
    user_msg = (
        f"ISMS-P 항목: {isms_control_id} {isms_control_title}\n"
        f"추가 힌트: {hint or '(없음)'}\n\n"
        "위 항목과 관련하여, 인증심사 현장에서 심사원이 지적할 만한 구체적이고 "
        "현실적인 상황을 **한 문단(2~4문장)** 으로 작성하십시오. "
        "AWS·SaaS·내부 시스템 등 어느 환경이든 자연스러우면 됩니다. "
        "추가 설명·번호·따옴표 없이 본문만 출력하십시오."
    )
    system_msg = "당신은 ISMS-P 인증 심사 시나리오를 작성하는 보안 컨설턴트입니다."
    return _simple_text_call(user_msg, system_msg)


def generate_auditor_question(scenario: str, isms_control_title: str = "") -> str:
    """시나리오에 어울리는 심사원 질문 한 줄을 생성."""
    user_msg = (
        f"관련 ISMS-P 항목: {isms_control_title or '(미지정)'}\n"
        f"심사 시나리오:\n{scenario}\n\n"
        "위 상황에서 심사원이 피심사자에게 던질 **한 줄 질문**을 작성하십시오. "
        "추가 설명·번호·따옴표 없이 질문만 출력하십시오."
    )
    system_msg = "당신은 ISMS-P 인증 심사 질문을 정확하고 짧게 작성하는 보안 컨설턴트입니다."
    return _simple_text_call(user_msg, system_msg)


def polish_text(text: str, kind: str = "question") -> str:
    """기존 문장을 의미는 유지한 채 더 명확하고 자연스럽게 다듬습니다."""
    kind_label = {
        "question": "ISMS-P 심사 질문",
        "scenario": "ISMS-P 심사 시나리오 문단",
        "rebuttal": "심사원의 반박 멘트",
        "follow_up": "심사원의 후속 질문",
        "criterion": "ISMS-P 통과 기준 한 항목",
    }.get(kind, "문장")

    user_msg = (
        f"다음 {kind_label}을(를) 더 명확하고 자연스러운 한국어로 다듬어 주십시오. "
        "의미를 바꾸지 말고, 추가 설명 없이 다듬어진 문장만 그대로 출력하십시오.\n\n"
        f"원문:\n{text}"
    )
    system_msg = "당신은 한국어 보안 문서를 정확하고 간결하게 다듬는 편집자입니다."
    return _simple_text_call(user_msg, system_msg)


# ──────────────────────────────────────────────
# 답변 경로 자동 생성 (관리자 편의 도구)
# ──────────────────────────────────────────────
_GENERATE_PATHS_TOOL: dict[str, Any] = {
    "toolSpec": {
        "name": "provide_answer_paths",
        "description": (
            "ISMS-P 심사 시나리오에 대한 정답 경로(answer_paths)를 절반/만점 각 1개씩 "
            "총 2개 생성합니다. 각 경로에는 모범답안(exemplar_answer)이 반드시 포함됩니다."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "answer_paths": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "tier": {"type": "string", "enum": ["full", "half"]},
                                "description": {"type": "string"},
                                "trigger_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "rebuttal": {"type": "string"},
                                "acknowledgment_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "follow_up": {"type": "string"},
                                "compensating_keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "exemplar_answer": {
                                    "type": "string",
                                    "description": (
                                        "이 경로로 통과하는 모범답안 1~3문장. "
                                        "trigger_keywords 와 보완통제(compensating/"
                                        "acknowledgment)를 자연스럽게 녹여 작성."
                                    ),
                                },
                            },
                            "required": ["id", "tier", "trigger_keywords", "exemplar_answer"],
                        },
                    }
                },
                "required": ["answer_paths"],
            }
        },
    }
}


def generate_answer_paths(scenario: str, auditor_question: str, isms_control_title: str = "") -> list[dict]:
    """시나리오/질문으로부터 half + full 답변 경로 2개를 자동 생성."""
    if _bedrock_client is None:
        raise RuntimeError("Bedrock 클라이언트가 초기화되지 않았습니다.")

    user_msg = (
        f"관련 ISMS-P 항목: {isms_control_title or '(미지정)'}\n"
        f"시나리오:\n{scenario}\n\n"
        f"심사원 질문: {auditor_question}\n\n"
        "이 상황에 대한 **answer_paths 2개**를 `provide_answer_paths` 도구로 반환하십시오.\n"
        "- 1개는 tier=\"half\": trigger_keywords(키워드 2~4개) + rebuttal(반박 한 문장) + "
        "acknowledgment_keywords(수용 키워드 2~3개) 포함.\n"
        "- 1개는 tier=\"full\": trigger_keywords(2~4개) + follow_up(보완통제 질문 한 문장) + "
        "compensating_keywords(2~3개) 포함.\n"
        "- 각 경로마다 exemplar_answer(모범답안) 1~3문장: 피심사자가 이 경로로 통과하기 "
        "위해 실제로 답변할 만한 한국어 모범 답변을 작성하십시오. 키워드와 보완통제를 "
        "자연스럽게 포함시켜야 합니다.\n"
        "키워드는 짧고 명확한 한국어 명사구로 작성하십시오."
    )
    system_msg = (
        "당신은 ISMS-P 인증 심사의 정답 패턴을 설계하는 보안 컨설턴트입니다. "
        "현실적인 통제·증적·보완통제 용어를 사용하십시오."
    )

    response = _bedrock_client.converse(
        modelId=config_service.get_bedrock_model_id(),
        system=[{"text": system_msg}],
        messages=[{"role": "user", "content": [{"text": user_msg}]}],
        toolConfig={
            "tools": [_GENERATE_PATHS_TOOL],
            "toolChoice": {"tool": {"name": "provide_answer_paths"}},
        },
        inferenceConfig={"temperature": 0.5, "maxTokens": 1024},
    )

    for block in response.get("output", {}).get("message", {}).get("content", []):
        if "toolUse" in block:
            raw_paths = block["toolUse"].get("input", {}).get("answer_paths", [])
            if isinstance(raw_paths, list):
                return [p for p in raw_paths if isinstance(p, dict)]
    return []
