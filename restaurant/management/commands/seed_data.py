from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date, time
from decimal import Decimal

from restaurant.models import (
    Category,
    InventoryItem,
    MenuItem,
    MenuItemIngredient,
    RestaurantTable,
    Reservation,
    Order,
    OrderItem,
)


class Command(BaseCommand):
    help = "Seeds database with sample restaurant data and creates default admin user"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Starting restaurant database seeding..."))

        # 1. Create Superuser if doesn't exist
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@restaurant.com", "admin123")
            self.stdout.write(self.style.SUCCESS("Created superuser: username='admin', password='admin123'"))
        else:
            self.stdout.write(self.style.NOTICE("Superuser 'admin' already exists."))

        # 2. Categories
        categories_data = [
            ("Main Courses", "Delicious traditional and modern main dishes"),
            ("Starters & Appetizers", "Fresh salads, soups and hot starters"),
            ("Desserts", "Sweet pastries, cakes and ice-creams"),
            ("Beverages", "Refreshing mocktails, fresh juices, teas and coffees"),
        ]
        cat_map = {}
        for name, desc in categories_data:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc})
            cat_map[name] = cat
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(cat_map)} categories."))

        # 3. Inventory Items
        inventory_data = [
            ("Beef Meat", Decimal("25.0"), "kg", Decimal("5.0")),
            ("Chicken Breast", Decimal("20.0"), "kg", Decimal("4.0")),
            ("Rice (Basmati)", Decimal("30.0"), "kg", Decimal("6.0")),
            ("Tomatoes", Decimal("15.0"), "kg", Decimal("3.0")),
            ("Onions", Decimal("20.0"), "kg", Decimal("5.0")),
            ("Cheese (Mozzarella)", Decimal("8.0"), "kg", Decimal("2.0")),
            ("Potatoes", Decimal("35.0"), "kg", Decimal("5.0")),
            ("Coffee Beans", Decimal("2.5"), "kg", Decimal("3.0")), # Low stock trigger
            ("Milk", Decimal("4.0"), "l", Decimal("5.0")),          # Low stock trigger
            ("Fresh Mint", Decimal("1.0"), "kg", Decimal("0.5")),
            ("Flour", Decimal("18.0"), "kg", Decimal("3.0")),
            ("Chocolate Sauce", Decimal("3.0"), "l", Decimal("1.0")),
        ]
        inv_map = {}
        for name, qty, unit, min_th in inventory_data:
            inv, _ = InventoryItem.objects.update_or_create(
                name=name,
                defaults={'quantity': qty, 'unit': unit, 'min_threshold': min_th}
            )
            inv_map[name] = inv
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(inv_map)} inventory items."))

        # 4. Tables
        tables_data = [
            (1, 2, 'MAIN'),
            (2, 4, 'MAIN'),
            (3, 4, 'MAIN'),
            (4, 6, 'MAIN'),
            (5, 8, 'MAIN'),
            (10, 2, 'TERRACE'),
            (11, 4, 'TERRACE'),
            (12, 4, 'TERRACE'),
            (20, 6, 'VIP'),
            (21, 10, 'VIP'),
            (30, 2, 'BALCONY'),
        ]
        for num, cap, loc in tables_data:
            RestaurantTable.objects.get_or_create(
                table_number=num,
                defaults={'capacity': cap, 'location': loc, 'status': 'AVAILABLE'}
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(tables_data)} restaurant tables."))

        # 5. Menu Items & Ingredients
        menu_items_data = [
            {
                "name": "Grilled Beef Steak",
                "category": cat_map["Main Courses"],
                "price": Decimal("24.50"),
                "description": "Prime grilled tender beef served with roasted potatoes",
                "ingredients": [
                    ("Beef Meat", Decimal("0.30")),
                    ("Potatoes", Decimal("0.20")),
                    ("Onions", Decimal("0.05")),
                ]
            },
            {
                "name": "Chicken Alfredo Rice",
                "category": cat_map["Main Courses"],
                "price": Decimal("16.00"),
                "description": "Creamy chicken breast slices served over fragrant basmati rice",
                "ingredients": [
                    ("Chicken Breast", Decimal("0.25")),
                    ("Rice (Basmati)", Decimal("0.15")),
                    ("Cheese (Mozzarella)", Decimal("0.05")),
                ]
            },
            {
                "name": "Fresh Tomato Salad",
                "category": cat_map["Starters & Appetizers"],
                "price": Decimal("7.50"),
                "description": "Organic ripe tomatoes with sliced onions, fresh herbs and olive oil",
                "ingredients": [
                    ("Tomatoes", Decimal("0.20")),
                    ("Onions", Decimal("0.05")),
                    ("Fresh Mint", Decimal("0.02")),
                ]
            },
            {
                "name": "Classic French Fries",
                "category": cat_map["Starters & Appetizers"],
                "price": Decimal("5.00"),
                "description": "Crispy golden potato fries seasoned with sea salt",
                "ingredients": [
                    ("Potatoes", Decimal("0.30")),
                ]
            },
            {
                "name": "Chocolate Lava Cake",
                "category": cat_map["Desserts"],
                "price": Decimal("9.00"),
                "description": "Warm chocolate molten cake topped with melted dark chocolate",
                "ingredients": [
                    ("Flour", Decimal("0.10")),
                    ("Chocolate Sauce", Decimal("0.08")),
                ]
            },
            {
                "name": "Cappuccino",
                "category": cat_map["Beverages"],
                "price": Decimal("4.50"),
                "description": "Rich espresso brewed from fresh beans with steamed creamy milk foam",
                "ingredients": [
                    ("Coffee Beans", Decimal("0.02")),
                    ("Milk", Decimal("0.20")),
                ]
            },
            {
                "name": "Iced Mint Lemonade",
                "category": cat_map["Beverages"],
                "price": Decimal("4.00"),
                "description": "Fresh squeezed lemonade with crushed ice and handpicked garden mint",
                "ingredients": [
                    ("Fresh Mint", Decimal("0.03")),
                ]
            },
        ]

        menu_map = {}
        for item_data in menu_items_data:
            menu_item, _ = MenuItem.objects.get_or_create(
                name=item_data["name"],
                defaults={
                    "category": item_data["category"],
                    "price": item_data["price"],
                    "description": item_data["description"],
                    "is_available": True
                }
            )
            menu_map[item_data["name"]] = menu_item

            for ing_name, req_qty in item_data["ingredients"]:
                if ing_name in inv_map:
                    MenuItemIngredient.objects.get_or_create(
                        menu_item=menu_item,
                        inventory_item=inv_map[ing_name],
                        defaults={"quantity_required": req_qty}
                    )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(menu_items_data)} menu items with ingredients."))

        # 6. Sample Reservation
        today = date.today()
        tbl2 = RestaurantTable.objects.get(table_number=2)
        if not Reservation.objects.filter(table=tbl2, reservation_date=today).exists():
            Reservation.objects.create(
                customer_name="Ali Mammadov",
                customer_phone="+994501234567",
                customer_email="ali@example.com",
                table=tbl2,
                reservation_date=today,
                reservation_time=time(19, 0),
                duration_minutes=120,
                party_size=4,
                status="CONFIRMED",
                special_requests="Window side requested"
            )
            self.stdout.write(self.style.SUCCESS("Created sample reservation for Table #2."))

        # 7. Sample Orders
        tbl1 = RestaurantTable.objects.get(table_number=1)
        if not Order.objects.filter(table=tbl1).exists():
            order1 = Order.objects.create(
                order_type="DINE_IN",
                table=tbl1,
                customer_name="Leyla Huseynova",
                status="COMPLETED"
            )
            steak = menu_map["Grilled Beef Steak"]
            coffee = menu_map["Cappuccino"]
            OrderItem.objects.create(order=order1, menu_item=steak, quantity=2, price=steak.price, subtotal=steak.price * 2)
            OrderItem.objects.create(order=order1, menu_item=coffee, quantity=2, price=coffee.price, subtotal=coffee.price * 2)
            order1.update_total()
            self.stdout.write(self.style.SUCCESS(f"Created sample completed order {order1.order_number} (${order1.total_amount})."))

        self.stdout.write(self.style.SUCCESS("All seed data created successfully!"))
