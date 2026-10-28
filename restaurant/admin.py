from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category,
    InventoryItem,
    MenuItem,
    MenuItemIngredient,
    RestaurantTable,
    Reservation,
    Order,
    OrderItem,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'items_count')
    search_fields = ('name',)

    def items_count(self, obj):
        return obj.menu_items.count()
    items_count.short_description = "Menu Items"


class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'is_available', 'created_at')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available')
    inlines = [MenuItemIngredientInline]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'quantity_badge', 'unit', 'min_threshold', 'stock_status', 'last_updated')
    list_filter = ('unit',)
    search_fields = ('name',)
    actions = ['add_10_units']

    def quantity_badge(self, obj):
        if obj.is_low_stock:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', obj.quantity)
        return format_html('<span style="color: green;">{}</span>', obj.quantity)
    quantity_badge.short_description = "Quantity"

    def stock_status(self, obj):
        if obj.quantity <= 0:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">OUT OF STOCK</span>')
        elif obj.is_low_stock:
            return format_html('<span style="background-color: #ffc107; color: black; padding: 3px 8px; border-radius: 4px; font-weight: bold;">LOW STOCK</span>')
        return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 4px;">OK</span>')
    stock_status.short_description = "Status"

    @admin.action(description="Add +10 units to selected inventory items")
    def add_10_units(self, request, queryset):
        for item in queryset:
            item.quantity += 10
            item.save(update_fields=['quantity', 'last_updated'])
        self.message_user(request, f"Added 10 units to {queryset.count()} items.")


@admin.register(RestaurantTable)
class RestaurantTableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'capacity', 'location', 'status_badge', 'is_active')
    list_filter = ('location', 'status', 'is_active')
    search_fields = ('table_number',)

    def status_badge(self, obj):
        colors = {
            'AVAILABLE': '#28a745',
            'OCCUPIED': '#dc3545',
            'RESERVED': '#17a2b8',
            'MAINTENANCE': '#6c757d'
        }
        color = colors.get(obj.status, '#333')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'customer_phone', 'table', 'reservation_date', 'reservation_time', 'party_size', 'status_badge')
    list_filter = ('status', 'reservation_date', 'table')
    search_fields = ('customer_name', 'customer_phone', 'customer_email')
    date_hierarchy = 'reservation_date'

    def status_badge(self, obj):
        colors = {
            'CONFIRMED': '#28a745',
            'PENDING': '#ffc107',
            'COMPLETED': '#007bff',
            'CANCELLED': '#6c757d',
        }
        color = colors.get(obj.status, '#333')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('menu_item', 'quantity', 'price', 'subtotal')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'order_type', 'table', 'total_amount', 'status_badge', 'created_at')
    list_filter = ('status', 'order_type', 'created_at')
    search_fields = ('order_number', 'customer_name')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    actions = ['mark_as_completed', 'mark_as_preparing']

    def status_badge(self, obj):
        colors = {
            'PENDING': '#ffc107',
            'PREPARING': '#17a2b8',
            'COMPLETED': '#28a745',
            'CANCELLED': '#dc3545',
        }
        color = colors.get(obj.status, '#333')
        text_color = 'black' if obj.status == 'PENDING' else 'white'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            text_color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    @admin.action(description="Mark selected orders as COMPLETED")
    def mark_as_completed(self, request, queryset):
        for order in queryset:
            order.status = 'COMPLETED'
            order.save(update_fields=['status', 'updated_at'])
            if order.table:
                order.table.status = 'AVAILABLE'
                order.table.save(update_fields=['status'])
        self.message_user(request, f"{queryset.count()} order(s) marked as completed.")

    @admin.action(description="Mark selected orders as PREPARING")
    def mark_as_preparing(self, request, queryset):
        queryset.update(status='PREPARING')
        self.message_user(request, f"{queryset.count()} order(s) marked as preparing.")
