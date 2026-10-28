from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import uuid


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ('kg', 'Kilograms (kg)'),
        ('g', 'Grams (g)'),
        ('l', 'Liters (l)'),
        ('ml', 'Milliliters (ml)'),
        ('pcs', 'Pieces (pcs)'),
        ('portion', 'Portions'),
    ]

    name = models.CharField(max_length=120, unique=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pcs')
    min_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5.0,
        help_text="Triggers low stock alert when quantity drops below or equals this value."
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_threshold

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class MenuItem(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu_items'
    )
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ${self.price}"


class MenuItemIngredient(models.Model):
    """
    Connects a menu item to its required ingredients in inventory.
    When an order is confirmed, the required quantity is automatically deducted.
    """
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='ingredients'
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='used_in_menu_items'
    )
    quantity_required = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Quantity required per 1 unit of this menu item"
    )

    class Meta:
        unique_together = ('menu_item', 'inventory_item')

    def __str__(self):
        return f"{self.menu_item.name} requires {self.quantity_required} {self.inventory_item.unit} of {self.inventory_item.name}"


class RestaurantTable(models.Model):
    LOCATION_CHOICES = [
        ('MAIN', 'Main Dining Hall'),
        ('TERRACE', 'Outdoor Terrace'),
        ('VIP', 'VIP Private Room'),
        ('BALCONY', 'Balcony'),
        ('BAR', 'Bar Area'),
    ]

    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
        ('MAINTENANCE', 'Out of Service'),
    ]

    table_number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField(default=4, help_text="Number of seats")
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='MAIN')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['table_number']

    def __str__(self):
        return f"Table #{self.table_number} ({self.get_location_display()} - {self.capacity} seats)"

    def is_available_at(self, check_date, check_time, duration_minutes=120, exclude_reservation_id=None):
        """
        Checks if table is available for the given date, time, and duration.
        """
        check_start = datetime.combine(check_date, check_time)
        check_end = check_start + timedelta(minutes=duration_minutes)

        reservations = Reservation.objects.filter(
            table=self,
            reservation_date=check_date,
            status__in=['PENDING', 'CONFIRMED']
        )
        if exclude_reservation_id:
            reservations = reservations.exclude(pk=exclude_reservation_id)

        for res in reservations:
            res_start = datetime.combine(res.reservation_date, res.reservation_time)
            res_end = res_start + timedelta(minutes=res.duration_minutes)

            # Overlap check
            if max(check_start, res_start) < min(check_end, res_end):
                return False
        return True


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=30)
    customer_email = models.EmailField(blank=True)
    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.CASCADE,
        related_name='reservations'
    )
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=120, help_text="Duration in minutes (e.g., 120 min / 2 hours)")
    party_size = models.PositiveIntegerField(default=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reservation_date', '-reservation_time']

    def clean(self):
        super().clean()
        if self.table_id:
            if self.party_size > self.table.capacity:
                raise ValidationError(
                    f"Party size ({self.party_size}) exceeds table capacity ({self.table.capacity})."
                )
            if not self.table.is_available_at(
                self.reservation_date,
                self.reservation_time,
                self.duration_minutes,
                exclude_reservation_id=self.pk
            ):
                raise ValidationError(
                    f"Table #{self.table.table_number} is already booked for this time slot."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation for {self.customer_name} - Table #{self.table.table_number} on {self.reservation_date} at {self.reservation_time}"


class Order(models.Model):
    TYPE_CHOICES = [
        ('DINE_IN', 'Dine-In'),
        ('TAKEAWAY', 'Takeaway'),
        ('DELIVERY', 'Delivery'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PREPARING', 'Preparing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    order_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='DINE_IN')
    table = models.ForeignKey(
        RestaurantTable,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    customer_name = models.CharField(max_length=100, blank=True, default="Guest")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            prefix = "ORD"
            date_str = timezone.now().strftime("%Y%m%d")
            unique_part = uuid.uuid4().hex[:6].upper()
            self.order_number = f"{prefix}-{date_str}-{unique_part}"
        super().save(*args, **kwargs)

    def update_total(self):
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save(update_fields=['total_amount'])

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()}) - ${self.total_amount}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.menu_item.price
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} (${self.subtotal})"
