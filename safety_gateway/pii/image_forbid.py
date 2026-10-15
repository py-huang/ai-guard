"""Child image forbid list: classify then block the whole photo.

The five categories match the child UI「哪些圖片不應上傳」. This is layout + OCR
language, not a YOLO/NSFW neural net — those would send pixels to a cloud model
or add hundreds of MB. Pixel-only nudes/gore without text still need a later
local vision backend.
"""

from __future__ import annotations

import re

# Child UI order: 1 body, 2 violence, 3 voyeur, 4 documents/finance, 5 other.
FORBID_REASONS = ("body", "violence", "voyeur", "document", "other")

_ID_BACK_LABELS = ("配偶", "住址", "出生地", "役別", "身分證字號", "國民身分證")
_ID_FRONT_HINTS = (
    "國民身分證",
    "身分證字號",
    "中華民國國民身分證",
    "第二代國民身分證",
    "第二代身分證",
    "身分證",
    "身份證",
    "健保卡",
    "健保卡號",
    "全民健康保險",
    "保險對象",
    "全民健保",
    "自然人憑證",
    "內政部憑證",
    "居留證",
    "外僑居留",
    "外來人口統一證號",
    "居留證號碼",
    "永久居留",
    "戶口名簿",
    "戶號",
    "電子戶口名簿",
    "晶片金融卡",
    "郵政存簿",
    "郵政存簿儲金簿",
    "儲金簿",
    "中華郵政",
    "郵局代號",
    "含檢號",
    "存摺封面",
    "銀行存摺",
    "存摺",
    "存簿",
    "統一編號",
    "統號",
    "身分識別",
    "身心障礙證明",
    "中華民國護照",
    "普通護照",
    "公路總局",
    "交通部公路",
    "監理站",
    "汽機車駕駛執照",
    "普通重型機車",
    "出生年月日",
    "發證日期",
)
_ID_LAYOUT_LABELS = ("姓名", "出生", "發證", "性別", "役別", "住址", "配偶", "戶籍")
_PASSBOOK_LAYOUT_LABELS = ("局號", "帳號", "戶名", "郵局", "存簿", "儲金簿", "郵局代號", "含檢號")
_CARD_HINTS = (
    "visa",
    "mastercard",
    "master card",
    "american express",
    "amex",
    "jcb",
    "unionpay",
    "銀聯",
    "信用卡",
    "金融卡",
    "debit card",
    "credit card",
    "cardholder",
    "valid thru",
    "valid through",
    "卡號",
    "信用卡號",
    "安全碼",
    "cvv",
    "cvc",
    "晶片卡",
)
_PASSPORT_HINTS = ("護照", "passport", "passeport", "reisepass")
_LICENSE_HINTS = (
    "駕駛執照",
    "駕照",
    "driver license",
    "driver licence",
    "drivers license",
    "driving licence",
    "identity card",
    "identitycard",
    "carte nationale",
    "national id",
    "id card",
    "land transportation",
    "motorcycle",
    "ausweis",
    "cedula",
    "nric",
    "bescheinigung",
)

_BODY_NEEDLES = ("裸照", "裸體", "裸露", "私密部位", "下體", "走光", "nude", "naked", "nsfw")
_VIOLENCE_NEEDLES = (
    "血腥",
    "碎屍",
    "屍體特寫",
    "斬首",
    "虐殺",
    "超血腥",
    "戰場",
    "戰爭畫面",
    "gore",
    "massacre",
    "wounded",
    "corpse",
    "battlefield",
    "combat",
)
_VOYEUR_NEEDLES = (
    "偷拍",
    "針孔",
    "偷窺",
    "更衣室偷",
    "裙底",
    "hidden camera",
    "spy camera",
    "spy",
    "peephole",
    "cctv",
    "surveillance",
    "webcam",
    "監視器",
    "針孔攝影機",
    "貓眼",
    "door viewer",
)
_OTHER_NEEDLES = (
    "色情",
    "A片",
    "毒品",
    "自殺方法",
    "怎麼自殺",
    "cigarette",
    "cigaretten",
    "tobacco",
    "casino",
    "gambling",
    "slot machine",
    "beer",
    "brew",
    "whisky",
    "whiskey",
    "alcohol",
    "香菸",
    "菸",
    "賭博",
    "piwo",
    "nicotin",
    "檳榔",
    "香煙",
    "紙菸",
    "酒類",
    "啤酒",
    "賭場",
    "樂透",
    "刮刮樂",
)

_DOCUMENT_ENTITIES = frozenset(
    {
        "TW_ID",
        "TW_PASSPORT",
        "TW_DRIVER_LICENSE",
        "TW_BANK_ACCOUNT",
        "CREDIT_CARD",
        "IBAN_CODE",
        "US_BANK_NUMBER",
        "US_ITIN",
        "IMAGE_DOCUMENT",
    }
)

_REASON_ENTITY = {
    "IMAGE_BODY": "body",
    "IMAGE_VIOLENCE": "violence",
    "IMAGE_VOYEUR": "voyeur",
    "IMAGE_DOCUMENT": "document",
    "IMAGE_OTHER": "other",
}


def classify_forbidden_image(ocr_text: str, entities: list[str] | set[str] | None = None) -> str | None:
    """Return a forbid reason or None. First match in child-list priority."""
    blob = ocr_text or ""
    kinds = {item.upper() for item in (entities or [])}

    if _looks_like_body(blob) or "IMAGE_BODY" in kinds:
        return "body"
    if _looks_like_voyeur(blob) or "IMAGE_VOYEUR" in kinds:
        return "voyeur"
    if _looks_like_document(blob) or kinds & _DOCUMENT_ENTITIES:
        return "document"
    if _looks_like_violence(blob) or "IMAGE_VIOLENCE" in kinds:
        return "violence"
    if _looks_like_other(blob) or "IMAGE_OTHER" in kinds:
        return "other"
    for entity, reason in _REASON_ENTITY.items():
        if entity in kinds:
            return reason
    return None


def document_entities_from_ocr(ocr_text: str) -> set[str]:
    if _looks_like_document(ocr_text):
        return {"TW_ID", "IMAGE_DOCUMENT"}
    return set()


def extra_forbid_entities(ocr_text: str, image_bytes: bytes | None = None) -> set[str]:
    found: set[str] = set()
    if _looks_like_body(ocr_text):
        found.add("IMAGE_BODY")
    if _looks_like_violence(ocr_text):
        found.add("IMAGE_VIOLENCE")
    if _looks_like_voyeur(ocr_text):
        found.add("IMAGE_VOYEUR")
    if _looks_like_document(ocr_text) or _looks_like_card_layout(ocr_text):
        found.add("IMAGE_DOCUMENT")
        found.add("TW_ID")
        if _looks_like_passbook(ocr_text):
            found.add("TW_BANK_ACCOUNT")
    if _looks_like_other(ocr_text):
        found.add("IMAGE_OTHER")
    if found:
        return found
    if image_bytes:
        from safety_gateway.pii.image_vision import classify_image_pixels

        visual = classify_image_pixels(image_bytes)
        mapping = {
            "body": "IMAGE_BODY",
            "violence": "IMAGE_VIOLENCE",
            "voyeur": "IMAGE_VOYEUR",
            "document": "IMAGE_DOCUMENT",
            "other": "IMAGE_OTHER",
        }
        entity = mapping.get(visual or "")
        if entity:
            found.add(entity)
            if entity == "IMAGE_DOCUMENT":
                found.add("TW_ID")
    return found


def _looks_like_card_layout(text: str) -> bool:
    """Dense identifier text even when OCR is messy (foreign licenses, MRZ-like)."""
    blob = text or ""
    lowered = blob.lower()
    digits = sum(ch.isdigit() for ch in blob)
    if any("\u0590" <= ch <= "\u05ff" for ch in blob) and digits >= 6:
        return True
    if digits < 8:
        return False
    cues = (
        "republic",
        "licence",
        "license",
        "passport",
        "ident",
        "exp",
        "national",
        "dl",
        "mrz",
        "ausweis",
        "beschein",
    )
    if any(cue in lowered for cue in cues):
        return True
    short_nums = re.findall(r"\d{1,4}", blob)
    years = re.findall(r"(?:19|20)\d{2}", blob)
    return digits >= 12 and len(short_nums) >= 6 and (bool(years) or len(blob) >= 40)


def _compact_ocr(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _looks_like_passbook(text: str) -> bool:
    compact = _compact_ocr(text)
    if sum(1 for label in _PASSBOOK_LAYOUT_LABELS if label in compact) >= 2:
        return True
    return any(hint in compact for hint in ("儲金簿", "郵政存簿", "中華郵政", "郵局代號", "含檢號", "銀行存摺"))


def _looks_like_document(text: str) -> bool:
    blob = text or ""
    compact = _compact_ocr(blob)
    lowered = blob.lower()
    if _looks_like_passbook(blob):
        return True
    back_hits = sum(1 for label in _ID_BACK_LABELS if label in compact)
    if back_hits >= 2:
        return True
    if sum(1 for label in _ID_LAYOUT_LABELS if label in compact) >= 3:
        return True
    if any(hint.lower() in compact.lower() or hint.lower() in lowered for hint in _ID_FRONT_HINTS):
        return True
    if any(hint.lower() in lowered for hint in _CARD_HINTS):
        return True
    if any(hint.lower() in compact.lower() or hint.lower() in lowered for hint in _PASSPORT_HINTS):
        return True
    if any(hint.lower() in compact.lower() or hint.lower() in lowered for hint in _LICENSE_HINTS):
        return True
    return False


def _looks_like_body(text: str) -> bool:
    return _has_needle(text, _BODY_NEEDLES)


def _looks_like_violence(text: str) -> bool:
    return _has_needle(text, _VIOLENCE_NEEDLES)


def _looks_like_voyeur(text: str) -> bool:
    return _has_needle(text, _VOYEUR_NEEDLES)


def _looks_like_other(text: str) -> bool:
    return _has_needle(text, _OTHER_NEEDLES)


def _has_needle(text: str, needles: tuple[str, ...]) -> bool:
    raw = text or ""
    lowered = raw.lower()
    return any(needle in raw or needle.lower() in lowered for needle in needles)
