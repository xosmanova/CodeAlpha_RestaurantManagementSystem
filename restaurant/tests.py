from django.test import TestCase
from django.utils import timezone
from datetime import date, time, timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status

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


class RestaurantManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Category
        self.category = Category.objects.create(name="Burgers", description="Juicy burgers")

        # Inventory Items
        self.beef = InventoryItem.objects.create(name="Beef Patty", quantity=Decimal("10.0"), unit="pcs", min_threshold=Decimal("2.0"))
        self.bun = InventoryItem.objects.create(name="Burger Bun", quantity=Decimal("10.0"), unit="pcs", min_threshold=Decimal("2.0"))
        self.cheese = InventoryItem.objects.create(name="Cheddar Slice", quantity=Decimal("1.0"), unit="pcs", min_threshold=Decimal("3.0")) # low stock!

        # Menu Item
        self.burger = MenuItem.objects.create(
            name="Classic Cheeseburger",
            category=self.category,
            price=Decimal("12.50"),
            is_available=True
        )
        MenuItemIngredient.objects.create(menu_item=self.burger, inventory_item=self.beef, quantity_required=Decimal("1.0"))
        MenuItemIngredient.objects.create(menu_item=self.burger, inventory_item=self.bun, quantity_required=Decimal("1.0"))

        # Tables
        self.table_small = RestaurantTable.objects.create(table_number=1, capacity=2, location="MAIN")
        self.table_large = RestaurantTable.objects.create(table_number=2, capacity=6, location="MAIN")

    def test_menu_api_list(self):
        response = self.client.get('/api/menu/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results', response.data)), 1)

    def test_reservation_creation_and_conflict(self):
        res_date = date.today() + timedelta(days=1)
        res_time = time(18, 0)

        # 1. Successful reservation
        payload = {
            "customer_name": "John Doe",
            "customer_phone": "+1234567890",
            "table": self.table_small.id,
            "reservation_date": str(res_date),
            "reservation_time": "18:00",
            "party_size": 2,
            "duration_minutes": 120
        }
        res1 = self.client.post('/api/reservations/', payload, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # 2. Overlapping reservation on the same table should fail
        conflict_payload = {
            "customer_name": "Jane Smith",
            "customer_phone": "+0987654321",
            "table": self.table_small.id,
            "reservation_date": str(res_date),
            "reservation_time": "18:30", # Within the 18:00 - 20:00 window
            "party_size": 2,
            "duration_minutes": 60
        }
        res2 = self.client.post('/api/reservations/', conflict_payload, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("table", res2.data)

        # 3. Party size exceeding capacity should fail
        exceed_payload = {
            "customer_name": "Big Group",
            "customer_phone": "+1122334455",
            "table": self.table_small.id, # capacity is 2
            "reservation_date": str(res_date),
            "reservation_time": "21:00",
            "party_size": 5
        }
        res3 = self.client.post('/api/reservations/', exceed_payload, format='json')
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)

    def test_table_availability_endpoint(self):
        res_date = date.today() + timedelta(days=2)
        res_time = time(19, 0)

        # Reserve table 1
        Reservation.objects.create(
            customer_name="Alice",
            customer_phone="123",
            table=self.table_small,
            reservation_date=res_date,
            reservation_time=res_time,
            party_size=2
        )

        # Query available tables for party_size 2
        url = f'/api/tables/available/?date={res_date}&time=19:00&party_size=2'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        available_ids = [t['id'] for t in response.data['tables']]
        self.assertNotIn(self.table_small.id, available_ids)
        self.assertIn(self.table_large.id, available_ids)

    def test_order_placement_and_inventory_auto_update(self):
        initial_beef_qty = self.beef.quantity
        initial_bun_qty = self.bun.quantity

        order_payload = {
            "order_type": "DINE_IN",
            "table": self.table_small.id,
            "customer_name": "Bob",
            "items": [
                {"menu_item_id": self.burger.id, "quantity": 3}
            ]
        }
        response = self.client.post('/api/orders/', order_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['total_amount']), 37.50) # 3 * 12.50

        # Check inventory was deducted automatically
        self.beef.refresh_from_db()
        self.bun.refresh_from_db()
        self.assertEqual(self.beef.quantity, initial_beef_qty - 3)
        self.assertEqual(self.bun.quantity, initial_bun_qty - 3)

        # Check table status became OCCUPIED
        self.table_small.refresh_from_db()
        self.assertEqual(self.table_small.status, 'OCCUPIED')

    def test_order_fails_when_insufficient_inventory(self):
        # We only have 10 buns, try to order 15
        order_payload = {
            "order_type": "TAKEAWAY",
            "customer_name": "Hungry Bob",
            "items": [
                {"menu_item_id": self.burger.id, "quantity": 15}
            ]
        }
        response = self.client.post('/api/orders/', order_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Verify inventory unchanged
        self.beef.refresh_from_db()
        self.assertEqual(self.beef.quantity, Decimal("10.0"))

    def test_order_cancellation_restocks_inventory(self):
        order_payload = {
            "order_type": "DINE_IN",
            "table": self.table_small.id,
            "items": [{"menu_item_id": self.burger.id, "quantity": 2}]
        }
        create_res = self.client.post('/api/orders/', order_payload, format='json')
        order_id = create_res.data['id']

        self.beef.refresh_from_db()
        self.assertEqual(self.beef.quantity, Decimal("8.0"))

        # Cancel order
        cancel_res = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(cancel_res.status_code, status.HTTP_200_OK)

        # Stock should be returned to 10.0
        self.beef.refresh_from_db()
        self.assertEqual(self.beef.quantity, Decimal("10.0"))

    def test_stock_alerts_and_reports(self):
        # We set cheddar to 1.0 with threshold 3.0, so it should trigger low stock alert
        response = self.client.get('/api/reports/stock-alerts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        alert_names = [item['name'] for item in response.data['alerts']]
        self.assertIn("Cheddar Slice", alert_names)

        # Daily sales report
        daily_res = self.client.get('/api/reports/daily-sales/')
        self.assertEqual(daily_res.status_code, status.HTTP_200_OK)
        self.assertIn('total_revenue', daily_res.data)
        self.assertIn('breakdown_by_type', daily_res.data)
