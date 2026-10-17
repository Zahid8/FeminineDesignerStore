"""Phone number normalisation for OTP login.

Countries are described in COUNTRIES; only those listed in
settings.PHONE_LOGIN_COUNTRIES are offered to customers. To support a new
country, add a PhoneCountry entry (ISO code, dial code, national-number regex)
and enable it in settings — no other code changes are needed.
"""
import re
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class PhoneCountry:
    code: str            # ISO 3166-1 alpha-2, e.g. "IN"
    name: str
    dial_code: str       # without "+", e.g. "91"
    national_pattern: str  # regex for the national significant number
    example: str
    trunk_prefix: str = ""  # domestic prefix dropped before validation, e.g. "0"

    def matches(self, national):
        return re.fullmatch(self.national_pattern, national) is not None


COUNTRIES = {
    # Indian mobile numbers: 10 digits starting 6–9 (TRAI numbering plan).
    "IN": PhoneCountry("IN", "India", "91", r"[6-9]\d{9}", "98765 43210", trunk_prefix="0"),
    # Examples of how to extend (disabled until listed in PHONE_LOGIN_COUNTRIES):
    "AE": PhoneCountry("AE", "United Arab Emirates", "971", r"5\d{8}", "50 123 4567", trunk_prefix="0"),
    "GB": PhoneCountry("GB", "United Kingdom", "44", r"7\d{9}", "7400 123456", trunk_prefix="0"),
    "US": PhoneCountry("US", "United States", "1", r"[2-9]\d{2}[2-9]\d{6}", "201 555 0123"),
}


class InvalidPhoneNumber(ValueError):
    pass


def enabled_countries():
    codes = getattr(settings, "PHONE_LOGIN_COUNTRIES", ["IN"])
    return [COUNTRIES[c] for c in codes if c in COUNTRIES]


def get_country(code):
    for country in enabled_countries():
        if country.code == code:
            return country
    raise InvalidPhoneNumber("Phone login is not available for this country yet.")


def normalize(country_code, raw):
    """Return the E.164 form (e.g. "+919876543210") or raise InvalidPhoneNumber."""
    country = get_country(country_code)
    digits = re.sub(r"\D", "", raw or "")
    had_plus = (raw or "").strip().startswith("+")
    if had_plus or (digits.startswith(country.dial_code) and len(digits) > len(country.dial_code) + 6):
        if not digits.startswith(country.dial_code):
            raise InvalidPhoneNumber(f"Please enter a {country.name} number (+{country.dial_code}).")
        digits = digits[len(country.dial_code):]
    if country.trunk_prefix and digits.startswith(country.trunk_prefix):
        digits = digits[len(country.trunk_prefix):]
    if not country.matches(digits):
        raise InvalidPhoneNumber(f"Enter a valid {country.name} mobile number, e.g. {country.example}.")
    return f"+{country.dial_code}{digits}"


def mask(e164):
    """+919876543210 -> +91 ******3210"""
    for country in COUNTRIES.values():
        prefix = "+" + country.dial_code
        if e164.startswith(prefix):
            rest = e164[len(prefix):]
            return f"{prefix} {'*' * max(len(rest) - 4, 0)}{rest[-4:]}"
    return e164[:3] + "*" * max(len(e164) - 7, 0) + e164[-4:]
