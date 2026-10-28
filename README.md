# Restaurant Management System API

Backend REST API for a restaurant management system built with Python, Django, and Django REST Framework. Developed as part of the CodeAlpha Backend Development Internship (Task 3).

## Features

- **Menu Management:** Categorized menu items with prices and real-time availability.
- **Table Management & Availability Check:** Prevents double-booking and validates table seating capacity against party size.
- **Order Processing & Inventory Auto-Update:** 
  - Orders automatically calculate totals and deduct raw ingredient quantities from inventory using atomic transactions.
  - Rejects orders if ingredient stock is insufficient (prevents negative inventory).
  - Restocks ingredients automatically if an order is cancelled.
- **Stock Alerts:** Flags items that drop below minimum threshold levels.
- **Daily Sales & Analytics:** Endpoints for daily revenue, order volume, and top-selling dishes.
- **Admin Panel:** Pre-configured Django admin with status badges, inline order items, and quick action buttons.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** Django 5 / 6 & Django REST Framework (DRF)
- **Database:** SQLite (default for development)
- **CORS:** django-cors-headers

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/xosmanova/CodeAlpha_RestaurantManagementSystem.git
   cd CodeAlpha_RestaurantManagementSystem
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Load seed data (tables, sample menu, inventory, admin user):**
   ```bash
   python manage.py seed_data
   ```
   *Default Admin credentials:*
   - Username: `admin`
   - Password: `admin123`

6. **Run the development server:**
   ```bash
   python manage.py runserver
   ```
   Server will start at `http://127.0.0.1:8000/`.

7. **Run tests:**
   ```bash
   python manage.py test
   ```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/` | Overview of all available endpoints |
| `GET` | `/api/menu/` | List all menu items (filter by `?category=` or `?available=`) |
| `GET` | `/api/tables/` | List all restaurant tables |
| `GET` | `/api/tables/available/` | Find available tables (`?date=YYYY-MM-DD&time=HH:MM&party_size=N`) |
| `POST` | `/api/reservations/` | Create a table reservation (with conflict check) |
| `GET` | `/api/reservations/` | List reservations |
| `POST` | `/api/orders/` | Place order (deducts stock atomically) |
| `GET` | `/api/orders/` | List orders |
| `POST` | `/api/orders/{id}/update_status/` | Update order status (`PREPARING`, `COMPLETED`, etc.) |
| `POST` | `/api/orders/{id}/cancel/` | Cancel order and restock ingredients |
| `GET` | `/api/inventory/` | View current inventory items |
| `GET` | `/api/inventory/low_stock/` | View low stock alerts |
| `GET` | `/api/reports/daily-sales/` | Daily sales summary (`?date=YYYY-MM-DD`) |
| `GET` | `/api/reports/stock-alerts/` | Low stock inventory report |
| `GET` | `/api/reports/top-selling/` | Top selling menu items |

### Sample Order Request (`POST /api/orders/`)

```json
{
  "order_type": "DINE_IN",
  "table": 1,
  "customer_name": "John Doe",
  "items": [
    {
      "menu_item_id": 1,
      "quantity": 2
    },
    {
      "menu_item_id": 6,
      "quantity": 1
    }
  ]
}
```

## License

This project is open-source and created for educational purposes under the CodeAlpha Internship Program.
