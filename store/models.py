import re
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.urls import reverse
from django.utils import timezone as tz


class SiteSettings(models.Model):
    """One-row store identity, contact, social, and currency settings."""

    store_name = models.CharField(max_length=120, default="FemDes")
    logo = models.ImageField(upload_to="site/", blank=True, null=True)
    tagline = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    currency_code = models.CharField(max_length=3, default="USD")
    currency_symbol = models.CharField(max_length=8, default="$")

    # Payments
    upi_id = models.CharField(
        "UPI ID / number", max_length=80, default="+919898989898",
        help_text="Shown in manual UPI payment instructions.",
    )
    customization_advance_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("500.00"),
        help_text="Legacy: no longer shown to customers; payment is taken at checkout.",
    )
    customization_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Extra charge per made-to-measure piece (products can override).",
    )
    customization_terms = models.TextField(
        "Made-to-measure terms",
        default=(
            "Made-to-measure pieces are cut and stitched to the measurements you provide, "
            "so they cannot be exchanged for a different size. Our team will confirm your "
            "measurements with you before stitching begins, and we will contact you if "
            "anything needs clarifying."
        ),
        help_text="Shown in the customization builder, cart and order pages.",
    )
    customization_lead_time = models.CharField(
        max_length=60, default="3–4 weeks", help_text="Shown as the made-to-measure dispatch time.",
    )
    cod_enabled = models.BooleanField(
        "Cash on delivery available", default=False,
    )

    # Shipping
    shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Flat shipping charge per order. 0 = free shipping.",
    )
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Orders at or above this amount ship free. Blank = no threshold.",
    )

    # Announcement bar (top of every page); blank text hides it
    announcement_text = models.CharField(
        max_length=160, blank=True, default="Handcrafted designer blouses · made to your measurements",
    )
    announcement_url = models.CharField(max_length=255, blank=True, help_text="Optional link for the announcement.")

    # Product page copy
    price_note = models.CharField(
        max_length=120, blank=True,
        help_text='Shown under prices, e.g. "Inclusive of all taxes". Leave blank to hide.',
    )
    low_stock_threshold = models.PositiveSmallIntegerField(
        default=3, help_text='Show "Only N left" at or below this stock. 0 = off.',
    )
    returns_summary = models.TextField(
        blank=True, help_text="Short shipping & returns text for the product page tab.",
    )

    # Legal / compliance (Consumer Protection (E-Commerce) Rules, India)
    legal_name = models.CharField(max_length=160, blank=True)
    gstin = models.CharField("GSTIN", max_length=20, blank=True)
    grievance_officer_name = models.CharField(max_length=120, blank=True)
    grievance_officer_email = models.EmailField(blank=True)
    grievance_officer_phone = models.CharField(max_length=40, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.store_name

    def clean(self):
        super().clean()
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one SiteSettings row is allowed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Category(models.Model):
    """Active product grouping for storefront filters and homepage sections."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class ProductTag(models.Model):
    """Reusable product tag managed from Django admin."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Occasion(models.Model):
    """Shopping occasion (e.g. wedding, festive, everyday) used for filtering."""

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class SizeChart(models.Model):
    """Admin-managed size chart shown on product pages.

    A product uses its own chart, else its category's chart, else the default.
    """

    UNITS = [("in", "inches"), ("cm", "cm")]

    name = models.CharField(max_length=120)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="size_charts", help_text="Use this chart for products in this category.",
    )
    is_default = models.BooleanField(default=False, help_text="Fallback chart for products without one.")
    unit = models.CharField(max_length=2, choices=UNITS, default="in")
    notes = models.TextField(blank=True, help_text="How to measure, fit notes, etc.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def columns(self):
        """Measurement columns that have at least one value."""
        rows = list(self.rows.all())
        return [(field, label) for field, label in SizeChartRow.MEASUREMENTS
                if any(getattr(r, field) is not None for r in rows)]


class SizeChartRow(models.Model):
    MEASUREMENTS = [
        ("bust", "Bust"), ("under_bust", "Under bust"), ("waist", "Waist"),
        ("shoulder", "Shoulder"), ("armhole", "Armhole"), ("length", "Length"),
        ("sleeve_length", "Sleeve length"),
    ]

    chart = models.ForeignKey(SizeChart, on_delete=models.CASCADE, related_name="rows")
    size_label = models.CharField(max_length=20)
    bust = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    under_bust = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    waist = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    shoulder = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    armhole = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    length = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    sleeve_length = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.chart.name} — {self.size_label}"

    def values(self, columns):
        return [getattr(self, field) for field, _ in columns]


class Product(models.Model):
    """Sellable catalog item with prices, stock, flags, and discount-aware pricing."""

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    sku = models.CharField(max_length=80, unique=True, blank=True, null=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_new_arrival = models.BooleanField(default=False)
    is_best_seller = models.BooleanField(default=False)
    is_recommended = models.BooleanField(default=False)
    allow_discounts = models.BooleanField(default=True)
    color_options = models.TextField(blank=True)
    size_options = models.TextField(blank=True)
    # Merchandising attributes (filters + product page details)
    FULFILMENT_CHOICES = [
        ("ready_to_ship", "Ready to ship"),
        ("made_to_order", "Made to order"),
    ]
    fulfilment = models.CharField(max_length=20, choices=FULFILMENT_CHOICES, default="ready_to_ship")
    dispatch_note = models.CharField(
        max_length=120, blank=True,
        help_text='Shown on the product page, e.g. "Ships in 2–3 days" or "Made to order: 3 weeks".',
    )
    fabric = models.CharField(max_length=80, blank=True, help_text="e.g. Silk, Cotton, Georgette")
    care_instructions = models.TextField(blank=True)
    country_of_origin = models.CharField(max_length=60, default="India")
    occasions = models.ManyToManyField(Occasion, blank=True, related_name="products")
    pairs_with = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="paired_in",
        help_text='Shown as "Complete the look" on the product page.',
    )
    size_chart = models.ForeignKey(
        SizeChart, on_delete=models.SET_NULL, blank=True, null=True, related_name="products",
        help_text="Overrides the category/default size chart.",
    )
    allow_customization = models.BooleanField(
        "Made to measure available", default=True,
    )
    customization_fee = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Overrides the store-wide made-to-measure fee. Blank = store default.",
    )
    customization_lead_time = models.CharField(
        max_length=60, blank=True, help_text="Overrides the store-wide lead time, e.g. 2 weeks.",
    )
    # Blouse measurement defaults (admin-editable, optional)
    default_length = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, default=None
    )
    default_chest = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, default=None
    )
    default_waist = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, default=None
    )
    default_armhole = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, default=None
    )
    default_opening = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, default=None
    )
    default_bicep = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True, default=None
    )
    measurement_guide_image = models.ImageField(
        upload_to="measurement-guides/", blank=True, null=True
    )
    measurement_note = models.TextField(blank=True)
    tags = models.ManyToManyField(
        "ProductTag", blank=True, related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        """Return the primary image (is_primary=True), or first by sort_order, or None."""
        imgs = list(self.images.all())
        if not imgs:
            return None
        primary = [i for i in imgs if i.is_primary]
        return primary[0] if primary else imgs[0]

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    @property
    def secondary_image(self):
        """Return the first non-primary image by sort order (card hover), or None."""
        primary = self.primary_image
        for img in self.images.all():
            if primary is None or img.pk != primary.pk:
                return img
        return None

    @staticmethod
    def _split_options(raw):
        seen = []
        for part in re.split(r"[,\n]", raw or ""):
            part = part.strip()
            if part and part not in seen:
                seen.append(part)
        return seen

    @property
    def color_choices(self):
        """Admin-entered colour options (comma or newline separated)."""
        return self._split_options(self.color_options)

    @property
    def size_choices(self):
        """Admin-entered size options (comma or newline separated)."""
        return self._split_options(self.size_options)

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_on_sale(self):
        return self.compare_at_price is not None and self.compare_at_price > self.price

    def get_size_chart(self):
        if self.size_chart_id:
            return self.size_chart
        if self.category_id:
            chart = SizeChart.objects.filter(category_id=self.category_id).first()
            if chart:
                return chart
        return SizeChart.objects.filter(is_default=True).first()

    def custom_fee(self, site_settings=None):
        if self.customization_fee is not None:
            return self.customization_fee
        return getattr(site_settings, "customization_fee", None) or Decimal("0.00")

    def custom_lead_time(self, site_settings=None):
        return self.customization_lead_time or getattr(site_settings, "customization_lead_time", "") or "3–4 weeks"

    def low_stock_count(self, threshold):
        """Units left when at or below `threshold` (and in stock), else None."""
        if threshold and 0 < self.stock_quantity <= threshold:
            return self.stock_quantity
        return None

    def active_tags(self):
        return self.tags.filter(is_active=True)

    def save(self, *args, **kwargs):
        # Normalize blank SKU to NULL so unique constraint allows multiple blanks.
        if self.sku == "":
            self.sku = None
        super().save(*args, **kwargs)

    def clean(self):
        # Normalize blank SKU to NULL before uniqueness validation.
        if self.sku == "":
            self.sku = None
        super().clean()
        if (
            self.compare_at_price is not None
            and self.compare_at_price < self.price
        ):
            raise ValidationError(
                {"compare_at_price": "Compare-at price must be >= price."}
            )
        # Measurement defaults must be positive if provided (blank = skip)
        for field in [
            "default_length", "default_chest", "default_waist",
            "default_armhole", "default_opening", "default_bicep",
        ]:
            val = getattr(self, field, None)
            if val is not None and val <= Decimal("0"):
                raise ValidationError(
                    {field: "Measurement must be positive if provided."}
                )

    def get_effective_price(self, now=None):
        """Return the discounted price as a 2-decimal Decimal.

        Returns the product price when allow_discounts is False or no
        active applicable discount exists.  Picks the first active
        applicable discount ordered by highest priority then lowest id.
        Searches product-scoped, category-scoped, and global discounts.
        """
        price = self.price
        if not self.allow_discounts:
            return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if now is None:
            now = tz.now()

        # Collect applicable discounts: product, category, and global.
        discounts = list(
            Discount.objects.filter(
                models.Q(scope="global")
                | models.Q(scope="category", category=self.category)
                | models.Q(scope="product", product=self),
                is_active=True,
            )
            .order_by("-priority", "id")
        )

        # Filter to those that are current.
        applicable = [d for d in discounts if d.is_current(now)]
        if not applicable:
            return price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return applicable[0].apply_to_price(price)


class ProductImage(models.Model):
    """One or more uploaded images for each product."""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=160, blank=True)
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Discount(models.Model):
    """Active discount rules for global, category, or product scopes."""

    DISCOUNT_TYPES = [
        ("percent", "Percent"),
        ("fixed", "Fixed"),
    ]
    SCOPES = [
        ("global", "Global"),
        ("category", "Category"),
        ("product", "Product"),
    ]

    name = models.CharField(max_length=120)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    scope = models.CharField(max_length=20, choices=SCOPES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="discounts",
        blank=True,
        null=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="discounts",
        blank=True,
        null=True,
    )
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # Value must be positive
        if self.value is not None and self.value <= 0:
            raise ValidationError(
                {"value": "Discount value must be greater than zero."}
            )

        # Percent discounts cannot exceed 100
        if self.discount_type == "percent" and self.value > 100:
            raise ValidationError(
                {"value": "Percent discount cannot exceed 100%."}
            )

        # ends_at must be after starts_at
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError(
                {"ends_at": "End date must be after start date."}
            )

        # Scope consistency
        if self.scope == "global":
            if self.category_id or self.product_id:
                raise ValidationError(
                    "Global discounts must not have a category or product."
                )
        elif self.scope == "category":
            if not self.category_id:
                raise ValidationError(
                    {"category": "Category discount requires a category."}
                )
            if self.product_id:
                raise ValidationError(
                    {"product": "Category discount must not have a product."}
                )
        elif self.scope == "product":
            if not self.product_id:
                raise ValidationError(
                    {"product": "Product discount requires a product."}
                )
            if self.category_id:
                raise ValidationError(
                    {"category": "Product discount must not have a category."}
                )

    def is_current(self, now=None):
        """Return True if the discount is active and within its date range."""
        if not self.is_active:
            return False
        if now is None:
            now = tz.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def applies_to_product(self, product):
        """Return True if this discount should apply to the given product."""
        if not self.is_current():
            return False
        if self.scope == "global":
            return True
        if self.scope == "category":
            return product.category_id == self.category_id
        if self.scope == "product":
            return product.pk == self.product_id
        return False

    def apply_to_price(self, price):
        """Apply this discount to a price, returning a 2-decimal Decimal.

        Never returns less than Decimal("0.00").
        """
        price = Decimal(str(price))
        if self.discount_type == "percent":
            discount_amount = price * self.value / Decimal("100")
        else:
            discount_amount = self.value

        result = price - discount_amount
        result = result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return max(result, Decimal("0.00"))


class HomeBanner(models.Model):
    """Full-bleed homepage hero slide managed by staff in Django admin."""

    TEXT_THEMES = [
        ("light", "Light text (for dark photos)"),
        ("dark", "Dark text (for light photos)"),
    ]
    PLACEMENTS = [
        ("hero", "Hero slideshow"),
        ("promo", "Promotion band (mid page)"),
    ]

    placement = models.CharField(max_length=10, choices=PLACEMENTS, default="hero")
    image = models.ImageField(upload_to="banners/")
    mobile_image = models.ImageField(
        upload_to="banners/", blank=True, null=True,
        help_text="Optional portrait crop shown on phones.",
    )
    eyebrow = models.CharField(max_length=80, blank=True)
    title = models.CharField(max_length=140)
    subtitle = models.CharField(max_length=255, blank=True)
    cta_label = models.CharField(max_length=40, default="Shop Now")
    cta_url = models.CharField(
        max_length=255, blank=True,
        help_text="Site path or full URL. Leave blank to link to the shop.",
    )
    text_theme = models.CharField(max_length=10, choices=TEXT_THEMES, default="light")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title


class NewsletterSubscriber(models.Model):
    """Captured newsletter signups."""

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class Order(models.Model):
    """Manual fulfillment checkout record."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    order_number = models.CharField(max_length=32, unique=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    customer_name = models.CharField(max_length=160)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=40, blank=True)
    shipping_address = models.TextField()
    notes = models.TextField(blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("awaiting_review", "Awaiting Review"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("manual_upi", "Manual UPI"),
            ("razorpay", "Razorpay"),
            ("cash_on_delivery", "Cash on Delivery"),
        ],
        default="manual_upi",
    )
    payment_reference = models.CharField(max_length=160, blank=True)
    payment_notes = models.TextField(blank=True)
    gateway_order_id = models.CharField(max_length=100, blank=True)
    gateway_payment_id = models.CharField(max_length=100, blank=True)
    gateway_signature = models.CharField(max_length=500, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    customer_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="orders",
    )
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    discount_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    shipping_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.order_number or f"Order #{self.pk}"

    def save(self, *args, **kwargs):
        # Auto-set paid_at when payment_status changes to paid.
        transitioning_to_paid = self.payment_status == "paid"
        if self.pk:
            old = Order.objects.filter(pk=self.pk).first()
            if old and old.payment_status == "paid":
                transitioning_to_paid = False
        if transitioning_to_paid and self.paid_at is None:
            self.paid_at = tz.now()
        if not self.order_number:
            self.order_number = self._generate_order_number()
            for _ in range(10):
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    return
                except IntegrityError:
                    self.order_number = self._generate_order_number()
            raise ValidationError(
                "Could not generate a unique order number after 10 attempts."
            )
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        """Generate a unique order number: FD-YYYYMMDD-XXXXXX."""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:6].upper()
        return f"FD-{today}-{suffix}"


class OrderItem(models.Model):
    """Immutable product line snapshot for orders."""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    product_name = models.CharField(max_length=160)
    sku = models.CharField(max_length=80, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    color = models.CharField(max_length=80, blank=True)
    size = models.CharField(max_length=80, blank=True)
    # Made-to-measure snapshot: {"measurements": {...inches}, "sleeve_style": "", "notes": ""}
    customization = models.JSONField(blank=True, null=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="order_items",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class CustomizationRequest(models.Model):
    """Blouse customization request with measurements and shareable token."""

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="customization_requests"
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=160)
    customer_phone = models.CharField(max_length=40)
    length = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    chest = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    waist = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    armhole = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    opening = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    bicep = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    sleeve_style = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    details = models.JSONField(blank=True, null=True, help_text="Optional measurements (inches).")
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("awaiting_review", "Awaiting Review"),
            ("paid", "Paid"),
            ("failed", "Failed"),
            ("refunded", "Refunded"),
        ],
        default="pending",
    )
    payment_reference = models.CharField(max_length=160, blank=True)
    payment_notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def reference(self):
        return "FIT-" + str(self.token).split("-")[0].upper()

    def as_custom(self):
        measurements = {k: f"{getattr(self, k):.2f}" for k in ("length", "chest", "waist", "armhole", "opening", "bicep")}
        measurements.update({k: v for k, v in (self.details or {}).items()})
        return {"measurements": measurements, "sleeve_style": self.sleeve_style, "notes": self.notes}

    def summary_rows(self):
        from store import measurements as mspec

        return mspec.summary(self.as_custom())

    def save(self, *args, **kwargs):
        transitioning_to_paid = self.payment_status == "paid"
        if self.pk:
            old = CustomizationRequest.objects.filter(pk=self.pk).first()
            if old and old.payment_status == "paid":
                transitioning_to_paid = False
        if transitioning_to_paid and self.paid_at is None:
            self.paid_at = tz.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Customization for {self.customer_name} ({self.product.name})"


class CustomerProfile(models.Model):
    """Extended profile for registered customers."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField(max_length=40, blank=True, null=True)
    # Verified number in E.164 form, used for OTP login (one account per number).
    phone_e164 = models.CharField(max_length=20, unique=True, blank=True, null=True)
    phone_verified_at = models.DateTimeField(blank=True, null=True)
    saved_measurements = models.JSONField(blank=True, null=True, help_text="Last measurements used, in inches.")
    shipping_address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(
        upload_to="profiles/", blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user.username}"


class PhoneOTP(models.Model):
    """A hashed one-time password sent by SMS for phone login/verification."""

    phone = models.CharField(max_length=20, db_index=True)  # E.164
    code_hash = models.CharField(max_length=64)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "phone OTP"

    def __str__(self):
        return f"OTP for {self.phone} at {self.created_at:%Y-%m-%d %H:%M}"


class Feedback(models.Model):
    """Customer contact/feedback messages."""

    name = models.CharField(max_length=160)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback from {self.name}: {self.subject}"


class WishlistItem(models.Model):
    """A product saved by a signed-in customer (guests use the session)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_wishlist_item")]

    def __str__(self):
        return f"{self.user} ♥ {self.product}"


class StockAlert(models.Model):
    """'Notify me when back in stock' request for an out-of-stock product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_alerts")
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "email"], condition=models.Q(notified_at__isnull=True),
                name="unique_pending_stock_alert",
            )
        ]

    def __str__(self):
        return f"{self.email} → {self.product}"


class Page(models.Model):
    """Admin-managed content page (shipping, returns, privacy, terms, about...)."""

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    body = models.TextField(help_text="Plain text. Blank lines start new paragraphs.")
    show_in_footer = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("page_detail", kwargs={"slug": self.slug})


class FAQ(models.Model):
    group = models.CharField(max_length=80, blank=True, help_text='e.g. "Orders", "Sizing", "Shipping"')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group", "sort_order", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class ClientDiary(models.Model):
    """A customer (or celebrity) photographed in a FemDes piece."""

    name = models.CharField(max_length=120)
    image = models.ImageField(upload_to="client-diaries/")
    caption = models.CharField(max_length=255, blank=True)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, related_name="client_diaries")
    is_published = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name_plural = "client diaries"

    def __str__(self):
        return self.name


class Appointment(models.Model):
    """Styling / fitting consultation request."""

    TOPICS = [
        ("size_fit", "Size & fit consultation"),
        ("made_to_measure", "Made-to-measure order"),
        ("styling", "Occasion styling"),
        ("product", "Product guidance"),
    ]
    MODES = [
        ("video", "Video call"),
        ("whatsapp", "WhatsApp call"),
        ("in_store", "Visit the studio"),
    ]
    SLOTS = [("morning", "Morning (10–1)"), ("afternoon", "Afternoon (1–4)"), ("evening", "Evening (4–7)")]
    STATUSES = [("new", "New"), ("confirmed", "Confirmed"), ("completed", "Completed"), ("cancelled", "Cancelled")]

    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    topic = models.CharField(max_length=20, choices=TOPICS, default="size_fit")
    mode = models.CharField(max_length=20, choices=MODES, default="video")
    preferred_date = models.DateField()
    preferred_slot = models.CharField(max_length=20, choices=SLOTS, default="morning")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, related_name="appointments")
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="new")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.get_topic_display()} on {self.preferred_date}"
