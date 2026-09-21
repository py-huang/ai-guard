"""Lifecycle demo: child input -> inbound tokens -> mock LLM echo -> outbound restore."""

from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.vault.memory import InMemorySessionVault


def mock_llm_echo(sanitized_prompt: str) -> str:
    """Stand-in for a child-facing model that only sees tokenized text."""
    return f"小朋友你好，我聽到你說：{sanitized_prompt}。我們可以一起想下一步喔！"


def run_lifecycle_demo() -> None:
    vault = InMemorySessionVault()
    gateway = AISafetyGateway(vault=vault)
    session_id = "k12-session-demo-001"

    turn_one = (
        "我叫王小明，我是中山國小的小朋友。"
        "我家住在台北市中正區重慶南路一段122號2樓，"
        "媽媽電話是0912-345-678，老師說身分證是A123456789。"
    )
    inbound_one = gateway.process_inbound(session_id, turn_one)
    llm_one = mock_llm_echo(inbound_one.processed_text)
    outbound_one = gateway.process_outbound(session_id, llm_one)

    turn_two = "同學王小明明天還要去中山國小上課。"
    inbound_two = gateway.process_inbound(session_id, turn_two)
    llm_two = mock_llm_echo(inbound_two.processed_text)
    outbound_two = gateway.process_outbound(session_id, llm_two)

    print("=== Turn 1 child input ===")
    print(turn_one)
    print("=== Turn 1 inbound (pre-LLM) ===")
    print(inbound_one.processed_text)
    print("entities:", [entity.model_dump() for entity in inbound_one.entities])
    print("steps:", inbound_one.steps_executed)
    print("=== Turn 1 mock LLM ===")
    print(llm_one)
    print("=== Turn 1 outbound (post-LLM) ===")
    print(outbound_one.processed_text)
    print("=== Turn 2 inbound (same PERSON/SCHOOL tokens) ===")
    print(inbound_two.processed_text)
    print("=== Turn 2 outbound ===")
    print(outbound_two.processed_text)
    print("=== Session vault ===")
    print(vault.list_mappings(session_id))


def main() -> None:
    run_lifecycle_demo()


if __name__ == "__main__":
    main()
