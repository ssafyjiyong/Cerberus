"""
Cerberus: The Dark Auditor - Amazon Bedrock 서비스

Bedrock Converse API를 사용하여 ISMS 심사원 AI의 답변 평가를 수행합니다.
Tool Use(Function Calling)를 활용하여 구조화된 JSON 응답을 보장합니다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config import AWS_REGION
from prompts.auditor_prompt import render_system_prompt
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
# Tool Use 스키마 정의
# ──────────────────────────────────────────────
EVALUATE_ANSWER_TOOL: dict[str, Any] = {
    "toolSpec": {
        "name": "evaluate_answer",
        "description": (
            "피심사자의 답변을 평가하고 결과를 구조화된 JSON으로 반환합니다. "
            "status는 반드시 'pass' 또는 'fail'이어야 합니다."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pass", "fail"],
                        "description": "평가 결과: 'pass'(합격) 또는 'fail'(불합격)",
                    },
                    "message": {
                        "type": "string",
                        "description": "심사원의 피드백 메시지 (한국어)",
                    },
                    "missing_criteria": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": (
                            "불합격(fail) 시 피심사자가 충족하지 못한 통과 기준의 "
                            "번호 목록입니다. 예: 1번과 3번 기준이 부족하면 [1, 3]. "
                            "합격(pass) 시에는 빈 배열 []을 반환하십시오."
                        ),
                    },
                },
                "required": ["status", "message", "missing_criteria"],
            }
        },
    }
}


def evaluate_answer(level: int, conversation_history: list[dict]) -> dict:
    """
    Bedrock Converse API를 호출하여 피심사자의 답변을 평가합니다.

    Args:
        level: 현재 레벨 번호 (1~3)
        conversation_history: 대화 이력 리스트
            각 항목은 {"role": "user"|"assistant", "content": "..."} 형태

    Returns:
        {"status": "pass"|"fail", "message": "..."} 형태의 딕셔너리

    Raises:
        RuntimeError: Bedrock 클라이언트가 초기화되지 않았거나 API 호출 실패 시
    """
    if _bedrock_client is None:
        raise RuntimeError(
            "Bedrock 클라이언트가 초기화되지 않았습니다. AWS 자격 증명을 확인하세요."
        )

    level_config = config_service.get_level_config(level)
    if level_config is None:
        raise ValueError(f"유효하지 않은 레벨입니다: {level}")

    # 동적 설정으로부터 system prompt 를 매번 렌더링 (관리자 수정이 즉시 반영됨)
    system_prompt = render_system_prompt(
        domain=level_config.get("domain", ""),
        question=level_config.get("question", ""),
        pass_criteria=level_config.get("pass_criteria", []),
    )

    # Converse API용 메시지 형식으로 변환
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
                "temperature": 0.3,
                "maxTokens": 1024,
            },
        )

        # Tool Use 응답 파싱
        return _parse_tool_use_response(response)

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_msg = exc.response["Error"]["Message"]
        logger.error("Bedrock API 호출 실패 [%s]: %s", error_code, error_msg)
        raise RuntimeError(f"Bedrock API 오류: {error_code} - {error_msg}") from exc


def _parse_tool_use_response(response: dict) -> dict:
    """
    Converse API 응답에서 tool_use 결과를 추출합니다.

    Args:
        response: Bedrock Converse API 응답

    Returns:
        {"status": "pass"|"fail", "message": "..."} 딕셔너리
    """
    try:
        output = response.get("output", {})
        message = output.get("message", {})
        content_blocks = message.get("content", [])

        for block in content_blocks:
            if "toolUse" in block:
                tool_input = block["toolUse"].get("input", {})
                status = tool_input.get("status", "fail")
                msg = tool_input.get("message", "평가를 완료할 수 없습니다.")

                # status 값 검증
                if status not in ("pass", "fail"):
                    logger.warning(
                        "예상치 못한 status 값: '%s' → 'fail'로 처리합니다.", status
                    )
                    status = "fail"

                return {
                    "status": status,
                    "message": msg,
                    "missing_criteria": _normalize_missing_criteria(
                        tool_input.get("missing_criteria"), status
                    ),
                }

        # toolUse 블록이 없는 경우 텍스트 응답에서 추출 시도
        for block in content_blocks:
            if "text" in block:
                text = block["text"]
                logger.warning("toolUse 블록 없음. 텍스트 응답에서 파싱 시도: %s", text[:100])
                try:
                    parsed = json.loads(text)
                    parsed_status = parsed.get("status", "fail")
                    return {
                        "status": parsed_status,
                        "message": parsed.get("message", text),
                        "missing_criteria": _normalize_missing_criteria(
                            parsed.get("missing_criteria"), parsed_status
                        ),
                    }
                except json.JSONDecodeError:
                    return {
                        "status": "fail",
                        "message": text,
                        "missing_criteria": [],
                    }

        # 어떤 콘텐츠 블록도 없는 경우
        logger.error("Bedrock 응답에 유효한 콘텐츠가 없습니다: %s", response)
        return {
            "status": "fail",
            "message": "심사원의 응답을 처리할 수 없습니다. 다시 시도해 주세요.",
            "missing_criteria": [],
        }

    except (KeyError, TypeError) as exc:
        logger.error("Bedrock 응답 파싱 오류: %s", exc)
        return {
            "status": "fail",
            "message": "응답 처리 중 오류가 발생했습니다. 다시 시도해 주세요.",
            "missing_criteria": [],
        }


def _normalize_missing_criteria(raw: Any, status: str) -> list[int]:
    """
    AI가 반환한 missing_criteria 값을 정수 리스트로 정규화합니다.

    합격(pass) 시에는 항상 빈 리스트를 반환하며, 정수로 해석할 수 없는
    값은 걸러냅니다.
    """
    if status == "pass" or not isinstance(raw, list):
        return []
    result: list[int] = []
    for item in raw:
        if isinstance(item, bool):
            continue
        if isinstance(item, (int, float)):
            result.append(int(item))
        elif isinstance(item, str) and item.strip().isdigit():
            result.append(int(item.strip()))
    return result


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


def generate_question(level: int, hint: str = "") -> str:
    """주어진 레벨의 심사 영역에 맞는 새 ISMS 심사 질문을 한 문장으로 생성합니다."""
    level_config = config_service.get_level_config(level) or {}
    domain = level_config.get("domain", "")

    user_msg = (
        f"심사 영역: {domain}\n"
        f"추가 힌트: {hint or '(없음)'}\n\n"
        "위 영역에 어울리는 ISMS 인증 심사 질문을 **한 문장**으로 작성해 주십시오. "
        "다른 설명·번호·따옴표 없이 질문 문장만 그대로 출력하십시오."
    )
    system_msg = "당신은 ISMS 인증 심사 질문을 한국어로 정확하고 자연스럽게 작성하는 보안 컨설턴트입니다."
    return _simple_text_call(user_msg, system_msg)


def polish_text(text: str, kind: str = "question") -> str:
    """기존 문장을 의미는 유지한 채 더 명확하고 자연스럽게 다듬습니다."""
    kind_label = {
        "question": "ISMS 심사 질문",
        "criterion": "ISMS 통과 기준 한 항목",
    }.get(kind, "문장")

    user_msg = (
        f"다음 {kind_label}을(를) 더 명확하고 자연스러운 한국어로 다듬어 주십시오. "
        "의미를 바꾸지 말고, 추가 설명 없이 다듬어진 문장만 그대로 출력하십시오.\n\n"
        f"원문:\n{text}"
    )
    system_msg = "당신은 한국어 보안 문서를 정확하고 간결하게 다듬는 편집자입니다."
    return _simple_text_call(user_msg, system_msg)


# 통과 기준 생성용 도구 스키마
_GENERATE_CRITERIA_TOOL: dict[str, Any] = {
    "toolSpec": {
        "name": "provide_criteria",
        "description": "ISMS 통과 기준을 3개의 짧은 한국어 항목으로 반환합니다.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "각 통과 기준 항목 (정확히 3개의 짧은 문장)",
                    }
                },
                "required": ["criteria"],
            }
        },
    }
}


def generate_pass_criteria(question: str, domain: str = "") -> list[str]:
    """주어진 심사 질문에 대한 ISMS 통과 기준 3가지를 생성합니다."""
    if _bedrock_client is None:
        raise RuntimeError("Bedrock 클라이언트가 초기화되지 않았습니다.")

    response = _bedrock_client.converse(
        modelId=config_service.get_bedrock_model_id(),
        system=[
            {
                "text": (
                    "당신은 ISMS 인증 심사 기준을 작성하는 보안 컨설턴트입니다. "
                    "각 통과 기준은 짧고 명확한 한 줄의 한국어로 작성합니다."
                )
            }
        ],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "text": (
                            f"심사 영역: {domain or '(미지정)'}\n"
                            f"심사 질문: {question}\n\n"
                            "이 질문에 대한 ISMS 통과 기준 **3가지**를 "
                            "provide_criteria 도구로 반환하십시오."
                        )
                    }
                ],
            }
        ],
        toolConfig={
            "tools": [_GENERATE_CRITERIA_TOOL],
            "toolChoice": {"tool": {"name": "provide_criteria"}},
        },
        inferenceConfig={"temperature": 0.5, "maxTokens": 512},
    )

    for block in response.get("output", {}).get("message", {}).get("content", []):
        if "toolUse" in block:
            criteria = block["toolUse"].get("input", {}).get("criteria", [])
            if isinstance(criteria, list):
                return [str(c).strip() for c in criteria if str(c).strip()][:3]
    return []
