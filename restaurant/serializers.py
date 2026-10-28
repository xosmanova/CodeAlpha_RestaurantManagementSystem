from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
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
from .services import OrderService


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']


class InventoryItemSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = ['id', 'name', 'quantity', 'unit', 'min_threshold', 'is_low_stock', 'last_updated']


class MenuItemIngredientSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventory_item.name', read_only=True)
    unit = serializers.CharField(source='inventory_item.unit', read_only=True)

    class Meta:
        model = MenuItemIngredient
        fields = ['id', 'inventory_item', 'inventory_item_name', 'quantity_required', 'unit']


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    ingredients = MenuItemIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'category', 'category_name', 'description', 'price', 'is_available', 'ingredients', 'created_at']


class RestaurantTableSerializer(serializers.ModelSerializer):
    location_display = serializers.CharField(source='get_location_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RestaurantTable
        fields = ['id', 'table_number', 'capacity', 'location', 'location_display', 'status', 'status_display', 'is_active']


class ReservationSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    table_capacity = serializers.IntegerField(source='table.capacity', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id',
            'customer_name',
            'customer_phone',
            'customer_email',
            'table',
            'table_number',
            'table_capacity',
            'reservation_date',
            'reservation_time',
            'duration_minutes',
            'party_size',
            'status',
            'special_requests',
            'created_at',
        ]

    def validate(self, attrs):
        table = attrs.get('table') or (self.instance.table if self.instance else None)
        party_size = attrs.get('party_size') or (self.instance.party_size if self.instance else None)
        reservation_date = attrs.get('reservation_date') or (self.instance.reservation_date if self.instance else None)
        reservation_time = attrs.get('reservation_time') or (self.instance.reservation_time if self.instance else None)
        duration_minutes = attrs.get('duration_minutes', 120)

        if table and party_size and party_size > table.capacity:
            raise serializers.ValidationError({
                "party_size": f"Party size ({party_size}) exceeds table capacity ({table.capacity})."
            })

        if table and reservation_date and reservation_time:
            exclude_id = self.instance.pk if self.instance else None
            if not table.is_available_at(reservation_date, reservation_time, duration_minutes, exclude_reservation_id=exclude_id):
                raise serializers.ValidationError({
                    "table": f"Table #{table.table_number} is already reserved or occupied during this time."
                })

        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity', 'price', 'subtotal']


class OrderItemInputSerializer(serializers.Serializer):
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(source='table.table_number', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'order_type',
            'order_type_display',
            'table',
            'table_number',
            'customer_name',
            'status',
            'status_display',
            'total_amount',
            'items',
            'created_at',
            'updated_at',
        ]


class OrderCreateSerializer(serializers.Serializer):
    order_type = serializers.ChoiceField(choices=Order.TYPE_CHOICES, default='DINE_IN')
    table = serializers.IntegerField(required=False, allow_null=True)
    customer_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='Guest')
    items = OrderItemInputSerializer(many=True)

    def create(self, validated_data):
        items_data = validated_data.get('items', [])
        table_id = validated_data.get('table')
        order_type = validated_data.get('order_type')
        customer_name = validated_data.get('customer_name')

        try:
            order = OrderService.place_order(
                order_type=order_type,
                table_id=table_id,
                customer_name=customer_name,
                items_data=items_data
            )
            return order
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message if hasattr(e, 'message') else str(e))
