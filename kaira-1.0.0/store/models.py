import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone as tz


class SiteSettings(models.Model):
    """One-row store identity, contact, social, and currency settings."""

    store_name = models.CharField(max_length=120, default="FemDes")
    tagline = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True)
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    currency_code = models.CharField(max_length=3, default="USD")
    currency_symbol = models.CharField(max_length=8, default="$")
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


class Product(models.Model):
    """Sellable catalog item with prices, stock, flags, and discount-aware pricing."""

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    sku = models.CharField(max_length=80, unique=True)
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
    # Blouse measurement defaults (admin-editable, positive only)
    default_length = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("10.00")
    )
    default_chest = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("10.00")
    )
    default_waist = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("10.00")
    )
    default_armhole = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("10.00")
    )
    default_opening = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("10.00")
    )
    default_bicep = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("10.00")
    )
    measurement_guide_image = models.ImageField(
        upload_to="measurement-guides/", blank=True, null=True
    )
    tags = models.ManyToManyField(
        "ProductTag", blank=True, related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    def active_tags(self):
        return self.tags.filter(is_active=True)

    def clean(self):
        super().clean()
        if (
            self.compare_at_price is not None
            and self.compare_at_price < self.price
        ):
            raise ValidationError(
                {"compare_at_price": "Compare-at price must be >= price."}
            )
        # Measurement defaults must be positive
        for field in [
            "default_length", "default_chest", "default_waist",
            "default_armhole", "default_opening", "default_bicep",
        ]:
            val = getattr(self, field, None)
            if val is not None and val <= 0:
                raise ValidationError(
                    {field: "Measurement default must be positive."}
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
            ("cash_on_delivery", "Cash on Delivery"),
        ],
        default="manual_upi",
    )
    payment_reference = models.CharField(max_length=160, blank=True)
    payment_notes = models.TextField(blank=True)
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
