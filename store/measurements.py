"""Made-to-measure specification shared by forms, cart, orders and templates.

Values are stored in inches as strings (JSON-safe). Customers may enter in cm;
the form converts before validation.
"""
from decimal import ROUND_HALF_UP, Decimal

CM_PER_INCH = Decimal("2.54")

# key, label, required, (min, max) in inches, how-to hint
MEASUREMENTS = [
    ("length", "Length", True, (8, 40), "From the highest point of the shoulder straight down to where you want the hem."),
    ("chest", "Chest", True, (20, 70), "Around the fullest part of the bust, tape level and snug, not tight."),
    ("waist", "Waist", True, (18, 70), "Around the narrowest part of the waist, usually just above the navel."),
    ("armhole", "Armhole", True, (8, 30), "Around the shoulder joint, under the arm and back over the top."),
    ("opening", "Opening", True, (4, 30), "Around the arm where the sleeve will end."),
    ("bicep", "Bicep", True, (6, 30), "Around the fullest part of the upper arm."),
    ("sleeve_length", "Sleeve length", False, (0, 30), "From the shoulder seam to where the sleeve should end."),
    ("front_neck", "Front neck depth", False, (2, 20), "From the base of the neck down to the deepest point of the neckline."),
    ("back_neck", "Back neck depth", False, (2, 24), "From the nape down to the deepest point at the back."),
]
REQUIRED_KEYS = [m[0] for m in MEASUREMENTS if m[2]]
ALL_KEYS = [m[0] for m in MEASUREMENTS]
LABELS = {m[0]: m[1] for m in MEASUREMENTS}

SLEEVE_STYLES = [
    ("", "As shown in the photos"),
    ("sleeveless", "Sleeveless"),
    ("cap", "Cap sleeve"),
    ("short", "Short sleeve"),
    ("elbow", "Elbow length"),
    ("three_quarter", "Three-quarter"),
    ("full", "Full sleeve"),
]
SLEEVE_LABELS = dict(SLEEVE_STYLES)


def q(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def cm_to_in(value):
    return q(Decimal(value) / CM_PER_INCH)


def in_to_cm(value):
    return q(Decimal(value) * CM_PER_INCH)


def summary(custom):
    """[(label, value)] pairs for display, in spec order; values in inches."""
    if not custom:
        return []
    rows = []
    for key, label, _req, _rng, _hint in MEASUREMENTS:
        value = (custom.get("measurements") or {}).get(key)
        if value not in (None, ""):
            rows.append((label, f"{Decimal(value).normalize():f} in"))
    style = custom.get("sleeve_style")
    if style:
        rows.append(("Sleeves", SLEEVE_LABELS.get(style, style)))
    return rows


def fingerprint(custom):
    """Short stable hash so different measurement sets become separate cart lines."""
    import hashlib
    import json

    return hashlib.sha1(json.dumps(custom, sort_keys=True).encode()).hexdigest()[:10]
