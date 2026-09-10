from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.vault.memory import InMemorySessionVault


def mock_llm_echo(sanitized_prompt: str) -> str:
    return f"小朋友你好，我聽到你說：{sanitized_prompt}。"


def test_full_lifecycle_inbound_llm_outbound() -> None:
    vault = InMemorySessionVault()
    gateway = AISafetyGateway(vault=vault)
    session_id = "child-session-001"
    child_input = (
        "我叫王小明，我在中山國小上課，電話是0912-345-678，"
        "身分證是A123456789，住在台北市中正區重慶南路一段122號"
    )

    inbound = gateway.process_inbound(session_id, child_input)
    assert "王小明" not in inbound.processed_text
    assert "中山國小" not in inbound.processed_text
    assert "0912-345-678" not in inbound.processed_text
    assert "A123456789" not in inbound.processed_text
    assert "台北市中正區" not in inbound.processed_text
    assert "<PERSON_1>" in inbound.processed_text
    assert "<SCHOOL_1>" in inbound.processed_text
    assert "<PHONE_NUMBER_1>" in inbound.processed_text
    assert "<TW_ID_1>" in inbound.processed_text
    assert "<LOCATION_1>" in inbound.processed_text
    assert inbound.steps_executed[0] == "taiwan_pii"
    assert inbound.steps_executed == [
        "taiwan_pii",
        "content_safety",
        "socratic_pedagogy",
        "parent_audit",
    ]
    assert inbound.blocked is False

    llm_output = mock_llm_echo(inbound.processed_text)
    assert "王小明" not in llm_output
    outbound = gateway.process_outbound(session_id, llm_output)
    assert outbound.processed_text == mock_llm_echo(inbound.original_text)
    assert "王小明" in outbound.processed_text
    assert "<PERSON_1>" not in outbound.processed_text
    assert "parent_audit" in outbound.steps_executed
    assert outbound.steps_executed == [
        "content_safety",
        "socratic_pedagogy",
        "parent_audit",
        "taiwan_pii",
    ]

    second = gateway.process_inbound(session_id, "同學王小明明天去中山國小")
    assert "<PERSON_1>" in second.processed_text
    assert "<SCHOOL_1>" in second.processed_text
    assert vault.list_mappings(session_id)["<PERSON_1>"] == "王小明"


def test_fullwidth_digits_fold_without_changing_cjk_punctuation() -> None:
    gateway = AISafetyGateway()
    inbound = gateway.process_inbound("s", "電話是０９１２３４５６７８，我叫王小明")
    assert "，" in inbound.processed_text
    assert "<PHONE_NUMBER_1>" in inbound.processed_text
    assert "<PERSON_1>" in inbound.processed_text
    assert "０９" not in inbound.processed_text


def test_deanonymize_text_passthrough_without_mappings() -> None:
    gateway = AISafetyGateway()
    restored = gateway.deanonymize_text("missing", "hello <PERSON_1>")
    assert restored == "hello <PERSON_1>"
