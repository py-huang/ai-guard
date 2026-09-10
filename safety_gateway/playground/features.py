"""Shipped-vs-stub inventory plus knobs operators can tune."""

from __future__ import annotations

FEATURES: list[dict[str, str]] = [
    {
        "id": "taiwan_pii",
        "status": "shipped",
        "title": "台灣在地個資偵測與代號化",
        "detail": "姓名、學校、手機/市話、身分證 checksum、地址，以及民國日期、護照、駕照、帳號、機構：進模型前換成 <TYPE_N>。",
    },
    {
        "id": "presidio_defaults_zh",
        "status": "shipped",
        "title": "Presidio 預設個資（掛在繁中句子上）",
        "detail": "Email、信用卡（Luhn）、美國 SSN、網址、IP、MAC、加密貨幣位址、IBAN、英文日期與電話以 language=zh 註冊。有 zh_core_web_md 時再掛 spaCy 人名 NER（忽略今天/3月這類日期，避免誤殺作業）。",
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
        "detail": "Presidio 負責照片上的繁中文字個資。人臉另外用 OpenCV Haar 遮掉，避免拿同學照片搞怪。示範聯絡簿仍可用座標遮碼對照。",
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
        "detail": "對齊台灣兒少保護／影視出版分級的兒童不宜：色情、血腥暴力、恐怖驚嚇、自傷與危險挑戰、毒品菸酒檳榔、仇恨言語、賭博，加上既有的同學照片惡搞。進站出站都會擋；歷史與健康教育作業不在封鎖詞內。Gemini 另開低門檻安全濾網當第二層。",
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
        "detail": "可加類別或改成外部模型分數門檻。目前是明確片語，避免「性教育」「二次大戰」「菸害防制」誤殺。",
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
        "where": "pii/ocr.py RapidOcrEngine；模型在 .venv/lib/.../rapidocr_onnxruntime/models",
        "detail": "OCR 與快取都關在虛擬環境。人臉敏感度在 pii/faces.py（Haar minSize、padding）。Presidio 不管臉，只管文字。",
    },
    {
        "name": "對話歷史長度",
        "where": "PlaygroundChat(max_history=12)",
        "detail": "越長越能連貫，但也越容易把舊回合的代號上下文送進模型。",
    },
    {
        "name": "繁中 spaCy 模型",
        "where": "safety_gateway/nlp.py → ZH_SPACY_MODEL、NLP_CONFIGURATION",
        "detail": "預設 zh_core_web_md（OntoNotes，簡繁字都能切，但日期 NER 會誤殺作業所以關掉）。沒裝模型時退回 regex-only。安裝：python -m spacy download zh_core_web_md",
    },
]
