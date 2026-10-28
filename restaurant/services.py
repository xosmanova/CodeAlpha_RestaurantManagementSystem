from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, date, timedelta
from .models import (
    MenuItem,
    InventoryItem,
    RestaurantTable,
    Reservation,
    Order,
    OrderItem,
)


class OrderService:
    @staticmethod
    @transaction.atomic
    def place_order(order_type, table_id, customer_name, items_data):
        """
        Creates an order with items, validates inventory stock,
        deducts required ingredients from inventory, and updates total price.
        """
        if not items_data:
            raise ValidationError("An order must contain at least one item.")

        table = None
        if table_id:
            try:
                table = RestaurantTable.objects.get(pk=table_id, is_active=True)
            except RestaurantTable.DoesNotExist:
                raise ValidationError(f"Table with id {table_id} does not exist or is inactive.")

        # Step 1: Pre-calculate total ingredient demands across all items
        ingredient_demands = {}  # {inventory_item_id: {'item': InventoryItem, 'needed': Decimal}}
        menu_items_cache = {}

        for item_info in items_data:
            menu_item_id = item_info.get('menu_item_id')
            qty = int(item_info.get('quantity', 1))
            if qty <= 0:
                raise ValidationError(f"Quantity must be at least 1.")

            try:
                menu_item = MenuItem.objects.get(pk=menu_item_id)
            except MenuItem.DoesNotExist:
                raise ValidationError(f"MenuItem with id {menu_item_id} does not exist.")

            if not menu_item.is_available:
                raise ValidationError(f"MenuItem '{menu_item.name}' is currently marked as unavailable.")

            menu_items_cache[menu_item_id] = menu_item

            # Check ingredients
            ingredients = menu_item.ingredients.select_related('inventory_item').all()
            for ing in ingredients:
                inv = ing.inventory_item
                needed = ing.quantity_required * qty
                if inv.id not in ingredient_demands:
                    ingredient_demands[inv.id] = {
                        'inventory_item': inv,
                        'total_needed': needed
                    }
                else:
                    ingredient_demands[inv.id]['total_needed'] += needed

        # Step 2: Check stock availability with row-locking (select_for_update)
        inventory_ids = list(ingredient_demands.keys())
        locked_inventory = {
            item.id: item
            for item in InventoryItem.objects.select_for_update().filter(id__in=inventory_ids)
        }

        shortages = []
        for inv_id, demand in ingredient_demands.items():
            current_stock = locked_inventory[inv_id]
            needed = demand['total_needed']
            if current_stock.quantity < needed:
                shortages.append(
                    f"{current_stock.name}: needed {needed} {current_stock.unit}, available {current_stock.quantity} {current_stock.unit}"
                )

        if shortages:
            shortage_msg = "; ".join(shortages)
            raise ValidationError(f"Insufficient inventory stock: {shortage_msg}")

        # Step 3: Deduct inventory stock
        for inv_id, demand in ingredient_demands.items():
            stock = locked_inventory[inv_id]
            stock.quantity -= demand['total_needed']
            stock.save(update_fields=['quantity', 'last_updated'])

        # Step 4: Create the Order instance
        order = Order.objects.create(
            order_type=order_type,
            table=table,
            customer_name=customer_name or "Guest",
            status='PENDING'
        )

        total_amount = 0
        for item_info in items_data:
            menu_item = menu_items_cache[item_info.get('menu_item_id')]
            qty = int(item_info.get('quantity', 1))
            price = menu_item.price
            subtotal = price * qty
            total_amount += subtotal

            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=qty,
                price=price,
                subtotal=subtotal
            )

        order.total_amount = total_amount
        order.save(update_fields=['total_amount'])

        # Update table status if dine-in
        if table and order_type == 'DINE_IN':
            table.status = 'OCCUPIED'
            table.save(update_fields=['status'])

        return order

    @staticmethod
    @transaction.atomic
    def cancel_order(order):
        """
        Cancels an order and optionally restocks ingredients.
        """
        if order.status == 'CANCELLED':
            return order

        # Restock ingredients
        for item in order.items.select_related('menu_item').all():
            for ing in item.menu_item.ingredients.select_related('inventory_item').all():
                restock_qty = ing.quantity_required * item.quantity
                inv = InventoryItem.objects.select_for_update().get(pk=ing.inventory_item_id)
                inv.quantity += restock_qty
                inv.save(update_fields=['quantity', 'last_updated'])

        order.status = 'CANCELLED'
        order.save(update_fields=['status', 'updated_at'])

        if order.table:
            # Check if there are other active orders on this table
            active_orders = Order.objects.filter(
                table=order.table,
                status__in=['PENDING', 'PREPARING']
            ).exclude(pk=order.pk).exists()
            if not active_orders:
                order.table.status = 'AVAILABLE'
                order.table.save(update_fields=['status'])

        return order


class TableService:
    @staticmethod
    def get_available_tables(target_date, target_time, party_size=1, duration_minutes=120):
        """
        Returns all active tables that can accommodate party_size and have no
        overlapping reservations during the specified window.
        """
        candidate_tables = RestaurantTable.objects.filter(
            is_active=True,
            capacity__gte=party_size
        )

        available_tables = []
        for tbl in candidate_tables:
            if tbl.is_available_at(target_date, target_time, duration_minutes):
                available_tables.append(tbl)

        return available_tables


class ReportService:
    @staticmethod
    def get_daily_sales(target_date=None):
        if target_date is None:
            target_date = timezone.localdate()
        elif isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

        orders = Order.objects.filter(
            created_at__date=target_date
        )

        completed_orders = orders.filter(status='COMPLETED')
        total_revenue = completed_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        total_orders_count = orders.count()
        completed_count = completed_orders.count()
        cancelled_count = orders.filter(status='CANCELLED').count()
        pending_or_prep_count = orders.filter(status__in=['PENDING', 'PREPARING']).count()

        avg_ticket = (total_revenue / completed_count) if completed_count > 0 else 0

        # Breakdown by order type
        breakdown_by_type = list(
            orders.values('order_type').annotate(
                count=Count('id'),
                revenue=Sum('total_amount')
            )
        )

        return {
            'date': str(target_date),
            'total_revenue': float(total_revenue),
            'total_orders': total_orders_count,
            'completed_orders': completed_count,
            'cancelled_orders': cancelled_count,
            'active_orders': pending_or_prep_count,
            'average_order_value': round(float(avg_ticket), 2),
            'breakdown_by_type': breakdown_by_type,
        }

    @staticmethod
    def get_stock_alerts():
        """
        Returns inventory items that are at or below minimum threshold.
        """
        low_stock_items = InventoryItem.objects.filter(
            quantity__lte=F('min_threshold')
        ).order_by('quantity')

        results = []
        for item in low_stock_items:
            results.append({
                'id': item.id,
                'name': item.name,
                'current_quantity': float(item.quantity),
                'unit': item.unit,
                'min_threshold': float(item.min_threshold),
                'shortage_percentage': round(
                    max(0.0, (1.0 - (float(item.quantity) / float(item.min_threshold))) * 100), 1
                ) if item.min_threshold > 0 else 0.0,
                'alert_level': 'CRITICAL' if item.quantity <= 0 else 'WARNING'
            })
        return results

    @staticmethod
    def get_top_selling_items(limit=5):
        top_items = (
            OrderItem.objects
            .filter(order__status='COMPLETED')
            .values('menu_item__id', 'menu_item__name', 'menu_item__price')
            .annotate(
                total_quantity_sold=Sum('quantity'),
                total_sales_amount=Sum('subtotal')
            )
            .order_by('-total_quantity_sold')[:limit]
        )
        return list(top_items)
