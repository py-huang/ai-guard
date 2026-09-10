"""Shipped-vs-stub inventory plus knobs operators can tune."""

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
        "title": "Gemini 真實對話（含忙碌重試）",
        "detail": "503/429 會指數退避並換模型；兒童畫面只看到溫柔提示，不會看到 API JSON。",
    },
    {
        "id": "tw_id_checksum",
        "status": "shipped",
        "title": "身分證檢查碼",
        "detail": "格式對但 checksum 錯的字串不會被當成 TW_ID，降低誤殺。",
    },
    {
        "id": "image_redact",
        "status": "shipped",
        "title": "零落盤圖片遮碼",
        "detail": "示範聯絡簿用繪製座標遮碼（不需 OCR）。上傳照片走 Presidio + Tesseract；沒裝 OCR 會說明原因。",
    },
    {
        "id": "pipeline",
        "status": "shipped",
        "title": "可擴充 Guard Pipeline",
        "detail": "inbound / outbound 的 Chain of Responsibility。PII、內容安全、蘇格拉底、家長稽核都已接上。",
    },
    {
        "id": "content_safety",
        "status": "shipped",
        "title": "內容安全（ContentSafetyStep）",
        "detail": "色情 / 自傷 / 暴力用語分類；命中則不呼叫 Gemini，改回兒童安全句。歷史與健康教育作業不在封鎖詞內。",
    },
    {
        "id": "socratic",
        "status": "shipped",
        "title": "蘇格拉底教學（SocraticPedagogyStep）",
        "detail": "偵測「直接給答案」時，進站加上教學約束、出站若沒有引導問句會補一句。不是只靠 system prompt。",
    },
    {
        "id": "parent_audit",
        "status": "shipped",
        "title": "家長稽核（ParentAuditStep）",
        "detail": "寫入監護人可讀事件：預設是代號化文本與攔截類別，可選擇用 vault 還原給家長看。",
    },
]

TUNABLES: list[dict[str, str]] = [
    {
        "name": "Gemini 模型清單與重試",
        "where": "safety_gateway/playground/llm.py → _GEMINI_MODELS, max_attempts, backoff_seconds",
        "detail": "預設 3.6-flash → 3.5 → 3.8。可改次數、退避秒數、timeout。兒童文案在 _CHILD_BUSY / _CHILD_FAIL。",
    },
    {
        "name": "內容安全詞表",
        "where": "steps/content_safety.py → DEFAULT_CATALOG、CHILD_MESSAGES",
        "detail": "可加類別或改成外部模型分數門檻。目前是明確片語，避免「性教育」「二次大戰」誤殺。",
    },
    {
        "name": "蘇格拉底強度",
        "where": "SocraticPedagogyStep(hint_level=gentle|medium|strict)、HOMEWORK_CUES",
        "detail": "可調什麼算「要答案」、以及出站補問的語氣。關閉 enabled=False 即只靠 LLM prompt。",
    },
    {
        "name": "家長稽核保留",
        "where": "InMemoryAuditLog(max_events=200)",
        "detail": "可改 TTL、改接資料庫。預設存代號化文本；家長頁可用 vault 還原。生產應加密與權限控管。",
    },
    {
        "name": "Session Vault",
        "where": "BaseSessionVault / InMemorySessionVault",
        "detail": "介面已是 Redis 形狀（session_id → token map）。多實例部署時換成 Redis 並設 TTL。",
    },
    {
        "name": "圖片遮碼",
        "where": "InMemoryImageRedactor OCR lang=chi_tra+eng；示範圖用 pii/demo_image.py 座標",
        "detail": "可改填充色、OCR 語言、或改成雲端文件 AI。示範圖不依賴 Tesseract。",
    },
    {
        "name": "對話歷史長度",
        "where": "PlaygroundChat(max_history=12)",
        "detail": "越長越能連貫，但也越容易把舊回合的代號上下文送進模型。",
    },
]
