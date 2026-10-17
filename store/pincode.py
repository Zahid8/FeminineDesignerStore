"""PIN code → district (city) and state, from India Post data (api.postalpincode.in).

Results are cached for 30 days; failures return None so the form simply stays
manual. The state is mapped onto our dropdown's spelling.
"""
import json
import logging
import re
import urllib.request

from django.core.cache import cache

from store.addresses import INDIAN_STATES, PINCODE_RE

logger = logging.getLogger(__name__)
ENDPOINT = "https://api.postalpincode.in/pincode/{pin}"
_NORMAL = {re.sub(r"[^a-z]", "", s.lower().replace("&", "and")): s for s in INDIAN_STATES}
_ALIASES = {"nctofdelhi": "Delhi", "orissa": "Odisha", "pondicherry": "Puducherry", "dadraandnagarhaveli": "Dadra and Nagar Haveli and Daman and Diu",
            "damananddiu": "Dadra and Nagar Haveli and Daman and Diu", "andamanandnicobar": "Andaman and Nicobar Islands"}


def match_state(name):
    key = re.sub(r"[^a-z]", "", (name or "").lower().replace("&", "and"))
    return _NORMAL.get(key) or _ALIASES.get(key) or ""


def lookup(pin):
    pin = re.sub(r"\D", "", pin or "")
    if not PINCODE_RE.match(pin):
        return None
    cache_key = f"femdes:pin:{pin}"
    hit = cache.get(cache_key)
    if hit is not None:
        return hit or None
    try:
        with urllib.request.urlopen(ENDPOINT.format(pin=pin), timeout=4) as resp:
            data = json.loads(resp.read() or b"[]")
    except Exception:
        logger.warning("PIN lookup failed for %s", pin, exc_info=True)
        return None  # don't cache outages
    first = data[0] if isinstance(data, list) and data else {}
    offices = first.get("PostOffice") or [] if str(first.get("Status", "")).lower() == "success" else []
    result = {}
    if offices:
        office = offices[0]
        result = {"city": office.get("District") or office.get("Block") or "", "state": match_state(office.get("State", "")),
                  "areas": sorted({o.get("Name", "") for o in offices if o.get("Name")})[:12]}
    cache.set(cache_key, result, 60 * 60 * 24 * 30)
    return result or None
