from __future__ import annotations

from safety_gateway.pii.image_forbid import classify_forbidden_image, extra_forbid_entities
from safety_gateway.pii.image_policy import classify_image_share


def test_id_back_layout_is_a_document() -> None:
    text = "父 陳德明 母 吳春美 配偶 金大昇 役別 / 出生地 臺北市 住址 臺北市內湖區"
    assert classify_forbidden_image(text, []) == "document"
    assert "TW_ID" in extra_forbid_entities(text)


def test_taiwan_health_and_residence_cards() -> None:
    assert classify_forbidden_image("全民健康保險 健保卡 姓名 測試", []) == "document"
    assert classify_forbidden_image("外僑居留證 居留證號碼", []) == "document"
    assert classify_forbidden_image("自然人憑證 晶片", []) == "document"
    assert classify_forbidden_image("戶口名簿 戶號", []) == "document"
    assert classify_forbidden_image("公路總局 汽機車駕駛執照 普通重型機車", []) == "document"
    assert classify_forbidden_image("中華民國護照 普通護照", []) == "document"
    assert classify_forbidden_image("姓名 測試 出生 民國 發證 內湖", []) == "document"


def test_postal_passbook_is_blocked_as_document() -> None:
    text = "郵政 存簿 儲金簿 局號 700 帳號 0311248 0287828 戶 名 黃沛嫿 郵 局 板橋三民路郵局 電話 02-29518120"
    assert classify_forbidden_image(text, ["PERSON", "PHONE_NUMBER"]) == "document"
    assert extra_forbid_entities(text) & {"IMAGE_DOCUMENT", "TW_BANK_ACCOUNT"}


def test_blurry_foreign_form_is_document() -> None:
    text = "CAALLLLUCILL 8 71 0 AI 39 021 3 9 65 CAGLLLAIl OCLLL 1964"
    assert extra_forbid_entities(text) & {"IMAGE_DOCUMENT", "TW_ID"}


def test_id_front_layout_is_a_document() -> None:
    assert classify_forbidden_image("中華民國國民身分證 身分證字號 A123456789", []) == "document"


def test_ocr_keywords_map_to_why_list() -> None:
    assert classify_forbidden_image("這是裸照", []) == "body"
    assert classify_forbidden_image("超血腥屍體特寫", []) == "violence"
    assert classify_forbidden_image("更衣室偷拍", []) == "voyeur"
    assert classify_forbidden_image("色情網站截圖", []) == "other"


def test_driver_license_is_document_not_violence() -> None:
    text = "REPUBLIC OF THE PHILIPPINES DEPARTMENT OF TRANSPORTATION LAND TRANSPORTATION OFFICE DRIVER LICENSE BLOOD TYPE O"
    assert classify_forbidden_image(text, []) == "document"


def test_person_only_is_not_forbidden() -> None:
    blocked, reason = classify_image_share(0.1, ["PERSON"], ocr_text="同學的作業")
    assert blocked is False
    assert reason is None
