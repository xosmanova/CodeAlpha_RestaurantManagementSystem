# 🍽️ Restaurant Management System — CodeAlpha Backend Internship

Bu layihə **CodeAlpha Backend Development Internship** çərçivəsində **TASK 3: Restaurant Management System** tələblərinə tam uyğun olaraq hazırlanmışdır.

---

## 📋 Layihənin Məqsədi və Tələbləri (Task Overview)

Tapşırıqda restoranın gündəlik əməliyyatlarını (sifarişlər, masalar, rezervasiyalar və anbar/inventar) idarə edən güclü bir **Backend REST API** sistemi qurulması tələb olunurdu:

1. **Backend Arxitekturası:** Python və **Django / Django REST Framework (DRF)** istifadə edilərək qurulmuşdur.
2. **Verilənlər Bazası Modelləri (Database Models):**
   - `MenuItem` & `Category`: Restoran menyusu, kateqoriyalar, qiymətlər və mövcudluq statusu.
   - `RestaurantTable`: Masaların nömrəsi, nəfərlik tutumu (capacity), zal zonası (Main, Terrace, VIP, Balcony) və statusu.
   - `Reservation`: Müştəri rezervasiyaları, tarix-saat, qonaq sayı və rezervasiya müddəti.
   - `Order` & `OrderItem`: Masaya və ya aparmağa (Dine-in, Takeaway, Delivery) sifarişlər, statuslar və ümumi məbləğ.
   - `InventoryItem`: Anbardakı ərzaq/xammal miqdarları, ölçü vahidləri və kritik ehtiyat limiti (min threshold).
   - `MenuItemIngredient`: Hər yeməyin hazırlanması üçün tələb olunan inqrediyent resepti.
3. **Biznes Məntiqi (Business Logic):**
   - ⚡ **Inventory Auto-Update:** Sifariş təsdiqlənən kimi tələb olunan inqrediyentlər avtomatik olaraq anbardan silinir (Database Transaction və Row-Locking ilə təhlükəsiz icra).
   - 🚫 **Insufficient Stock Protection:** Əgər anbarda tələb olunan ərzaq çatmırsa, sifariş xəta verir və anbarın mənfiyə düşməsi əngəllənir.
   - 🔄 **Restock on Cancel:** Sifariş ləğv edilərsə, ərzaqlar avtomatik anbara geri qaytarılır.
   - 🪑 **Table Availability Check:** Müştəri rezervasiya edərkən həmin saat aralığında masanın artıq bron edilib-edilmədiyi və qonaq sayının masa tutumuna uyğunluğu avtomatik yoxlanılır (double-booking qarşısı alınır).
4. **Əlavə (Bonus/Optional) Xüsusiyyətlər:**
   - 📊 **Daily Sales Report:** Günlük gəlir, tamamlanmış sifariş sayı, orta çek məbləği və sifariş növlərinə görə analiz.
   - ⚠️ **Stock Alerts:** Kritik həddən aşağı düşən və ya tükənən xammallar üçün xəbərdarlıq hesabatı.
   - 🏆 **Top Selling Items:** Ən çox satılan yeməklərin reytinqi.
   - 🎛️ **Full Admin Access Panel:** Rəngli status nişanları, xammal əlavə etmə düymələri, sifariş statusunu tək kliklə dəyişmə imkanı verən fərdiləşdirilmiş Django Admin Paneli.

---

## 🚀 Quraşdırma və İşə Salma (Quick Start)

### 1. Virtual Mühiti aktivləşdirin:
```bash
# Windows:
.\venv\Scripts\activate

# Linux / Mac:
source venv/bin/activate
```

### 2. Tələb olunan paketləri quraşdırın:
```bash
pip install -r requirements.txt
```

### 3. Miqrasiyaları tətbiq edin:
```bash
python manage.py migrate
```

### 4. Nümunəvi Məlumatları (Seed Data) bazaya yükləyin:
> Bu əmr avtomatik olaraq `admin` superistifadəçisini, menyu yeməklərini, masaları, reseptləri və anbar ərzaqlarını generasiya edir!
```bash
python manage.py seed_data
```
- **Admin Girişi:**
  - İstifadəçi adı: `admin`
  - Şifrə: `admin123`
  - Giriş linki: `http://127.0.0.1:8000/admin/`

### 5. Serveri başladın:
```bash
python manage.py runserver
```
Server `http://127.0.0.1:8000/` ünvanında aktiv olacaq.

### 6. Testləri yoxlayın:
```bash
python manage.py test
```
Bütün 7 avtomatlaşdırılmış vahid test (unit test) uğurla keçəcəkdir (`OK`).

---

## 📡 Əsas API Endpoint-ləri (API Reference)

| Metod | Endpoint | Təsvir |
|---|---|---|
| `GET` | `/api/` | Bütün API ünvanlarının xülasəsi |
| `GET` | `/api/menu/` | Bütün menyu yeməkləri və qiymətləri |
| `GET` | `/api/menu/?category=1` | Kateqoriyaya görə süzgəcləmə |
| `GET` | `/api/tables/` | Bütün masaların siyahısı və statusu |
| `GET` | `/api/tables/available/?date=YYYY-MM-DD&time=19:00&party_size=4` | Boş masaların axtarışı |
| `POST` | `/api/reservations/` | Yeni masa rezervasiyası etmək (doluluq yoxlanışı ilə) |
| `GET` | `/api/reservations/` | Rezervasiyaların siyahısı |
| `POST` | `/api/orders/` | Yeni sifariş yaratmaq (anbardan avtomatik çıxılma ilə) |
| `GET` | `/api/orders/` | Bütün sifarişlərin siyahısı |
| `POST` | `/api/orders/{id}/update_status/` | Sifarişin statusunu dəyişmək (`COMPLETED`, `PREPARING` və s.) |
| `POST` | `/api/orders/{id}/cancel/` | Sifarişi ləğv etmək və ərzaqları anbara qaytarmaq |
| `GET` | `/api/inventory/` | Anbardakı ərzaqların siyahısı |
| `GET` | `/api/inventory/low_stock/` | Bitmək üzrə olan ərzaqlar |
| `GET` | `/api/reports/daily-sales/` | Günlük gəlir və satış hesabatı |
| `GET` | `/api/reports/stock-alerts/` | Anbar xəbərdarlıq hesabatı |
| `GET` | `/api/reports/top-selling/` | Ən çox satılan yeməklərin hesabatı |

---

### 💡 Nümunə: Sifariş Yerləşdirmək (`POST /api/orders/`)

**Request Body (JSON):**
```json
{
  "order_type": "DINE_IN",
  "table": 1,
  "customer_name": "Elmir Aliyev",
  "items": [
    {
      "menu_item_id": 1,
      "quantity": 2
    },
    {
      "menu_item_id": 6,
      "quantity": 2
    }
  ]
}
```

**Response (JSON - 201 Created):**
```json
{
  "id": 2,
  "order_number": "ORD-20261028-A1B2C3",
  "order_type": "DINE_IN",
  "order_type_display": "Dine-In",
  "table": 1,
  "table_number": 1,
  "customer_name": "Elmir Aliyev",
  "status": "PENDING",
  "status_display": "Pending",
  "total_amount": "58.00",
  "items": [
    {
      "id": 3,
      "menu_item": 1,
      "menu_item_name": "Grilled Beef Steak",
      "quantity": 2,
      "price": "24.50",
      "subtotal": "49.00"
    },
    {
      "id": 4,
      "menu_item": 6,
      "menu_item_name": "Cappuccino",
      "quantity": 2,
      "price": "4.50",
      "subtotal": "9.00"
    }
  ],
  "created_at": "2026-10-28 04:00:00",
  "updated_at": "2026-10-28 04:00:00"
}
```

---

## 🎥 LinkedIn İzah Videosu və Təqdimat Üçün Ssenari (Video Guide)

CodeAlpha təlimatında qeyd edilən LinkedIn video izahı üçün aşağıdakı planla 2-3 dəqiqəlik video çəkə bilərsiniz:

1. **Giriş (15-20 saniyə):**
   - Özünüzü təqdim edin: *"Salam! Mən CodeAlpha Backend İnternship proqramı çərçivəsində TASK 3: Restaurant Management System layihəsini tamamladım."*
2. **Texnologiyalar (15 saniyə):**
   - Python, Django, Django REST Framework və SQLite istifadə edildiyini qeyd edin.
3. **Modellər və Biznes Məntiqi (45 saniyə):**
   - Menyu, Masalar, Rezervasiyalar, Sifarişlər və Anbar sistemini göstərin.
   - Sifariş veriləndə reseptdəki inqrediyentlərin anbardan avtomatik silinməsini və kifayət qədər ərzaq olmadıqda xətanın çıxmasını nümayiş etdirin.
4. **Masa Rezervasiyası və Doluluq Yoxlanışı (30 saniyə):**
   - Eyni saata eyni masanın ikinci dəfə rezervasiya edilə bilmədiyini (Double-booking qarşısının alınmasını) göstərin.
5. **Admin Paneli və Hesabatlar (30 saniyə):**
   - Django Admin panelindəki sifarişləri, rəngli statusları və `/api/reports/daily-sales/` ilə günlük gəlir hesabatını ekranda göstərin.
6. **Yekun (10 saniyə):**
   - CodeAlpha komandasına təşəkkür edin və GitHub reposu linkini postda qeyd edin.

---

## 📂 GitHub Repozitoriyası Adı:
CodeAlpha təlimatına əsasən GitHub repozitoriyanızın adı:
`CodeAlpha_RestaurantManagementSystem`
