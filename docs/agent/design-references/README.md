# Design references (T29)

Montages captured 2026-10-17 with Playwright (1440×900, three scroll positions
each) from public homepages, used only as design inspiration for the FemDes
storefront. No copy, imagery or code was taken from these sites.

| File | Site | What FemDes adopted |
|------|------|---------------------|
| `sabyasachi_m.jpg` | sabyasachi.com | Full-bleed photographic hero with a single tracked label and one outlined CTA; centred wordmark; tracked uppercase nav. |
| `anitadongre_m.jpg` | anitadongre.com | Centred section titles with a short italic serif subtitle ("A silhouette for every occasion"); portrait category tiles with name below. |
| `rawmango_m.jpg` | rawmango.com | Edge-to-edge image sections with minimal chrome; a thin utility row above the logo; restraint in colour. |
| `masaba_m.jpg` | houseofmasaba.com | Thin announcement bar; portrait product tiles with centred name/price; editorial "for every occasion" copy block beside imagery. |
| `zimmermann_m.jpg` | zimmermann.com | Two-tier header (utility row + centred logo + centred nav); hairline rules; square corners. |
| `toteme_m.jpg` | toteme.com | Hairline dividers, near-monochrome palette, large whitespace, product names in small tracked type. |
| `torani_m.jpg`, `plp2.jpg` | torani.in | PLP toolbar (count, sort, grid density); PDP buy panel: size/colour chips, outlined Add to Cart, filled Buy Now, green outlined "Order on WhatsApp"; floating WhatsApp button. |

Sites that could not be captured (bot protection / maintenance) and were not
used: sezane.com, aesop.com, jacquemus.com.

Frameworks used to implement these patterns: Bootstrap 5.3.8 (layout and
offcanvas), Swiper 11 (hero and product carousels), GSAP 3.15 + ScrollTrigger
(reveals, parallax, hero text), Lenis (smooth scrolling) and Alpine.js 3
(mega menu, sort/density toolbar state). All loaded from jsDelivr with SRI.
