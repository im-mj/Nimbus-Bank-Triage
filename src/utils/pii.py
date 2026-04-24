"""
Nimbus Bank Triage — PII Redaction Utility

Regex-based detection and redaction of personally identifiable information.
Runs on both input (before LLMs) and output (before customer sees response).

Input scrubbing: aggressive — redact everything that looks like PII.
Output scrubbing: smart — skip known bank contact info from KB articles.
"""

import re


# ── Pattern Definitions ──────────────────────────────────────

# Credit/debit card: standard formats only
# - 4-4-4-4 (Visa/MC with separators)
# - 4-6-5 (Amex with separators)
# - 13-19 continuous digits (any card without separators)
_CARD_PATTERN = re.compile(
    r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{1,7}\b"   # separated: 4-4-4-X
    r"|\b\d{4}[-\s]\d{6}[-\s]\d{5}\b"                # separated: 4-6-5 (Amex)
    r"|\b\d{13,19}\b"                                  # continuous: 13-19 digits
)

# SSN: XXX-XX-XXXX or 9 consecutive digits near SSN-like context
_SSN_PATTERN = re.compile(
    r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
)

# US phone: various formats
_PHONE_PATTERN = re.compile(
    r"(?:\+?1[-.\s]?)?"               # optional country code
    r"(?:\(?\d{3}\)?[-.\s]?)"         # area code
    r"\d{3}[-.\s]?"                    # exchange
    r"\d{4}\b"                         # subscriber
)

# Email
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# Bank routing number: exactly 9 digits (when near banking context)
_ROUTING_PATTERN = re.compile(
    r"(?i)(?:routing|aba|transit)[\s\w#:]*?(\d{9})\b"
)

# Account number: 8-17 digits near account-related words
_ACCOUNT_PATTERN = re.compile(
    r"(?i)(?:account|acct|acnt)[\s#:]*(\d{8,17})\b"
)

# Dollar amounts above reporting threshold ($10,000+)
_LARGE_AMOUNT_PATTERN = re.compile(
    r"\$\s*\d{2,3}(?:,\d{3})+(?:\.\d{2})?"
)


# ── Whitelisted bank contact info (never redact in output) ───
# These appear in KB articles and should be in customer responses.
_BANK_WHITELIST = {
    # Phone numbers
    "1-800-646-2871",
    "800-646-2871",
    "1-800-NIMBUS-1",
    # Emails
    "fraud@nimbusbank.com",
    "support@nimbusbank.com",
    # Domains
    "nimbusbank.com",
}


# ── Ordered redaction rules ──────────────────────────────────
# Order matters: more specific patterns first to avoid partial matches.

_REDACTION_RULES: list[tuple[str, re.Pattern, str]] = [
    ("routing_number", _ROUTING_PATTERN,      "[ROUTING_REDACTED]"),
    ("account_number", _ACCOUNT_PATTERN,      "[ACCOUNT_REDACTED]"),
    ("ssn",            _SSN_PATTERN,          "[SSN_REDACTED]"),
    ("card_number",    _CARD_PATTERN,         "[CARD_REDACTED]"),
    ("email",          _EMAIL_PATTERN,        "[EMAIL_REDACTED]"),
    ("phone",          _PHONE_PATTERN,        "[PHONE_REDACTED]"),
]


def _mask_value(pii_type: str, value: str) -> str:
    """
    Create a partially masked version of a PII value for demo/audit logs.
    Shows enough to prove detection without exposing the full value.

    Examples:
        card_number: "4532-1234-5678-9012" → "4532-****-****-9012"
        phone:       "214-555-0198"        → "214-***-0198"
        email:       "john.doe@gmail.com"  → "j*****e@gmail.com"
        ssn:         "123-45-6789"         → "***-**-6789"
    """
    clean = value.strip()

    if pii_type == "card_number":
        digits = re.sub(r"[^0-9]", "", clean)
        if len(digits) >= 8:
            return digits[:4] + "-****-****-" + digits[-4:]
        return "****-****-****-****"

    elif pii_type == "ssn":
        digits = re.sub(r"[^0-9]", "", clean)
        if len(digits) >= 4:
            return "***-**-" + digits[-4:]
        return "***-**-****"

    elif pii_type == "phone":
        digits = re.sub(r"[^0-9]", "", clean)
        if len(digits) >= 7:
            return digits[:3] + "-***-" + digits[-4:]
        return "***-***-****"

    elif pii_type == "email":
        if "@" in clean:
            local, domain = clean.split("@", 1)
            if len(local) > 2:
                masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
            else:
                masked_local = "*" * len(local)
            return f"{masked_local}@{domain}"
        return "****@****.***"

    elif pii_type == "account_number":
        digits = re.sub(r"[^0-9]", "", clean)
        if len(digits) >= 4:
            return "****" + digits[-4:]
        return "********"

    elif pii_type == "routing_number":
        digits = re.sub(r"[^0-9]", "", clean)
        if len(digits) >= 4:
            return "*****" + digits[-4:]
        return "*********"

    return "****"


def redact_pii(text: str) -> tuple[str, list[str], list[str]]:
    """
    Scan text for PII patterns and replace with placeholder tags.

    Returns:
        (redacted_text, list_of_pii_types_found, list_of_masked_details)

    Example:
        >>> text = "My card is 4532-1234-5678-9012 and phone 214-555-0198"
        >>> redacted, flags, details = redact_pii(text)
        >>> # redacted = "My card is [CARD_REDACTED] and phone [PHONE_REDACTED]"
        >>> # flags = ["card_number", "phone"]
        >>> # details = ["card_number: 4532-****-****-9012", "phone: 214-***-0198"]
    """
    flags: list[str] = []
    details: list[str] = []
    redacted = text

    for pii_type, pattern, replacement in _REDACTION_RULES:
        matches = pattern.findall(redacted) if not pattern.groups else pattern.findall(redacted)
        # Also get the full match strings for masking
        full_matches = [m.group(0) for m in pattern.finditer(redacted)]

        if full_matches:
            # Build masked detail for each match
            for match_str in full_matches:
                masked = _mask_value(pii_type, match_str)
                detail = f"{pii_type}: {masked}"
                if detail not in details:
                    details.append(detail)

            # Perform the redaction
            redacted = pattern.sub(replacement, redacted)

            if pii_type not in flags:
                flags.append(pii_type)

    return redacted, flags, details


def contains_pii(text: str) -> bool:
    """Quick check: does the text contain any detectable PII?"""
    for _, pattern, _ in _REDACTION_RULES:
        if pattern.search(text):
            return True
    return False


def scrub_output(text: str) -> tuple[str, list[str], list[str]]:
    """
    Output-side PII scrub. Same pattern detection but SKIPS
    whitelisted bank contact info (phone numbers, emails from KB).

    Returns:
        (scrubbed_text, pii_types_found, masked_details)
    """
    # First, temporarily replace whitelisted values with placeholders
    # so the regex doesn't catch them
    protected = text
    replacements = []
    for i, safe_value in enumerate(_BANK_WHITELIST):
        placeholder = f"__BANK_SAFE_{i}__"
        if safe_value.lower() in protected.lower():
            # Case-insensitive replacement while preserving original case
            pattern = re.compile(re.escape(safe_value), re.IGNORECASE)
            original_matches = pattern.findall(protected)
            protected = pattern.sub(placeholder, protected)
            replacements.append((placeholder, original_matches[0] if original_matches else safe_value))

    # Run PII redaction on the protected text
    scrubbed, flags, details = redact_pii(protected)

    # Restore whitelisted values
    for placeholder, original in replacements:
        scrubbed = scrubbed.replace(placeholder, original)

    return scrubbed, flags, details
