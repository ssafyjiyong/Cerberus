"""
Cerberus: The Dark Auditor - Bedrock 연결 테스트 스크립트

실제 AWS 환경과의 연동이 정상 동작하는지 점검합니다.
STS 로 자격 증명을 확인하고, 실제 Bedrock Converse API 를 호출해
케르베로스 심사원의 평가 응답을 받아옵니다.

사용법:
    1. 프로젝트 루트의 .env 에 AWS 자격 증명을 입력합니다.
       (또는 AWS CLI 프로파일 / IAM Role 을 구성합니다.)
    2. backend 디렉토리에서 실행합니다:
           python test_bedrock.py
"""

from __future__ import annotations

import sys

import boto3

from config import AWS_REGION, BEDROCK_MODEL_ID
from services import bedrock_service

# Windows 콘솔(cp949 등)에서도 이모지/한글 출력이 깨지지 않도록 UTF-8 로 강제 설정
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def main() -> int:
    print("=" * 62)
    print(" Cerberus · Bedrock 연결 테스트")
    print("=" * 62)
    print(f" 리전     : {AWS_REGION}")
    print(f" 모델 ID  : {BEDROCK_MODEL_ID}")
    print("-" * 62)

    # 1) Bedrock 클라이언트 초기화 여부
    if bedrock_service._bedrock_client is None:
        print("❌ Bedrock 클라이언트가 초기화되지 않았습니다.")
        print("   .env 의 AWS 자격 증명 또는 리전 설정을 확인하세요.")
        return 1

    # 2) 자격 증명 검증 (STS)
    try:
        identity = boto3.client("sts", region_name=AWS_REGION).get_caller_identity()
        print(f" 인증 계정 : {identity['Account']}")
        print(f" 호출 ARN  : {identity['Arn']}")
    except Exception as exc:
        print(f"❌ AWS 자격 증명 검증 실패: {exc}")
        print("   .env 의 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 를 확인하세요.")
        return 1

    print("-" * 62)
    print(" Level 1(물리적 보안) 샘플 답변으로 평가를 요청합니다...")

    sample_answer = (
        "저희는 모든 직원 PC에 화면 보호기를 설정하고, 5분 이내에 자동으로 "
        "화면이 잠기도록 그룹 정책을 적용했습니다. 잠금 해제는 반드시 "
        "윈도우 로그인 비밀번호를 입력해야만 가능합니다."
    )

    # 3) 실제 Bedrock Converse API 호출
    try:
        result = bedrock_service.evaluate_answer(
            level=1,
            conversation_history=[{"role": "user", "content": sample_answer}],
        )
    except Exception as exc:
        print(f"❌ Bedrock 호출 실패: {exc}")
        print()
        print(" 자주 발생하는 원인:")
        print("  - 모델 액세스 미승인: AWS 콘솔 > Bedrock > Model access 에서")
        print(f"    '{BEDROCK_MODEL_ID}' 모델을 활성화하세요.")
        print("  - IAM 권한 부족: bedrock:InvokeModel 권한을 확인하세요.")
        print("  - 리전 불일치: 해당 리전에서 모델이 제공되는지 확인하세요.")
        return 1

    print("-" * 62)
    print("✅ Bedrock 통신 성공!")
    print(f"   평가 결과   : {result['status']}")
    print(f"   심사 코멘트 : {result['message']}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
