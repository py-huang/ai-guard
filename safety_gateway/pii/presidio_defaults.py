"""Presidio's English predefined recognizers, registered for zh so they run on child chat."""

from __future__ import annotations

from collections.abc import Callable

from presidio_analyzer import EntityRecognizer
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    CryptoRecognizer,
    DateRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    IpRecognizer,
    MacAddressRecognizer,
    PhoneRecognizer,
    UrlRecognizer,
    UsBankRecognizer,
    UsItinRecognizer,
    UsLicenseRecognizer,
    UsPassportRecognizer,
    UsSsnRecognizer,
)

# Generic types work the same in a 繁中句子裡（email、卡號、網址）。
# US-specific types stay as US_*; Taiwan analogues live in recognizers.py.
_ZH_CONTEXT = {
    "EMAIL_ADDRESS": ["email", "e-mail", "信箱", "電子郵件", "電子信箱"],
    "CREDIT_CARD": [
        "credit",
        "card",
        "visa",
        "mastercard",
        "信用卡",
        "卡號",
        "簽帳",
        "visa卡",
    ],
    "URL": ["url", "http", "網址", "網站", "連結"],
    "IP_ADDRESS": ["ip", "ip位址"],
    "CRYPTO": ["bitcoin", "wallet", "錢包", "比特幣"],
    "DATE_TIME": ["date", "birthday", "生日", "日期"],
    "US_SSN": ["ssn", "social", "社會安全號碼", "社會安全碼"],
    "US_PASSPORT": ["passport", "美國護照"],
    "US_DRIVER_LICENSE": ["driver", "license", "美國駕照"],
    "US_BANK_NUMBER": ["routing", "美國銀行帳號"],
}


def build_predefined_recognizers_for_zh() -> list[EntityRecognizer]:
    """Clone Presidio's default pattern recognizers onto language=zh.

    SpacyRecognizer 由 analyzer 在 zh_core_web_md 可用時另外掛上（只留 PERSON）。
    """
    builders: list[Callable[[], EntityRecognizer]] = [
        lambda: EmailRecognizer(
            supported_language="zh",
            context=_ZH_CONTEXT["EMAIL_ADDRESS"],
            name="EmailRecognizer_zh",
        ),
        lambda: CreditCardRecognizer(
            supported_language="zh",
            context=_ZH_CONTEXT["CREDIT_CARD"],
            name="CreditCardRecognizer_zh",
        ),
        lambda: UrlRecognizer(
            supported_language="zh",
            context=_ZH_CONTEXT["URL"],
            name="UrlRecognizer_zh",
        ),
        lambda: IpRecognizer(supported_language="zh", name="IpRecognizer_zh"),
        lambda: MacAddressRecognizer(supported_language="zh", name="MacAddressRecognizer_zh"),
        lambda: CryptoRecognizer(
            supported_language="zh",
            context=_ZH_CONTEXT["CRYPTO"],
            name="CryptoRecognizer_zh",
        ),
        lambda: IbanRecognizer(supported_language="zh", name="IbanRecognizer_zh"),
        lambda: DateRecognizer(
            supported_language="zh",
            context=_ZH_CONTEXT["DATE_TIME"],
            name="DateRecognizer_zh",
        ),
        lambda: PhoneRecognizer(
            supported_language="zh",
            supported_regions=("US", "GB", "TW"),
            name="PhoneRecognizer_zh",
        ),
        lambda: UsSsnRecognizer(
            supported_language="zh",
            context=_ZH_CONTEXT["US_SSN"],
            name="UsSsnRecognizer_zh",
        ),
        lambda: UsPassportRecognizer(supported_language="zh", name="UsPassportRecognizer_zh"),
        lambda: UsLicenseRecognizer(supported_language="zh", name="UsLicenseRecognizer_zh"),
        lambda: UsBankRecognizer(supported_language="zh", name="UsBankRecognizer_zh"),
        lambda: UsItinRecognizer(supported_language="zh", name="UsItinRecognizer_zh"),
    ]
    return [build() for build in builders]
