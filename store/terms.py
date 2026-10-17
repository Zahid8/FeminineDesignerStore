"""Terms printed on online-order bills.

Keep in sync with the billing app (src/lib/constants/business.ts, ONLINE_ORDER_TERMS)
so the shop's bill page and the billing app's PDF say the same thing.
"""

ONLINE_ORDER_TERMS = [
    "This bill is for an order placed on our online store. Prices include applicable taxes.",
    "Ready-made pieces are dispatched within the time shown on the product page. Made-to-measure pieces are stitched after we confirm your measurements and payment; the lead time given is an estimate.",
    "Please check your parcel when it arrives and tell us within 48 hours, with photos, if anything is damaged, missing or not as ordered.",
    "Ready-made pieces can be exchanged within 7 days of delivery if they are unworn, unwashed and have their tags attached.",
    "Made-to-measure pieces are cut and stitched to the measurements you provide, so they cannot be returned or exchanged for a different size. If a piece does not match those measurements, we will alter it free of charge.",
    "Orders can be cancelled before dispatch (ready-made) or before stitching begins (made to measure). Refunds are made to the original payment method.",
    "For help with your order, contact us on WhatsApp or by email and mention your order number.",
]
