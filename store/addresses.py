"""Indian postal address standard used at checkout and on customer profiles.

Address line 1 (house / flat / building), address line 2 (area / street /
landmark), city, state (dropdown), 6-digit PIN code and country. The parts are
also joined into one printable block (``compose``) for bills, emails and the
billing app.
"""
import re

from django.core.exceptions import ValidationError

COUNTRY = "India"

# States and union territories as listed by India Post.
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]
STATE_CHOICES = [("", "Select state")] + [(s, s) for s in INDIAN_STATES]

PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")
PHONE_RE = re.compile(r"^[6-9][0-9]{9}$")


def clean_pincode(value):
    digits = re.sub(r"\D", "", value or "")
    if not PINCODE_RE.match(digits):
        raise ValidationError("Enter a valid 6-digit PIN code.")
    return digits


def clean_indian_mobile(value):
    """Accept 98765 43210, +91 98765 43210 or 098765 43210; store as 10 digits."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not PHONE_RE.match(digits):
        raise ValidationError("Enter a valid 10-digit mobile number.")
    return digits


def compose(line1, line2="", city="", state="", pincode="", country=COUNTRY):
    """One printable address block, one part per line, empty parts skipped."""
    locality = ", ".join(p for p in (city, state) if p)
    if pincode:
        locality = f"{locality} {pincode}".strip()
    return "\n".join(p.strip() for p in (line1, line2, locality, country) if p and p.strip())
