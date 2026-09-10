"""Shipped-vs-stub inventory so the prototype does not over-claim."""

from __future__ import annotations

FEATURES: list[dict[str, str]] = [
    {
        "id": "taiwan_pii",
        "status": "shipped",
        "title": "台灣在地個資偵測與代號化",
        "detail": "姓名、學校、手機/市話、身分證（含 checksum）、地址：進模型前換成 <TYPE_N>。",
    },
    {
        "id": "session_vault",
        "status": "shipped",
        "title": "多輪 Session Vault",
        "detail": "同一 session 裡，王小明永遠是 <PERSON_1>。記憶體實作，介面可換成 Redis。",
    },
    {
        "id": "deanonymize",
        "status": "shipped",
        "title": "出站還原給兒童",
        "detail": "模型只看代號；小朋友看到的回覆會把代號換回原本的詞。",
    },
    {
        "id": "gemini",
        "status": "shipped",
        "title": "Gemini 真實對話",
        "detail": "本機用 GEMINI_API_KEY 呼叫 Gemini。模型收到的 contents 已是代號化文本。",
    },
    {
        "id": "tw_id_checksum",
        "status": "shipped",
        "title": "身分證檢查碼",
        "detail": "格式對但 checksum 錯的字串不會被當成 TW_ID，降低誤殺。",
    },
    {
        "id": "image_redact",
        "status": "api_only",
        "title": "零落盤圖片遮碼",
        "detail": "redact_image_in_memory() 已實作。此 prototype 對話頁尚未開放上傳照片。",
    },
    {
        "id": "pipeline",
        "status": "shipped",
        "title": "可擴充 Guard Pipeline",
        "detail": "inbound / outbound 的 Chain of Responsibility。PII 步驟已接上。",
    },
    {
        "id": "content_safety",
        "status": "stub",
        "title": "內容安全（ContentSafetyStep）",
        "detail": "介面已在鏈上，目前是 pass-through。尚未做色情/自傷/暴力分類。",
    },
    {
        "id": "socratic",
        "status": "stub",
        "title": "蘇格拉底教學（SocraticPedagogyStep）",
        "detail": "步驟是 stub。目前只靠 Gemini system prompt 鼓勵思考，不是獨立教學引擎。",
    },
    {
        "id": "parent_audit",
        "status": "stub",
        "title": "家長稽核（ParentAuditStep）",
        "detail": "介面已在鏈上，尚未寫入監護人可讀的紀錄系統。",
    },
]
