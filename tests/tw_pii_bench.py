"""Map tw-PII-bench gold labels to this gateway's entity types."""

from __future__ import annotations

GOLD_TO_OURS: dict[str, frozenset[str]] = {
    "private_person": frozenset({"PERSON"}),
    "private_phone": frozenset({"PHONE_NUMBER"}),
    "private_email": frozenset({"EMAIL_ADDRESS", "EMAIL"}),
    "private_address": frozenset({"LOCATION"}),
    "private_date": frozenset({"DATE_TIME"}),
    "private_url": frozenset({"URL"}),
    "account_number": frozenset({"TW_BANK_ACCOUNT", "CREDIT_CARD", "STUDENT_ID", "TW_ID"}),
    "tw_national_id": frozenset({"TW_ID"}),
    "tw_passport": frozenset({"TW_PASSPORT"}),
    "tw_driver_license": frozenset({"TW_DRIVER_LICENSE"}),
    "tw_household_no": frozenset({"TW_HOUSEHOLD_NO", "TW_BANK_ACCOUNT", "STUDENT_ID"}),
}

# Types this product actually aims to catch in child chat.
CORE_GOLD = frozenset(
    {
        "private_person",
        "private_phone",
        "private_email",
        "private_address",
        "tw_national_id",
    }
)
