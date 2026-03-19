"""Auto-categorization service for expenses.

Rule-based merchant→category mapping with optional LLM fallback.
"""

from __future__ import annotations

import re
from typing import Any

from brokebutthriving.models.entities import ExpenseCategory

# ---------------------------------------------------------------------------
# Rule-based merchant-to-category mapping
# ---------------------------------------------------------------------------

_MERCHANT_RULES: list[tuple[re.Pattern[str], ExpenseCategory]] = [
    # Food
    (re.compile(r"zomato|swiggy|uber\s*eats|domino|pizza|mcdonald|kfc|burger|biryani|chai|tea|coffee|starbucks|cafe|canteen|mess|dhaba|restaurant|food", re.I), ExpenseCategory.FOOD),
    # Transport
    (re.compile(r"uber|ola|rapido|metro|bus|train|irctc|petrol|diesel|fuel|parking|toll|cab|auto|rickshaw", re.I), ExpenseCategory.TRANSPORT),
    # Entertainment
    (re.compile(r"netflix|hotstar|prime\s*video|spotify|apple\s*music|youtube|cinema|movie|pvr|inox|game|steam|play\s*store|concert", re.I), ExpenseCategory.ENTERTAINMENT),
    # Shopping
    (re.compile(r"amazon|flipkart|myntra|ajio|meesho|nykaa|shoppers|mall|cloth|shoe|fashion|reliance\s*digital|croma|electronics", re.I), ExpenseCategory.SHOPPING),
    # Education
    (re.compile(r"college|university|tuition|book|notebook|pen|stationery|course|udemy|coursera|exam|fees|library", re.I), ExpenseCategory.EDUCATION),
    # Health
    (re.compile(r"pharmacy|medical|doctor|hospital|clinic|medicine|apollo|1mg|pharmeasy|netmeds|gym|fitness", re.I), ExpenseCategory.HEALTH),
    # Utilities
    (re.compile(r"electricity|electric|water|gas|broadband|wifi|internet|jio|airtel|vi\b|bsnl|recharge|phone\s*bill|rent", re.I), ExpenseCategory.UTILITIES),
    # Subscription
    (re.compile(r"subscription|premium|membership|renewal|plan|monthly\s*plan", re.I), ExpenseCategory.SUBSCRIPTION),
    # Travel
    (re.compile(r"hotel|hostel|airbnb|oyo|makemytrip|goibibo|flight|airport|travel|trip|vacation|booking", re.I), ExpenseCategory.TRAVEL),
]


def auto_categorize(merchant: str | None = None, note: str | None = None) -> ExpenseCategory:
    """Categorize an expense based on merchant name and/or note text.

    Returns the best matching category, or OTHER if no match found.
    """
    text = " ".join(filter(None, [merchant, note])).strip()
    if not text:
        return ExpenseCategory.OTHER

    for pattern, category in _MERCHANT_RULES:
        if pattern.search(text):
            return category

    return ExpenseCategory.OTHER


# ---------------------------------------------------------------------------
# SMS parser for Indian bank transaction messages
# ---------------------------------------------------------------------------

_SMS_AMOUNT_PATTERN = re.compile(
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{1,2})?)", re.I
)
_SMS_MERCHANT_PATTERN = re.compile(
    r"(?:at|to|for|@)\s+([A-Za-z0-9\s&\-\.]+?)(?:\s+on|\s+ref|\s*$)", re.I
)
_SMS_DATE_PATTERN = re.compile(
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.I
)
_SMS_DEBIT_PATTERN = re.compile(
    r"debited|spent|paid|withdrawn|purchase|deducted|sent", re.I
)


def parse_sms_messages(sms_text: str) -> list[dict[str, Any]]:
    """Parse Indian bank SMS messages and extract expense-like transactions.

    Returns a list of dicts with keys: amount, merchant, category, note, date_str.
    """
    results: list[dict[str, Any]] = []
    lines = [line.strip() for line in sms_text.split("\n") if line.strip()]

    for line in lines:
        if not _SMS_DEBIT_PATTERN.search(line):
            continue

        amount_match = _SMS_AMOUNT_PATTERN.search(line)
        if not amount_match:
            continue

        amount = float(amount_match.group(1).replace(",", ""))
        if amount <= 0:
            continue

        merchant = None
        merchant_match = _SMS_MERCHANT_PATTERN.search(line)
        if merchant_match:
            merchant = merchant_match.group(1).strip()[:120]

        date_str = None
        date_match = _SMS_DATE_PATTERN.search(line)
        if date_match:
            date_str = date_match.group(1)

        category = auto_categorize(merchant, line)

        results.append({
            "amount": amount,
            "merchant": merchant,
            "category": category.value,
            "note": line[:240],
            "date_str": date_str,
        })

    return results
