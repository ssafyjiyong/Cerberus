"""
Cerberus: The Dark Auditor — 시드 질문 풀

ISMS-P 21개 중분류 전반을 커버하는 시나리오 기반 시드 질문들.
각 질문은 `auditor_prompt.normalize_question` 으로 정규화됩니다.

구조:
    {
        "id":                 슬러그(예: "2.6.2-nat-gateway"),
        "isms_control_id":    "2.6.2",
        "isms_control_title": "정보시스템 접근",
        "scenario_context":   상황 문단,
        "auditor_question":   심사원의 한 줄 질문,
        "default_rebuttal":   어느 경로에도 안 걸렸을 때 던질 멘트,
        "answer_paths": [
            { half 경로 — trigger/rebuttal/acknowledgment/exemplar_answer },
            { full 경로 — trigger/follow_up/compensating/exemplar_answer },
            ...
        ]
    }
"""
from __future__ import annotations

from typing import Any


# ============================================================================
# Stage 1 — ISMS-P 1.x (관리체계 수립 및 운영)
# ============================================================================
STAGE_1_QUESTIONS: list[dict[str, Any]] = [
    # ── 1.1 관리체계 기반 마련 ──
    {
        "id": "1.1.5-policy-establishment",
        "isms_control_id": "1.1.5",
        "isms_control_title": "정책 수립",
        "scenario_context": (
            "회사의 정보보호 정책서 최종 개정일이 4년 전이고, 최근 클라우드 전환·"
            "재택근무 확산 등 환경 변화가 반영되지 않은 상태로 운영되고 있는 것이 "
            "확인되었습니다."
        ),
        "auditor_question": (
            "환경 변화를 반영한 정보보호 정책 개정은 어떤 절차로 수행하고 계십니까?"
        ),
        "default_rebuttal": (
            "정책 개정 주기·승인 체계·이력 관리에 대한 증적이 보이지 않습니다."
        ),
        "answer_paths": [
            {
                "id": "half-on-demand",
                "tier": "half",
                "description": "필요 시 비정기 개정 — 주기성 부재. 보완 시 절반.",
                "trigger_keywords": ["필요 시", "이슈 발생 시", "비정기", "사안별"],
                "rebuttal": (
                    "비정기 개정만으로는 환경 변화에 적시 대응하기 어렵습니다. "
                    "최소 연 1회 정기 검토 주기와 사후 추적 체계가 필요합니다."
                ),
                "acknowledgment_keywords": ["정기 검토", "주기적", "반영"],
                "exemplar_answer": (
                    "현재는 이슈 발생 시 비정기로 개정하고 있으나, 이를 보완해 "
                    "연 1회 이상 정기 검토 주기를 도입하고 개정 이력을 체계적으로 관리하겠습니다."
                ),
            },
            {
                "id": "full-periodic-with-approval",
                "tier": "full",
                "description": "정기 검토 + 경영진 승인 + 이력 관리 = 만점.",
                "trigger_keywords": ["연 1회", "정기 검토", "정책 위원회", "개정 주기"],
                "follow_up": (
                    "정기 개정 체계는 적절합니다. 개정안의 결재 라인과 "
                    "전사 공유 절차는 어떻게 운영하고 계십니까?"
                ),
                "compensating_keywords": ["경영진 승인", "전사 공유", "이력 관리"],
                "exemplar_answer": (
                    "연 1회 정기 검토와 환경 변화 발생 시 수시 개정 절차를 운영합니다. "
                    "개정안은 정책 위원회 검토 후 경영진 승인을 거쳐 전사에 공유되며, "
                    "버전 이력은 문서관리시스템에 보존하고 있습니다."
                ),
            },
        ],
    },

    # ── 1.2 위험 관리 ── (기존 + 신규)
    {
        "id": "1.2.1-asset-identification",
        "isms_control_id": "1.2.1",
        "isms_control_title": "정보자산 식별",
        "scenario_context": (
            "최근 6개월 사이 AWS 신규 계정 2개가 추가 사용되기 시작했지만, "
            "정보자산 목록(자산대장)에는 해당 계정 내 EC2·RDS·S3 등 주요 리소스가 "
            "단 한 건도 등록되어 있지 않은 것이 확인되었습니다."
        ),
        "auditor_question": (
            "신규 도입된 AWS 계정의 정보자산은 어떤 절차로 식별·등록하고 계십니까?"
        ),
        "default_rebuttal": (
            "신규 자산을 식별·등록·분류하는 정형화된 절차가 운영되지 않는 것으로 보입니다."
        ),
        "answer_paths": [
            {
                "id": "half-manual-tracking",
                "tier": "half",
                "description": "수기/엑셀 자산대장 — 자동화/주기성 부족. 보완 약속 시 절반.",
                "trigger_keywords": ["엑셀", "수기", "수동", "스프레드시트"],
                "rebuttal": (
                    "수기 관리만으로는 신규 자산을 적시에 누락 없이 식별하기 어렵습니다. "
                    "자동 인벤토리 수집과 정기 점검 절차가 필요합니다."
                ),
                "acknowledgment_keywords": ["자동화", "주기적 점검", "보완", "개선"],
                "exemplar_answer": (
                    "현재 엑셀 자산대장으로 관리하고 있으나, AWS Config·Resource Explorer 같은 "
                    "자동 인벤토리 수집 도구로 전환하고 주기적 누락 점검 절차를 도입하겠습니다."
                ),
            },
            {
                "id": "full-automated-inventory",
                "tier": "full",
                "description": "자동 인벤토리 + 분류·소유자 지정 + 주기 점검 = 만점.",
                "trigger_keywords": ["AWS Config", "Resource Explorer", "Inventory", "자동 인벤토리", "태그"],
                "follow_up": (
                    "자동 수집 체계는 적절합니다. 식별된 자산의 중요도 분류와 소유자 지정 "
                    "절차, 그리고 변경 발생 시 갱신은 어떻게 운영되고 있습니까?"
                ),
                "compensating_keywords": ["분류 기준", "소유자 지정", "주기적 점검", "경영진 보고"],
                "exemplar_answer": (
                    "AWS Config와 Resource Explorer를 통해 자동으로 인벤토리를 수집·태그 기반으로 분류하고, "
                    "자산별 소유자를 지정해 분기 단위로 변경 점검을 수행합니다. 결과는 경영진에게 보고됩니다."
                ),
            },
        ],
    },
    {
        "id": "1.2.3-risk-assessment",
        "isms_control_id": "1.2.3",
        "isms_control_title": "위험 평가",
        "scenario_context": (
            "관리체계 도입 이후 3년이 지났지만 위험평가 결과 보고서가 1회만 존재하고, "
            "최근 신규 서비스·시스템 변경에 대한 위험평가가 수행된 흔적이 없습니다."
        ),
        "auditor_question": (
            "위험평가는 어떤 주기와 트리거로 수행하고 계십니까?"
        ),
        "default_rebuttal": (
            "위험평가의 수행 주기·범위·결과 활용에 대한 명확한 증적이 부족합니다."
        ),
        "answer_paths": [
            {
                "id": "half-annual-only",
                "tier": "half",
                "description": "연 1회만 — 변경 트리거 부재. 보완 시 절반.",
                "trigger_keywords": ["연 1회", "매년", "정기 평가"],
                "rebuttal": (
                    "연 1회 정기 평가만으로는 신규 서비스 도입이나 시스템 변경 시점의 "
                    "위험을 적시에 파악하기 어렵습니다. 변경 발생 시점에도 평가가 트리거되어야 합니다."
                ),
                "acknowledgment_keywords": ["변경 시", "신규 도입 시", "트리거", "보완"],
                "exemplar_answer": (
                    "현재는 연 1회 정기 위험평가만 수행 중이나, 신규 서비스 도입과 주요 시스템 변경 "
                    "발생 시점에도 추가 평가가 트리거되도록 절차를 보완하겠습니다."
                ),
            },
            {
                "id": "full-event-and-periodic",
                "tier": "full",
                "description": "정기 + 이벤트 기반 + 경영진 보고 = 만점.",
                "trigger_keywords": ["변경 시", "신규 서비스", "정기 평가", "위험 식별"],
                "follow_up": (
                    "두 축의 위험평가 체계는 적절합니다. 식별된 위험에 대한 대응 우선순위와 "
                    "후속 조치 추적은 어떻게 하고 계십니까?"
                ),
                "compensating_keywords": ["우선순위", "후속 조치", "경영진 보고", "DoA"],
                "exemplar_answer": (
                    "연 1회 정기 위험평가와 신규 서비스 도입·중대 변경 시점의 이벤트 기반 평가를 "
                    "병행 운영합니다. 식별된 위험은 영향도·발생가능성 기반 우선순위 매트릭스로 분류하고, "
                    "DoA(Statement of Applicability) 갱신과 함께 경영진에게 보고합니다."
                ),
            },
        ],
    },

    # ── 1.3 관리체계 운영 ──
    {
        "id": "1.3.3-operation-status",
        "isms_control_id": "1.3.3",
        "isms_control_title": "운영현황 관리",
        "scenario_context": (
            "보호대책 이행 현황표가 2년 전 한 시점에서 멈춰 있고, "
            "최근 도입된 통제(예: EDR, CSPM 등)에 대한 운영 현황이 반영되어 있지 않습니다."
        ),
        "auditor_question": (
            "보호대책 운영 현황은 어떤 주기로 모니터링·갱신하고 계십니까?"
        ),
        "default_rebuttal": (
            "보호대책 운영 현황을 지속적으로 관리·갱신하는 절차의 증적이 부족합니다."
        ),
        "answer_paths": [
            {
                "id": "half-ad-hoc-update",
                "tier": "half",
                "description": "필요 시에만 — 정기성 부재. 보완 시 절반.",
                "trigger_keywords": ["필요 시", "비정기", "감사 직전"],
                "rebuttal": (
                    "감사 직전에만 갱신하는 방식은 평시 보호대책의 실제 운영 상태를 보장하지 못합니다. "
                    "정기 모니터링 체계가 필요합니다."
                ),
                "acknowledgment_keywords": ["정기 모니터링", "주기적", "보완"],
                "exemplar_answer": (
                    "현재 감사 시점에만 갱신하고 있으나, 분기 단위 정기 모니터링과 "
                    "이행 현황 대시보드를 도입해 평시에도 추적 가능하도록 보완하겠습니다."
                ),
            },
            {
                "id": "full-dashboard-driven",
                "tier": "full",
                "description": "대시보드 + 분기 점검 + 경영진 보고 = 만점.",
                "trigger_keywords": ["대시보드", "분기 점검", "이행 현황", "지표"],
                "follow_up": (
                    "정기 모니터링 체계는 적절합니다. 이행 미흡 항목에 대한 후속 조치와 "
                    "재발 방지 절차는 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["후속 조치", "재발 방지", "경영진 보고"],
                "exemplar_answer": (
                    "보호대책 이행 현황을 대시보드로 상시 모니터링하고 분기마다 정식 점검을 수행합니다. "
                    "미흡 항목은 책임자 지정 후 후속 조치 기한을 설정하며, 경영진에게 결과를 보고합니다."
                ),
            },
        ],
    },

    # ── 1.4 관리체계 점검 및 개선 ── (기존)
    {
        "id": "1.4.1-legal-review",
        "isms_control_id": "1.4.1",
        "isms_control_title": "법적 요구사항 준수 검토",
        "scenario_context": (
            "작년에 개인정보보호법 시행령이 개정되었으나, 회사 내부의 "
            "개인정보 처리방침과 관련 보안 정책 문서가 1년 이상 개정 이력 없이 "
            "그대로 운영되고 있는 것이 확인되었습니다."
        ),
        "auditor_question": (
            "개정된 법령·규제 사항에 대한 준수 검토는 어떤 절차로 수행하고 계십니까?"
        ),
        "default_rebuttal": (
            "법령 변경에 대한 체계적 모니터링·영향평가·반영 절차의 증적이 보이지 않습니다."
        ),
        "answer_paths": [
            {
                "id": "half-legal-monitoring",
                "tier": "half",
                "description": "법령 모니터링 알림 서비스에 의존 — 영향평가까지는 부재.",
                "trigger_keywords": ["법령 모니터링", "법제처 알리미", "뉴스레터", "알림 서비스"],
                "rebuttal": (
                    "알림 수신만으로는 부족합니다. 변경 사항이 우리 조직의 정책·시스템에 "
                    "어떤 영향을 주는지 영향평가 절차가 함께 운영되어야 합니다."
                ),
                "acknowledgment_keywords": ["반영", "영향평가 절차 마련", "보완", "검토하겠습니다"],
                "exemplar_answer": (
                    "현재는 법제처 알리미 등 법령 모니터링 서비스로 변경을 인지하고 있으나, "
                    "이를 보완해 변경 사항이 정책·시스템에 미치는 영향평가 절차를 마련하겠습니다."
                ),
            },
            {
                "id": "full-periodic-review",
                "tier": "full",
                "description": "주기적 법규 검토 + 영향평가 + 외부 자문/내부 승인까지 갖춘 만점 경로.",
                "trigger_keywords": ["주기적", "분기", "반기", "정기 검토", "영향평가", "법무 자문"],
                "follow_up": (
                    "정기 검토 체계는 인정합니다. 그렇다면 검토 결과가 정책 개정으로 "
                    "이어지는 의사결정 절차와 그 증적은 어떻게 관리하고 계십니까?"
                ),
                "compensating_keywords": ["위험평가", "경영진 승인", "정책 개정", "이력 관리"],
                "exemplar_answer": (
                    "분기마다 법무팀 자문과 함께 정기 법규 검토를 수행하고 변경 사항에 대한 영향평가를 진행합니다. "
                    "검토 결과는 위험평가를 거쳐 경영진 승인 후 정책 개정에 반영되며, 이력을 보존합니다."
                ),
            },
        ],
    },
]


# ============================================================================
# Stage 2 — ISMS-P 2.x (보호대책 요구사항)
# ============================================================================
STAGE_2_QUESTIONS: list[dict[str, Any]] = [
    # ── 2.1 정책·조직·자산 관리 ──
    {
        "id": "2.1.3-asset-classification",
        "isms_control_id": "2.1.3",
        "isms_control_title": "정보자산 관리",
        "scenario_context": (
            "자산대장에 모든 자산이 '중요' 한 가지 등급으로만 분류되어 있어, "
            "보호 수준 차등화의 실효성이 떨어지는 것이 확인되었습니다."
        ),
        "auditor_question": "정보자산의 중요도 분류는 어떤 기준으로 수행하고 계십니까?",
        "default_rebuttal": "자산 분류 기준의 다단계 운영과 차등 통제 적용 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-uniform-classification",
                "tier": "half",
                "description": "단일 등급 — 차등 통제 부재. 보완 시 절반.",
                "trigger_keywords": ["단일 등급", "일괄", "전사 동일"],
                "rebuttal": (
                    "전사 일괄 분류로는 자산별 위험에 맞춘 보호 강도를 적용할 수 없습니다. "
                    "최소 3단계 이상의 차등 기준이 필요합니다."
                ),
                "acknowledgment_keywords": ["차등", "다단계", "보완"],
                "exemplar_answer": (
                    "현재는 단일 등급으로 운영 중이나, 기밀성·무결성·가용성을 고려한 3단계 차등 "
                    "분류 기준으로 보완하고 등급별 통제 매트릭스를 적용하겠습니다."
                ),
            },
            {
                "id": "full-cia-based",
                "tier": "full",
                "description": "C/I/A 기반 다단계 분류 + 등급별 통제 = 만점.",
                "trigger_keywords": ["기밀성", "무결성", "가용성", "CIA", "다단계", "등급별 통제"],
                "follow_up": (
                    "분류 기준은 적절합니다. 등급별로 적용되는 구체적 통제(접근·암호화 등)는 "
                    "어떻게 차등화하고 있습니까?"
                ),
                "compensating_keywords": ["등급별 매트릭스", "접근통제 차등", "주기적 재분류"],
                "exemplar_answer": (
                    "기밀성·무결성·가용성(CIA) 평가에 따라 자산을 상·중·하 3단계로 분류하고, "
                    "등급별 접근통제·암호화·백업 요구수준이 정의된 통제 매트릭스를 적용합니다. "
                    "분류 결과는 연 1회 재평가합니다."
                ),
            },
        ],
    },

    # ── 2.2 인적 보안 ──
    {
        "id": "2.2.4-awareness-training",
        "isms_control_id": "2.2.4",
        "isms_control_title": "인식제고 및 교육훈련",
        "scenario_context": (
            "정보보호 교육 수료율이 60% 수준이고, 미수료자에 대한 후속 조치 기록이 "
            "확인되지 않습니다. 또한 직무별 차별화된 교육 과정이 존재하지 않습니다."
        ),
        "auditor_question": "정보보호 교육은 어떤 대상·주기·방식으로 운영하고 계십니까?",
        "default_rebuttal": "교육 대상·주기·미이수자 관리에 대한 체계적 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-annual-uniform",
                "tier": "half",
                "description": "연 1회 전사 동일 교육 — 직무 차등·미이수자 추적 부재.",
                "trigger_keywords": ["연 1회", "전사 교육", "온라인 교육"],
                "rebuttal": (
                    "전사 동일 교육만으로는 직무별 위험에 맞춘 인식 강화가 어렵습니다. "
                    "또한 미이수자에 대한 추적·재교육 체계가 필요합니다."
                ),
                "acknowledgment_keywords": ["직무별 차등", "미이수자 추적", "보완"],
                "exemplar_answer": (
                    "현재 연 1회 전사 온라인 교육만 운영 중이나, 개인정보취급자·개발자·일반 "
                    "직무 등으로 차등화하고 미이수자 추적·재교육 체계를 도입해 보완하겠습니다."
                ),
            },
            {
                "id": "full-tiered-training",
                "tier": "full",
                "description": "직무별 차등 + 신규 입사자 의무 + 미이수 후속조치 = 만점.",
                "trigger_keywords": ["직무별", "신규 입사자", "개인정보취급자", "미이수자"],
                "follow_up": (
                    "교육 체계는 인정합니다. 교육 효과 측정과 인식 수준의 변화 추적은 "
                    "어떻게 하고 계십니까?"
                ),
                "compensating_keywords": ["효과 측정", "평가", "모의 훈련", "경영진 보고"],
                "exemplar_answer": (
                    "신규 입사자 의무 교육, 개인정보취급자 특별 교육, 전 직원 연 1회 정기 교육의 "
                    "3축으로 운영하며, 미이수자는 재교육 통보 후 인사 평가에 반영합니다. "
                    "모의 피싱 훈련으로 효과를 측정해 경영진에 보고합니다."
                ),
            },
        ],
    },

    # ── 2.3 외부자 보안 ──
    {
        "id": "2.3.3-external-party",
        "isms_control_id": "2.3.3",
        "isms_control_title": "외부자 보안 이행 관리",
        "scenario_context": (
            "개인정보 처리 업무를 위탁한 협력사 3곳에 대해 최근 1년간 보안 점검이 "
            "수행된 기록이 없습니다. 계약서에는 보안 요구사항이 명시되어 있으나 이행 점검은 부재합니다."
        ),
        "auditor_question": "위탁사의 보안 요구사항 이행 여부는 어떻게 점검하고 계십니까?",
        "default_rebuttal": "위탁사 보안 이행에 대한 주기적 점검과 미흡 사항 후속 조치 증적이 보이지 않습니다.",
        "answer_paths": [
            {
                "id": "half-contract-only",
                "tier": "half",
                "description": "계약서 명시만 — 실 이행 점검 부재. 보완 시 절반.",
                "trigger_keywords": ["계약서", "보안 약정", "서약서"],
                "rebuttal": (
                    "계약상 명시만으로는 실제 이행 여부를 보장할 수 없습니다. "
                    "정기 점검과 미흡 사항 추적이 함께 운영되어야 합니다."
                ),
                "acknowledgment_keywords": ["정기 점검", "현장 점검", "보완"],
                "exemplar_answer": (
                    "현재는 계약 시점의 보안 약정 확인에 머물러 있으나, 연 1회 이상 위탁사 "
                    "보안 점검(체크리스트·현장 확인)을 도입하고 미흡 사항 후속 조치를 추적하겠습니다."
                ),
            },
            {
                "id": "full-audit-and-monitor",
                "tier": "full",
                "description": "정기 점검 + 위반 시 페널티 + 모니터링 체계 = 만점.",
                "trigger_keywords": ["정기 점검", "체크리스트", "현장 점검", "위탁사 평가"],
                "follow_up": (
                    "점검 체계는 적절합니다. 점검 결과 미흡한 위탁사에 대한 "
                    "조치 절차(개선 요구·계약 해지 등)는 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["개선 요구", "계약 조치", "재점검", "결과 보고"],
                "exemplar_answer": (
                    "위탁 계약서에 보안 요구사항을 명시하고, 연 1회 이상 체크리스트 기반 정기 점검과 "
                    "필요 시 현장 점검을 수행합니다. 미흡 사항은 개선 요구서를 발부해 재점검하며, "
                    "중대 위반 시 계약 조치까지 가능한 절차를 운영합니다."
                ),
            },
        ],
    },

    # ── 2.4 물리 보안 ──
    {
        "id": "2.4.2-access-control",
        "isms_control_id": "2.4.2",
        "isms_control_title": "출입통제",
        "scenario_context": (
            "전산실 출입 카드 발급 대장에 18명이 등록되어 있으나, 실제로는 그중 5명이 "
            "이미 퇴사하거나 부서를 이동한 것이 확인되었습니다."
        ),
        "auditor_question": "전산실 출입 권한은 어떤 절차로 부여·회수하고 계십니까?",
        "default_rebuttal": "출입 권한의 발급·회수·정기 검토에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-issue-only",
                "tier": "half",
                "description": "발급만 통제 — 회수 절차 부재. 보완 시 절반.",
                "trigger_keywords": ["승인", "발급 절차", "신청서"],
                "rebuttal": (
                    "발급 시점의 승인만으로는 부족합니다. 퇴직·인사이동 발생 시 회수 "
                    "절차와 정기 권한 재검토가 필요합니다."
                ),
                "acknowledgment_keywords": ["회수", "정기 검토", "보완"],
                "exemplar_answer": (
                    "현재 발급 시점의 승인만 통제 중이나, 퇴직·인사이동 발생 시 즉시 회수 절차와 "
                    "분기 단위 권한 재검토를 도입해 보완하겠습니다."
                ),
            },
            {
                "id": "full-lifecycle-control",
                "tier": "full",
                "description": "발급·회수·재검토 전 라이프사이클 + 로그 모니터링 = 만점.",
                "trigger_keywords": ["인사이동", "퇴직 시 회수", "권한 재검토", "출입 로그"],
                "follow_up": (
                    "라이프사이클 관리는 인정합니다. 출입 로그의 이상행위 검출과 "
                    "주기적 리뷰는 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["이상행위 분석", "정기 리뷰", "경영진 보고"],
                "exemplar_answer": (
                    "출입 권한은 부서장 승인 후 발급하고, 퇴직·인사이동 발생 시 HR 시스템과 연동해 "
                    "자동 회수합니다. 분기마다 권한 재검토를 수행하고, 출입 로그는 월 단위 이상행위 "
                    "분석 후 보안팀이 리뷰해 경영진에 보고합니다."
                ),
            },
        ],
    },

    # ── 2.5 인증 및 권한 관리 ──
    {
        "id": "2.5.4-password-policy",
        "isms_control_id": "2.5.4",
        "isms_control_title": "비밀번호 관리",
        "scenario_context": (
            "서버 관리자 계정의 비밀번호 정책 점검 중, 일부 서버에서 6자리 단순 "
            "비밀번호가 1년 이상 변경 없이 사용 중인 것이 확인되었습니다."
        ),
        "auditor_question": "관리자 계정 비밀번호 정책은 어떻게 적용되고 있습니까?",
        "default_rebuttal": "비밀번호 복잡도·변경 주기·이력 관리에 대한 일관된 적용 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-policy-but-unenforced",
                "tier": "half",
                "description": "정책은 있으나 강제 미적용. 보완 시 절반.",
                "trigger_keywords": ["정책 문서", "가이드", "지침"],
                "rebuttal": (
                    "문서상 정책만으로는 실제 시스템에서 강제되지 않으면 통제로 인정되지 않습니다. "
                    "기술적 강제 적용이 필요합니다."
                ),
                "acknowledgment_keywords": ["강제 적용", "시스템 적용", "보완"],
                "exemplar_answer": (
                    "현재 비밀번호 정책 문서는 존재하나 일부 서버에 기술적 강제가 적용되지 않은 상태입니다. "
                    "PAM/AD 등으로 모든 서버에 정책을 강제 적용하도록 보완하겠습니다."
                ),
            },
            {
                "id": "full-enforced-with-mfa",
                "tier": "full",
                "description": "기술적 강제 + MFA + 권한 분리 = 만점.",
                "trigger_keywords": ["MFA", "다중요소", "PAM", "AD 정책", "기술적 강제"],
                "follow_up": (
                    "강제 적용 체계는 적절합니다. 비밀번호 이력 관리와 유출 사고 대응 "
                    "절차는 어떻게 운영하고 계십니까?"
                ),
                "compensating_keywords": ["이력 관리", "유출 대응", "정기 변경"],
                "exemplar_answer": (
                    "관리자 계정은 PAM과 AD 그룹 정책으로 12자 이상 복잡도와 90일 변경 주기를 "
                    "기술적으로 강제하며, MFA를 의무 적용합니다. 이력은 최근 5회 재사용을 차단하고, "
                    "유출 의심 시 즉시 강제 변경 절차를 운영합니다."
                ),
            },
        ],
    },

    # ── 2.6 접근통제 ── (기존 + 신규 1)
    {
        "id": "2.6.2-nat-gateway",
        "isms_control_id": "2.6.2",
        "isms_control_title": "정보시스템 접근",
        "scenario_context": (
            "인증심사원이 VPC 구성도를 검토하던 중, Private 서브넷에서 외부로 "
            "나가는 NAT 게이트웨이가 활성화된 것을 확인했습니다. "
            "심사원은 불필요한 외부 통신 경로가 있는 것은 아닌지 문제 삼고 있습니다."
        ),
        "auditor_question": "NAT 게이트웨이는 어떤 용도로 사용 중인가요?",
        "default_rebuttal": (
            "그 정도의 답변으로는 NAT 게이트웨이의 필요성을 입증하기 어렵습니다. "
            "구체적인 사용 목적·통제·보완대책의 근거가 필요합니다."
        ),
        "answer_paths": [
            {
                "id": "half-patch",
                "tier": "half",
                "description": "라이브러리/패키지 패치 용도 — 대안(S3+PrivateLink) 수용 시 절반.",
                "trigger_keywords": ["패치", "패키지", "라이브러리 업데이트", "yum", "apt"],
                "rebuttal": (
                    "패치는 S3 버킷에 무결성 검증된 버전을 옮긴 뒤 PrivateLink 로 "
                    "전달하는 구조로 대체 가능합니다. 이렇게 개선하시겠습니까?"
                ),
                "acknowledgment_keywords": ["반영", "검토하겠습니다", "개선", "조치"],
                "exemplar_answer": (
                    "패키지 패치 용도로 사용 중입니다. 무결성 검증된 버전을 S3에 보관하고 "
                    "PrivateLink로 전달하는 구조로 개선하겠습니다."
                ),
            },
            {
                "id": "full-external-api",
                "tier": "full",
                "description": "외부 API 와의 실시간 동기화 + 위험평가/경영진 승인 보완통제 → 만점.",
                "trigger_keywords": ["외부 API", "실시간", "동기화", "연동"],
                "follow_up": (
                    "외부 연동 필요성은 이해했습니다. 그렇다면 이에 대한 "
                    "보완통제는 어떻게 갖추셨습니까?"
                ),
                "compensating_keywords": ["위험평가", "경영진 승인"],
                "exemplar_answer": (
                    "외부 결제 API와 실시간 동기화가 필요해 사용 중입니다. "
                    "이 경로는 위험평가 절차를 거쳐 식별된 위험을 문서화하고, 경영진 승인 후 "
                    "보완통제를 적용해 운영하고 있습니다."
                ),
            },
        ],
    },
    {
        "id": "2.6.6-remote-access",
        "isms_control_id": "2.6.6",
        "isms_control_title": "원격접근 통제",
        "scenario_context": (
            "재택근무자 30명에게 VPN 계정이 발급되어 있으나, VPN 연결 시 ID/PW 외 "
            "추가 인증 요소가 적용되지 않고, 접속 IP 제한도 없는 것이 확인되었습니다."
        ),
        "auditor_question": "원격 접근에 대한 통제는 어떻게 운영하고 계십니까?",
        "default_rebuttal": "원격 접근의 인증 강도·접근 통제·로그 모니터링에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-vpn-only",
                "tier": "half",
                "description": "VPN만 — 추가 인증·IP 제한 부재. 보완 시 절반.",
                "trigger_keywords": ["VPN", "원격 접속"],
                "rebuttal": (
                    "VPN 단일 통제로는 부족합니다. 최소한 MFA와 접속 IP 제한, "
                    "관리자 권한 분리 통제가 함께 운영되어야 합니다."
                ),
                "acknowledgment_keywords": ["MFA", "다중요소", "보완", "IP 제한"],
                "exemplar_answer": (
                    "현재 VPN 단일 인증만 적용 중이나, MFA와 접속 IP 화이트리스트를 "
                    "추가 적용해 보완하겠습니다."
                ),
            },
            {
                "id": "full-zero-trust",
                "tier": "full",
                "description": "MFA + Zero Trust + 세션 모니터링 = 만점.",
                "trigger_keywords": ["MFA", "다중요소 인증", "Zero Trust", "ZTNA", "세션 모니터링"],
                "follow_up": (
                    "통제는 적절합니다. 원격 세션의 활동 모니터링과 이상행위 "
                    "탐지 체계는 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["로그 모니터링", "이상행위", "세션 녹화"],
                "exemplar_answer": (
                    "원격 접근은 MFA 강제와 ZTNA 기반 접근통제로 적용하며, 관리자 세션은 별도로 "
                    "녹화·모니터링합니다. 이상 접속 패턴은 SIEM에서 탐지해 보안팀이 즉시 검토합니다."
                ),
            },
        ],
    },

    # ── 2.7 암호화 ──
    {
        "id": "2.7.1-encryption-policy",
        "isms_control_id": "2.7.1",
        "isms_control_title": "암호정책 적용",
        "scenario_context": (
            "개인정보를 처리하는 RDS 인스턴스 3개 중 1개에서 저장 시 암호화(at-rest)가 "
            "적용되지 않은 채 운영되고 있는 것이 확인되었습니다."
        ),
        "auditor_question": "개인정보 저장 시 암호화는 어떤 기준으로 적용하고 계십니까?",
        "default_rebuttal": "암호화 적용 범위·알고리즘·키 관리에 대한 일관된 기준 적용 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-partial-encryption",
                "tier": "half",
                "description": "일부 시스템만 — 전체 적용 부재. 보완 시 절반.",
                "trigger_keywords": ["일부 적용", "신규 시스템만", "암호화 중"],
                "rebuttal": (
                    "법령상 개인정보 저장 시 암호화는 모든 대상에 일관되게 적용되어야 합니다. "
                    "예외 시스템에 대한 보완 계획이 필요합니다."
                ),
                "acknowledgment_keywords": ["전체 적용", "보완 계획", "마이그레이션"],
                "exemplar_answer": (
                    "신규 시스템에는 저장 시 암호화를 적용하고 있으나 일부 레거시 RDS에 미적용된 "
                    "상태입니다. 단기 마이그레이션 계획을 수립해 전체 적용으로 보완하겠습니다."
                ),
            },
            {
                "id": "full-kms-managed",
                "tier": "full",
                "description": "전체 KMS 적용 + 키 분리·교체 정책 = 만점.",
                "trigger_keywords": ["KMS", "AES-256", "전체 적용", "키 관리"],
                "follow_up": (
                    "암호화 적용은 적절합니다. 키 생애주기 관리(생성·교체·폐기)는 "
                    "어떤 정책으로 운영하고 계십니까?"
                ),
                "compensating_keywords": ["키 교체", "키 분리", "권한 분리", "키 폐기"],
                "exemplar_answer": (
                    "개인정보 처리 시스템은 모두 KMS 기반 AES-256으로 저장 시 암호화를 적용합니다. "
                    "키는 서비스별로 분리해 발급하고 연 1회 교체 정책을 운영하며, "
                    "키 사용·관리 권한은 별도 인원으로 분리되어 있습니다."
                ),
            },
        ],
    },

    # ── 2.8 도입·개발 보안 ──
    {
        "id": "2.8.3-test-prod-separation",
        "isms_control_id": "2.8.3",
        "isms_control_title": "시험과 운영환경 분리",
        "scenario_context": (
            "QA 환경에서 운영 DB의 실제 개인정보 데이터를 복사해 테스트에 사용한 "
            "기록이 확인되었으며, 환경 간 네트워크 분리도 부분적입니다."
        ),
        "auditor_question": "시험 환경과 운영 환경의 분리는 어떻게 적용하고 계십니까?",
        "default_rebuttal": "환경 분리·테스트 데이터 보안·접근 통제 차등에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-network-only",
                "tier": "half",
                "description": "네트워크 분리만 — 데이터·계정 분리 부재. 보완 시 절반.",
                "trigger_keywords": ["네트워크 분리", "VPC 분리"],
                "rebuttal": (
                    "네트워크 분리만으로는 충분하지 않습니다. 시험 데이터 익명화·"
                    "가명화와 계정 분리가 함께 적용되어야 합니다."
                ),
                "acknowledgment_keywords": ["익명화", "가명화", "보완", "계정 분리"],
                "exemplar_answer": (
                    "현재 네트워크는 분리되어 있으나 운영 데이터가 그대로 QA에서 사용 중입니다. "
                    "운영 데이터는 가명화·익명화 후에만 시험 환경에 반입하도록 절차를 보완하겠습니다."
                ),
            },
            {
                "id": "full-multi-layer-separation",
                "tier": "full",
                "description": "네트워크 + 계정 + 데이터 가명화 = 만점.",
                "trigger_keywords": ["가명화", "익명화", "환경 분리", "계정 분리", "테스트 데이터"],
                "follow_up": (
                    "분리 체계는 적절합니다. 시험 데이터의 폐기와 환경 간 데이터 이동 통제는 "
                    "어떻게 운영합니까?"
                ),
                "compensating_keywords": ["데이터 폐기", "이관 통제", "변경 관리"],
                "exemplar_answer": (
                    "운영·스테이징·QA를 별도 계정·VPC로 분리하고, 운영 데이터는 가명화·익명화 "
                    "도구를 거쳐야만 시험 환경에 반입됩니다. 시험 종료 후 데이터는 즉시 폐기하며, "
                    "환경 간 이관은 변경관리 절차에 따라 통제됩니다."
                ),
            },
        ],
    },

    # ── 2.9 운영관리 ──
    {
        "id": "2.9.4-log-management",
        "isms_control_id": "2.9.4",
        "isms_control_title": "로그 및 접속기록 관리",
        "scenario_context": (
            "개인정보 처리 시스템의 접속 기록이 90일만 보관되고 있고, 별도 백업이나 "
            "변조 방지 조치가 적용되지 않은 것이 확인되었습니다."
        ),
        "auditor_question": "개인정보 처리 시스템의 접속 기록은 어떻게 보존·관리하고 계십니까?",
        "default_rebuttal": "법정 보존 기간·변조 방지·접근 통제 관점의 로그 관리 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-retention-only",
                "tier": "half",
                "description": "기간만 보장 — 변조 방지 부재. 보완 시 절반.",
                "trigger_keywords": ["1년 보관", "2년 보관", "보존 기간"],
                "rebuttal": (
                    "보존 기간만으로는 부족합니다. 무결성 보장(변조 방지)과 접근 통제가 "
                    "함께 적용되어야 법적 증거력이 확보됩니다."
                ),
                "acknowledgment_keywords": ["무결성", "변조 방지", "보완"],
                "exemplar_answer": (
                    "현재 보존 기간만 충족하고 있어, WORM 스토리지나 해시 체인 등 변조 방지 "
                    "조치와 별도 접근 통제를 추가 적용해 보완하겠습니다."
                ),
            },
            {
                "id": "full-immutable-monitored",
                "tier": "full",
                "description": "보존 + 무결성 + 모니터링 + 권한 분리 = 만점.",
                "trigger_keywords": ["WORM", "S3 Object Lock", "해시", "변조 방지", "SIEM"],
                "follow_up": (
                    "로그 보호 체계는 적절합니다. 접속 기록에 대한 정기 점검(이상행위 분석)은 "
                    "어떤 주기로 수행하고 계십니까?"
                ),
                "compensating_keywords": ["정기 점검", "이상행위 분석", "월 단위", "분기 보고"],
                "exemplar_answer": (
                    "개인정보 접속 기록은 법정 기준에 따라 1년 이상 보존하며, S3 Object Lock으로 "
                    "변조 방지를 적용하고 SIEM에서 집계합니다. 로그 접근은 별도 권한자만 가능하며, "
                    "월 단위로 이상행위를 분석해 분기 단위로 경영진에 보고합니다."
                ),
            },
        ],
    },

    # ── 2.10 시스템·서비스 보안관리 ── (기존 + 신규)
    {
        "id": "2.10.1-sg-outbound",
        "isms_control_id": "2.10.1",
        "isms_control_title": "보안시스템 운영",
        "scenario_context": (
            "EC2 인스턴스에 적용된 Security Group 의 아웃바운드 정책이 "
            "0.0.0.0/0(ANY) 으로 전면 허용된 것이 확인되었습니다. "
            "심사원은 보안시스템에 설정된 정책의 타당성 검토가 주기적으로 "
            "이뤄지지 않고 있다고 지적하고 있습니다."
        ),
        "auditor_question": "Security Group 아웃바운드 통제가 전혀 되지 않고 있네요?",
        "default_rebuttal": (
            "아웃바운드 전면 허용은 보안시스템 운영 기준에서 명백한 결함입니다. "
            "통제 방식이나 보완대책의 근거가 부족합니다."
        ),
        "answer_paths": [
            {
                "id": "half-central-inspection",
                "tier": "half",
                "description": "중앙 Inspection VPC(NFW/UTM)로 검사 위임 — SG 목적지 강제 필요.",
                "trigger_keywords": ["Inspection VPC", "NFW", "UTM", "중앙 방화벽", "Network Firewall"],
                "rebuttal": (
                    "중앙 검사 구조는 좋습니다만, Security Group 아웃바운드 목적지가 "
                    "Inspection VPC 의 NFW/UTM 프로파일로 강제되어야 통제로 인정됩니다. "
                    "반영해 주시겠습니까?"
                ),
                "acknowledgment_keywords": ["반영", "조치", "개선", "검토하겠습니다"],
                "exemplar_answer": (
                    "모든 아웃바운드 트래픽은 중앙 Inspection VPC의 Network Firewall에서 검사하도록 "
                    "구성되어 있습니다. Security Group 목적지를 NFW 프로파일로 강제 라우팅되도록 보완하겠습니다."
                ),
            },
            {
                "id": "full-long-term-plan",
                "tier": "full",
                "description": "장기조치계획 + 위험평가/모니터링/경영진 승인 = 만점.",
                "trigger_keywords": ["장기조치계획", "내부 감사", "조치 계획", "단계적 개선"],
                "follow_up": (
                    "장기 조치 계획으로 분류된 것은 인정합니다. 그 사이의 "
                    "보완통제는 어떻게 운영되고 있습니까?"
                ),
                "compensating_keywords": ["위험평가", "모니터링", "경영진 승인"],
                "exemplar_answer": (
                    "내부 감사에서 지적된 이후 시스템 중요도가 높아 장기 조치 계획으로 분류된 항목입니다. "
                    "조치 완료 전까지는 위험평가 절차를 거쳤고, 실시간 이상행위 모니터링 체계를 "
                    "운영하며 경영진 승인을 취득했습니다."
                ),
            },
        ],
    },
    {
        "id": "2.10.8-patch-management",
        "isms_control_id": "2.10.8",
        "isms_control_title": "패치 관리",
        "scenario_context": (
            "보안 패치 적용 현황을 조사한 결과, 일부 운영 서버에 6개월 이상 미적용된 "
            "CVE 점수 9.0+ 의 Critical 패치가 다수 확인되었습니다."
        ),
        "auditor_question": "보안 패치는 어떤 주기와 우선순위 기준으로 적용하고 계십니까?",
        "default_rebuttal": "패치 적용 주기·우선순위 기준·예외 통제에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-quarterly-uniform",
                "tier": "half",
                "description": "전체 분기 일괄 — 심각도 차등 부재. 보완 시 절반.",
                "trigger_keywords": ["분기", "정기 패치", "일괄 적용"],
                "rebuttal": (
                    "심각도 무관 분기 일괄 적용으로는 Critical 패치 적시 대응이 어렵습니다. "
                    "CVSS 기반 차등 SLA가 필요합니다."
                ),
                "acknowledgment_keywords": ["CVSS", "심각도 차등", "보완"],
                "exemplar_answer": (
                    "현재 분기 단위 일괄 패치 중심이나, CVSS 9.0+ Critical은 72시간 이내, "
                    "High는 2주 이내 등 심각도별 차등 SLA를 도입해 보완하겠습니다."
                ),
            },
            {
                "id": "full-risk-based-sla",
                "tier": "full",
                "description": "CVSS 기반 차등 SLA + 예외 승인 절차 = 만점.",
                "trigger_keywords": ["CVSS", "심각도", "차등 SLA", "긴급 패치"],
                "follow_up": (
                    "패치 정책은 적절합니다. 적용이 어려운 시스템에 대한 예외 통제와 "
                    "보완 대책은 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["예외 승인", "보완 통제", "위험평가"],
                "exemplar_answer": (
                    "CVSS 9.0 이상 Critical은 72시간, High는 14일, Medium은 분기 정기 패치로 "
                    "차등 SLA를 운영합니다. 적용이 어려운 시스템은 위험평가 후 예외 승인 절차를 "
                    "거치고 IPS·EDR 등 보완 통제를 적용합니다."
                ),
            },
        ],
    },

    # ── 2.11 사고 예방 및 대응 ──
    {
        "id": "2.11.2-vulnerability-scan",
        "isms_control_id": "2.11.2",
        "isms_control_title": "취약점 점검 및 조치",
        "scenario_context": (
            "외부 공인 취약점 점검을 연 1회 수행하고 있으나, 점검 결과 발견된 High 등급 "
            "취약점 12건 중 5건이 6개월째 미조치 상태로 남아있는 것이 확인되었습니다."
        ),
        "auditor_question": "취약점 점검 결과의 조치는 어떤 절차로 추적하고 계십니까?",
        "default_rebuttal": "취약점 조치 추적·완료 검증·재점검 절차에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-scan-only",
                "tier": "half",
                "description": "점검만 수행 — 추적 절차 부재. 보완 시 절반.",
                "trigger_keywords": ["외부 점검", "연 1회", "취약점 진단"],
                "rebuttal": (
                    "점검 수행만으로는 통제가 완성되지 않습니다. 발견 항목의 조치 기한·"
                    "담당자 지정과 완료 검증 절차가 필요합니다."
                ),
                "acknowledgment_keywords": ["조치 추적", "기한 관리", "보완"],
                "exemplar_answer": (
                    "현재 연 1회 점검만 수행 중이나, 발견 취약점에 대해 등급별 조치 기한을 "
                    "지정하고 완료 검증과 재점검을 의무화하는 추적 절차를 도입하겠습니다."
                ),
            },
            {
                "id": "full-managed-lifecycle",
                "tier": "full",
                "description": "점검 + 등급별 SLA + 재검증 + 경영진 보고 = 만점.",
                "trigger_keywords": ["조치 기한", "재점검", "추적 시스템", "Jira", "티켓"],
                "follow_up": (
                    "라이프사이클 관리는 적절합니다. 정기 점검 외에 자동 스캔이나 "
                    "버그바운티 같은 보완 체계는 운영하고 계십니까?"
                ),
                "compensating_keywords": ["자동 스캔", "지속 진단", "버그바운티", "경영진 보고"],
                "exemplar_answer": (
                    "연 1회 외부 점검과 분기 자체 스캔을 병행하고, 발견 항목은 티켓 시스템에서 "
                    "등급별 SLA로 조치 기한을 추적합니다. 조치 완료 시 재점검으로 검증하며, "
                    "결과는 분기 단위로 경영진에 보고합니다."
                ),
            },
        ],
    },

    # ── 2.12 재해복구 ──
    {
        "id": "2.12.1-disaster-recovery",
        "isms_control_id": "2.12.1",
        "isms_control_title": "재해·재난 대비 안전조치",
        "scenario_context": (
            "재해복구 계획서는 존재하나 RTO/RPO 목표값이 정의되지 않았고, 최근 2년간 "
            "복구 훈련을 수행한 기록이 없습니다."
        ),
        "auditor_question": "재해복구 계획의 실효성은 어떻게 검증하고 계십니까?",
        "default_rebuttal": "RTO/RPO 정의와 정기 훈련 수행에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-plan-only",
                "tier": "half",
                "description": "계획만 존재 — 훈련/검증 부재. 보완 시 절반.",
                "trigger_keywords": ["계획서", "BCP", "DR 계획"],
                "rebuttal": (
                    "계획서 존재만으로는 실효성을 보장할 수 없습니다. RTO/RPO 명확화와 "
                    "주기적 복구 훈련이 함께 운영되어야 합니다."
                ),
                "acknowledgment_keywords": ["훈련", "RTO", "RPO", "보완"],
                "exemplar_answer": (
                    "현재 DR 계획서만 보유 중이나, 시스템별 RTO/RPO 목표를 정의하고 "
                    "연 1회 이상 복구 훈련을 수행해 실효성을 검증하도록 보완하겠습니다."
                ),
            },
            {
                "id": "full-tested-and-revised",
                "tier": "full",
                "description": "RTO/RPO + 정기 훈련 + 결과 반영 = 만점.",
                "trigger_keywords": ["RTO", "RPO", "복구 훈련", "DR 훈련", "정기 훈련"],
                "follow_up": (
                    "훈련 체계는 적절합니다. 훈련 결과의 미흡 사항을 계획에 "
                    "반영하는 절차는 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["개선 반영", "사후 검토", "경영진 보고"],
                "exemplar_answer": (
                    "시스템 중요도별로 RTO·RPO를 정의하고 연 1회 이상 모의 복구 훈련을 수행합니다. "
                    "훈련 후 사후 검토를 통해 미흡 사항을 식별하고 DR 계획을 개정하며, "
                    "경영진에게 결과를 보고합니다."
                ),
            },
        ],
    },
]


# ============================================================================
# Stage 3 — ISMS-P 3.x (개인정보 처리 단계별 요구사항)
# ============================================================================
STAGE_3_QUESTIONS: list[dict[str, Any]] = [
    # ── 3.1 수집 시 보호조치 ──
    {
        "id": "3.1.1-collection-purpose",
        "isms_control_id": "3.1.1",
        "isms_control_title": "개인정보 수집·이용",
        "scenario_context": (
            "회원가입 시 수집되는 개인정보 항목 중 일부에 대해 동의 항목과 실제 수집 "
            "항목이 일치하지 않고, '서비스 품질 향상'이라는 모호한 목적으로 추가 항목을 "
            "수집한 흔적이 확인되었습니다."
        ),
        "auditor_question": "개인정보 수집 항목과 목적의 일치성은 어떻게 관리하고 계십니까?",
        "default_rebuttal": "수집 항목·목적·동의 절차의 일관성에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-consent-form",
                "tier": "half",
                "description": "동의서만 존재 — 실 수집 검증 부재. 보완 시 절반.",
                "trigger_keywords": ["동의서", "약관", "체크박스"],
                "rebuttal": (
                    "동의서 양식 보유만으로는 부족합니다. 실제 수집 항목과 동의 항목의 "
                    "일치성을 정기 검증하는 절차가 필요합니다."
                ),
                "acknowledgment_keywords": ["일치성 검증", "정기 점검", "보완"],
                "exemplar_answer": (
                    "동의서 양식과 시스템 입력 필드를 정기적으로 매핑 점검해 일치성을 "
                    "검증하고, 변경 시 동의서·고지를 함께 갱신하는 절차를 도입하겠습니다."
                ),
            },
            {
                "id": "full-mapping-controlled",
                "tier": "full",
                "description": "수집 항목-목적 매핑 + 분기 점검 + 변경관리 = 만점.",
                "trigger_keywords": ["매핑", "수집 목적", "최소 수집", "정기 점검"],
                "follow_up": (
                    "관리 체계는 적절합니다. 신규 서비스 도입 시 수집 항목 검토 절차는 "
                    "어떻게 운영하고 계십니까?"
                ),
                "compensating_keywords": ["검토 절차", "신규 서비스", "PIA", "법무 검토"],
                "exemplar_answer": (
                    "수집 항목별로 목적과 법적 근거를 매핑 관리하고, 최소수집 원칙에 따라 "
                    "분기마다 항목을 점검합니다. 신규 서비스 도입 시 PIA와 법무 검토를 "
                    "거쳐 동의서와 시스템을 동기화합니다."
                ),
            },
        ],
    },

    # ── 3.2 보유 및 이용 시 보호조치 ──
    {
        "id": "3.2.1-pii-inventory",
        "isms_control_id": "3.2.1",
        "isms_control_title": "개인정보 현황관리",
        "scenario_context": (
            "개인정보 처리 현황표가 작성되어 있으나, 일부 시스템(예: 마케팅 분석 DB, "
            "고객 응대 로그 등)이 누락되어 있고 최근 1년간 갱신 이력이 없습니다."
        ),
        "auditor_question": "전사 개인정보 처리 현황은 어떻게 식별·갱신하고 계십니까?",
        "default_rebuttal": "전사 개인정보 처리 항목·시스템 식별과 갱신 절차에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-self-report",
                "tier": "half",
                "description": "부서 자체 보고 — 사각지대 존재. 보완 시 절반.",
                "trigger_keywords": ["부서 보고", "자체 신고", "현황 조사"],
                "rebuttal": (
                    "부서 자율 보고만으로는 사각지대가 발생합니다. 자동 스캔이나 "
                    "DB 메타데이터 점검 같은 보완 체계가 필요합니다."
                ),
                "acknowledgment_keywords": ["자동 스캔", "메타데이터", "DLP", "보완"],
                "exemplar_answer": (
                    "현재 부서 자체 보고 방식에 의존하고 있어, DB 메타데이터 자동 스캔이나 "
                    "DLP 기반 발견 체계를 추가 도입해 사각지대를 보완하겠습니다."
                ),
            },
            {
                "id": "full-automated-discovery",
                "tier": "full",
                "description": "자동 발견 + 분기 점검 + 변경관리 = 만점.",
                "trigger_keywords": ["자동 발견", "데이터 분류 도구", "Macie", "DLP", "분기 점검"],
                "follow_up": (
                    "발견 체계는 적절합니다. 발견된 개인정보의 보유 기간·파기 관리는 "
                    "어떻게 연동하고 계십니까?"
                ),
                "compensating_keywords": ["보유 기간", "파기 연계", "라이프사이클"],
                "exemplar_answer": (
                    "Amazon Macie 등 자동 데이터 분류 도구로 개인정보 보유 시스템을 발견하고, "
                    "분기마다 현황을 갱신합니다. 발견된 데이터는 보유 기간과 파기 일정에 "
                    "연결되어 라이프사이클로 관리됩니다."
                ),
            },
        ],
    },

    # ── 3.3 제공 시 보호조치 ──
    {
        "id": "3.3.1-third-party-provision",
        "isms_control_id": "3.3.1",
        "isms_control_title": "개인정보 제3자 제공",
        "scenario_context": (
            "제휴 마케팅 캠페인을 위해 협력사에 회원 개인정보를 제공한 사례가 있으나, "
            "사전 별도 동의 없이 일반 이용약관 내 문구만 근거로 제공된 것이 확인되었습니다."
        ),
        "auditor_question": "제3자 제공 시 동의는 어떤 절차로 취득하고 계십니까?",
        "default_rebuttal": "제3자 제공 시 별도 동의·고지·기록 절차에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-general-tos",
                "tier": "half",
                "description": "이용약관 일괄 동의 — 별도 동의 부재. 보완 시 절반.",
                "trigger_keywords": ["이용약관", "포괄 동의", "약관 동의"],
                "rebuttal": (
                    "법령상 제3자 제공은 별도 동의가 필수입니다. 약관 동의로는 대체될 수 없습니다. "
                    "제공 항목·목적을 명시한 별도 동의 절차가 필요합니다."
                ),
                "acknowledgment_keywords": ["별도 동의", "고지 강화", "보완"],
                "exemplar_answer": (
                    "현재 약관 동의에 의존하고 있어, 제공 항목·목적·기간을 명시한 별도 동의 "
                    "절차와 동의 이력 보존 체계로 보완하겠습니다."
                ),
            },
            {
                "id": "full-itemized-consent",
                "tier": "full",
                "description": "항목별 별도 동의 + 이력 보존 + 정기 점검 = 만점.",
                "trigger_keywords": ["별도 동의", "항목별 동의", "동의 이력", "고지"],
                "follow_up": (
                    "동의 체계는 적절합니다. 동의 철회·제공 중단 요청은 어떤 절차로 "
                    "처리하고 계십니까?"
                ),
                "compensating_keywords": ["동의 철회", "제공 중단", "기록 관리"],
                "exemplar_answer": (
                    "제3자 제공 시 제공받는 자·항목·목적·기간을 명시한 별도 동의를 항목별로 "
                    "취득하고, 동의 이력을 보존합니다. 동의 철회 요청 시 즉시 제공 중단 절차가 "
                    "운영되며, 분기마다 제공 현황을 점검합니다."
                ),
            },
        ],
    },

    # ── 3.4 파기 시 보호조치 ──
    {
        "id": "3.4.1-pii-destruction",
        "isms_control_id": "3.4.1",
        "isms_control_title": "개인정보의 파기",
        "scenario_context": (
            "보유 기간이 경과한 회원 데이터 약 12만 건이 운영 DB에 그대로 잔존하고 있고, "
            "백업본에도 파기 처리가 적용되지 않은 것이 확인되었습니다."
        ),
        "auditor_question": "보유 기간 경과 개인정보의 파기는 어떻게 수행하고 계십니까?",
        "default_rebuttal": "파기 대상 식별·운영/백업 동시 파기·복구 불가 검증에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-prod-only",
                "tier": "half",
                "description": "운영 DB만 파기 — 백업 미파기. 보완 시 절반.",
                "trigger_keywords": ["운영 DB", "파기 절차", "보유 기간"],
                "rebuttal": (
                    "운영 DB만 파기하고 백업본이 남아있으면 실질적 파기로 인정되지 않습니다. "
                    "백업본까지 포함한 파기 또는 분리 보관·접근 차단이 필요합니다."
                ),
                "acknowledgment_keywords": ["백업", "분리 보관", "접근 차단", "보완"],
                "exemplar_answer": (
                    "운영 DB는 파기 절차가 있으나 백업본이 누락된 상태입니다. 백업본도 "
                    "보유 기간 경과 시 함께 파기되거나, 분리 보관·접근 차단되도록 보완하겠습니다."
                ),
            },
            {
                "id": "full-end-to-end-destruction",
                "tier": "full",
                "description": "운영/백업/로그 일괄 파기 + 복구 불가 검증 = 만점.",
                "trigger_keywords": ["자동 파기", "복구 불가", "백업 파기", "스케줄러"],
                "follow_up": (
                    "파기 절차는 적절합니다. 파기 실행 기록의 보존과 정기 점검은 어떻게 "
                    "운영하고 계십니까?"
                ),
                "compensating_keywords": ["파기 기록", "정기 점검", "결과 보고"],
                "exemplar_answer": (
                    "보유 기간 경과 데이터는 스케줄러로 운영 DB·백업·로그에서 자동 파기되며, "
                    "암호학적 삭제로 복구 불가능 상태를 검증합니다. 파기 기록을 보존하고 "
                    "분기마다 점검 결과를 보고합니다."
                ),
            },
        ],
    },

    # ── 3.5 정보주체 권리보호 ── (기존 + 신규)
    {
        "id": "3.5.1-privacy-policy",
        "isms_control_id": "3.5.1",
        "isms_control_title": "개인정보처리방침 공개",
        "scenario_context": (
            "개인정보 처리방침이 웹사이트에 게시되어 있으나, 최근 위탁 업체 변경 사항이 "
            "방침에 반영되지 않았고 개정 이력 공개도 누락되어 있습니다."
        ),
        "auditor_question": "개인정보 처리방침의 변경 사항은 어떻게 반영·공개하고 계십니까?",
        "default_rebuttal": "처리방침의 적시 갱신과 이력 공개에 대한 증적이 부족합니다.",
        "answer_paths": [
            {
                "id": "half-static-publication",
                "tier": "half",
                "description": "게시만 — 변경 관리 부재. 보완 시 절반.",
                "trigger_keywords": ["웹사이트 게시", "공개", "공시"],
                "rebuttal": (
                    "게시만으로는 부족합니다. 위탁사 변경 등 사실 변경 시 즉시 반영하는 "
                    "절차와 개정 이력 공개가 필요합니다."
                ),
                "acknowledgment_keywords": ["개정 이력", "변경 반영", "보완"],
                "exemplar_answer": (
                    "현재 게시만 운영 중이라, 위탁사·수집 항목 등 변경 발생 시 즉시 방침을 "
                    "갱신하고 개정 이력을 함께 공개하는 절차로 보완하겠습니다."
                ),
            },
            {
                "id": "full-change-managed",
                "tier": "full",
                "description": "변경 트리거 + 이력 공개 + 통지 = 만점.",
                "trigger_keywords": ["변경 트리거", "개정 이력", "이용자 통지", "위탁 변경"],
                "follow_up": (
                    "방침 관리는 적절합니다. 중요 변경 시 이용자 사전 통지 기준과 "
                    "동의 갱신 절차는 어떻게 운영합니까?"
                ),
                "compensating_keywords": ["사전 통지", "동의 갱신", "고지 기한"],
                "exemplar_answer": (
                    "위탁사 변경·수집 항목 변경 등의 사유가 발생하면 즉시 처리방침을 갱신하고, "
                    "개정 이력을 함께 공시합니다. 중요 변경 시에는 시행 30일 전 이용자에게 "
                    "통지하고 필요 시 동의를 다시 취득합니다."
                ),
            },
        ],
    },
    {
        "id": "3.5.2-mass-query-anomaly",
        "isms_control_id": "3.5.2",
        "isms_control_title": "정보주체 권리보장 / 이상행위 소명",
        "scenario_context": (
            "개인정보취급자에 의해 개인정보가 1,000건 이상 조회될 시 이를 "
            "이상행위로 판단하고 소명하도록 하는 정책을 운영 중입니다. "
            "3월 15일에 2,500건 조회 사건이 발생하였지만, 심사 당일(5월 1일) "
            "기준 소명 자료를 확인할 수 없습니다."
        ),
        "auditor_question": (
            "3월 15일자 2,500건 조회 건에 대한 소명이 왜 확인되지 않습니까? "
            "이를 '적합'으로 평가할 만한 근거가 있습니까?"
        ),
        "default_rebuttal": (
            "이상행위 임계치를 초과한 조회에 대해 소명 절차가 운영된 증적이 보이지 않습니다. "
            "정책상 사전 승인·예외처리·진행 중 절차 중 어떤 근거에 해당하는지 제시해 주십시오."
        ),
        "answer_paths": [
            {
                "id": "full-pre-approval",
                "tier": "full",
                "description": "사전 결재 승인된 정당한 대량 조회 업무 — 결재 증적 제시 시 만점.",
                "trigger_keywords": ["사전 승인", "사전 결재", "그룹웨어 결재", "정당한 업무", "예외 처리"],
                "follow_up": (
                    "사전 승인 건이라면 결재 문서 ID와 조회 사유, 승인자 정보가 "
                    "매칭되어야 합니다. 해당 증적을 어떻게 보존하고 계십니까?"
                ),
                "compensating_keywords": ["결재 문서", "보존", "승인자"],
                "exemplar_answer": (
                    "3월 15일 조회는 그룹웨어에서 사전 결재된 정당한 업무 목적의 예외 처리 건입니다. "
                    "결재 문서 ID와 승인자 정보가 조회 로그와 매칭되며, 증적은 별도로 보존됩니다."
                ),
            },
            {
                "id": "full-batch-program",
                "tier": "full",
                "description": "취급자(사람) 아닌 배치 프로그램 작업 — 자동화 작업 기록 제시 시 만점.",
                "trigger_keywords": ["배치", "배치 프로그램", "자동화", "스케줄러", "정산 배치"],
                "follow_up": (
                    "배치 작업이라면 사람의 직접 조회가 아니라는 점이 명확해야 합니다. "
                    "작업 실행 로그와 실행 주체(서비스 계정) 기록은 어떻게 분리·관리하십니까?"
                ),
                "compensating_keywords": ["서비스 계정", "작업 로그", "주요직무"],
                "exemplar_answer": (
                    "해당 조회는 개인정보취급자(사람)가 아닌 정산 배치 프로그램이 서비스 계정으로 "
                    "수행한 작업입니다. 작업 로그와 실행 주체는 사람 사용자와 분리되어 별도 관리되며, "
                    "주요직무자 기준에 해당하지 않습니다."
                ),
            },
            {
                "id": "full-ongoing-process",
                "tier": "full",
                "description": "월별 소명 절차 진행 중 — 4월 1일자 소명 요청 증적 제시 시 만점.",
                "trigger_keywords": ["진행 중", "월별 점검", "소명 요청", "내부 검토 프로세스", "기한 도래"],
                "follow_up": (
                    "진행 중 절차라면 소명 요청 발송 시점과 회신 기한, 미회신 시 "
                    "에스컬레이션 절차가 정의되어 있어야 합니다. 어떻게 운영하십니까?"
                ),
                "compensating_keywords": ["회신 기한", "에스컬레이션", "절차 문서"],
                "exemplar_answer": (
                    "월별 이상행위 점검 절차에 따라 4월 1일에 소명 요청이 발송되었고, "
                    "정해진 회신 기한 내 내부 검토 프로세스로 진행 중인 건입니다. "
                    "미회신 시 에스컬레이션 절차가 정의되어 있어 적합으로 판단됩니다."
                ),
            },
        ],
    },
]


# ============================================================================
# 통합 — 각 스테이지의 시드 질문 풀
# ============================================================================
DEFAULT_QUESTIONS_BY_STAGE: dict[int, list[dict[str, Any]]] = {
    1: STAGE_1_QUESTIONS,
    2: STAGE_2_QUESTIONS,
    3: STAGE_3_QUESTIONS,
}
