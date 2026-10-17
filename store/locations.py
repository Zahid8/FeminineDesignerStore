"""Google Maps location links customers can add to their delivery details.

Customers usually paste a share link (maps.app.goo.gl/…) or a whole shared
message ("Home https://maps.app.goo.gl/…"); we pull out the first URL and
only accept Google Maps addresses so the link is safe to open for staff.
"""
import re
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError

MAX_LENGTH = 500
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
HELP = "Paste a Google Maps link, e.g. https://maps.app.goo.gl/… or https://www.google.com/maps/…"


def _is_google_maps(parts):
    host = (parts.hostname or "").lower()
    path = parts.path or ""
    if host in ("maps.app.goo.gl", "goo.gl") and (host == "maps.app.goo.gl" or path.startswith("/maps")):
        return True
    if re.fullmatch(r"maps\.google\.[a-z.]{2,8}", host):
        return True
    if re.fullmatch(r"(www\.)?google\.[a-z.]{2,8}", host) and path.startswith("/maps"):
        return True
    return False


def clean_maps_link(value):
    """Return a normalised https Google Maps URL, '' for empty input, or raise ValidationError."""
    text = (value or "").strip()
    if not text:
        return ""
    match = URL_RE.search(text)
    if not match:
        raise ValidationError(HELP)
    url = match.group(0).rstrip(".,);]")
    if url.lower().startswith("http://"):
        url = "https://" + url[7:]
    if len(url) > MAX_LENGTH:
        raise ValidationError("That link is too long. Please use Google Maps' Share → Copy link.")
    if not _is_google_maps(urlsplit(url)):
        raise ValidationError(HELP)
    return url


def maps_link_for_coordinates(lat, lng):
    return f"https://www.google.com/maps?q={float(lat):.6f},{float(lng):.6f}"
