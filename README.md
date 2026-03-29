# ERPNext → OpenCart Product Sync System

A Python-based integration that synchronizes products from ERPNext to OpenCart.
Supports **bulk syncing** (all products) and **real-time webhook-based syncing** (add / update / delete triggered by ERPNext events).

The system communicates with OpenCart's MySQL database through a lightweight PHP bridge file (`db_bridge.php`) hosted on your OpenCart server.


---


## Features

- **Bulk product sync** — Syncs all products from configured ERPNext categories to OpenCart.
- **Real-time webhook sync** — FastAPI server listens for ERPNext webhooks to add, update, or delete products.
- **Price sync** — Fetches the "Standard Selling" price from ERPNext.
- **Quantity sync** — Calculates available stock across one or more ERPNext warehouses.
- **Category linking** — Automatically links products to their corresponding OpenCart categories.
- **Multi-language support** — Inserts product descriptions into all configured OpenCart languages.
- **SEO-friendly URLs** — Generates clean SEO keywords for each product automatically.
- **Retry mechanism** — Each operation retries up to 4 times on failure.
- **Logging** — All operations are logged to `app.log` and the console with colored output.


---


## Architecture Overview

```
+---------------+       HTTP/API        +--------------------+
|   ERPNext     | ------------------>   |  Python Sync App   |
|   (Source)    |                        |  (This Project)    |
+---------------+                       +---------+----------+
                                                  |
                                           HTTP POST (SQL)
                                                  |
                                                  v
                                        +-------------------+
                                        |  db_bridge.php    |
                                        | (On OpenCart Web   |
                                        |      Server)      |
                                        +---------+---------+
                                                  |
                                            MySQL Queries
                                                  |
                                                  v
                                        +-------------------+
                                        |  OpenCart MySQL    |
                                        |    Database        |
                                        +-------------------+
```


---


## Project Structure

```
ERP_Opencart_sync_system/
|
|-- .env                          # Environment variables (API keys, URLs, secrets)
|-- main.py                       # Starts the FastAPI webhook server (real-time sync)
|-- initiate_sync.py              # Runs bulk sync for all configured categories
|-- main_manager.py               # Orchestrates add / update / delete operations
|-- requirements.txt              # Python dependencies
|-- db_bridge.php                 # PHP bridge file (upload to your OpenCart server)
|
|-- app/
    |-- config/
    |   |-- settings.py           # ERP stores, OpenCart languages, tax & stock settings
    |   |-- category_configs.py   # ERPNext to OpenCart category name mapping
    |
    |-- controller/
    |   |-- endpoints.py          # FastAPI routes for webhook-based sync
    |   |-- schema.py             # Pydantic request schemas
    |
    |-- mapper/
    |   |-- erpnext_to_opencart.py  # Maps ERPNext item fields to OpenCart product format
    |
    |-- services/
    |   |-- ERPNext_services/
    |   |   |-- item_service.py     # Fetches items, prices, quantities from ERPNext API
    |   |
    |   |-- opencart_services/
    |       |-- product_addition.py   # Inserts new products into OpenCart
    |       |-- prodcut_updating.py   # Updates existing products in OpenCart
    |       |-- product_deleting.py   # Deletes products from OpenCart
    |       |-- category_addition.py  # Links categories to products
    |       |-- category_updating.py  # Updates category-product links
    |
    |-- utils/
        |-- db_utils.py           # Sends SQL queries to the PHP bridge
        |-- logger.py             # Logging configuration
```


---


## Prerequisites

- Python 3.10+
- ERPNext instance with API access enabled
- OpenCart store with admin access (to find language IDs, tax class IDs, stock status IDs)
- Server access (FTP/SSH) to upload the PHP bridge file to OpenCart server
- PHP + MySQL on the OpenCart server (already present if OpenCart is running)


---


## Installation


### Step 1 — Clone the Repository

```
git clone https://github.com/your-username/ERP_Opencart_sync_system.git
cd ERP_Opencart_sync_system
```


### Step 2 — Create a Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```


### Step 3 — Install Dependencies

```
pip install -r requirements.txt
```


### Step 4 — Set Up the PHP Bridge on Your OpenCart Server

The `db_bridge.php` file acts as a secure middleman between this Python app and your OpenCart MySQL database.

1. Open `db_bridge.php` and fill in your OpenCart database credentials:

```php
define('SECRET', 'your_strong_secret_key_here');

$host     = 'localhost';
$port     = 3306;
$user     = 'your_opencart_db_username';
$password = 'your_opencart_db_password';
$database = 'your_opencart_db_name';
```

   TIP: You can find the database credentials in your OpenCart's `config.php` on the server.

2. Upload `db_bridge.php` to the ROOT directory of your OpenCart installation
   (e.g. `public_html/db_bridge.php`).

3. Test the bridge by visiting `https://your-opencart-domain.com/db_bridge.php`
   in a browser. You should see `{"error":"Forbidden"}` — this means it's working.


---


## Configuration

There are 3 files you need to configure before running the system.


### FILE 1:  `.env`  (Environment Variables)

Create a `.env` file in the project root directory (same level as `main.py`).

```
# API Secret Key (Webhook Authentication)
# ERPNext must send this key in the "Authorization" header.
API_SECRET_KEY="your_api_secret_key_here"

# ERPNext Configuration
ERP_BASE_URL=https://your-erpnext-site.com/api/resource
ERP_API_KEY="your_erp_api_key"
ERP_API_SECRET="your_erp_api_secret"

# OpenCart Bridge Configuration
BRIDGE_URL="https://your-opencart-domain.com/db_bridge.php"
SECRET="your_bridge_secret_key_here"
DB_PREFIX="oc_"
```

Variable reference:

| Variable | Description | Example |
|---|---|---|
| `API_SECRET_KEY` | Secret key to authenticate webhook requests. ERPNext sends this in the `Authorization` header. | `"mY_s3cret_w3bhook_key"` |
| `ERP_BASE_URL` | Your ERPNext site API base URL. Must end with `/api/resource`. | `https://myerp.frappe.cloud/api/resource` |
| `ERP_API_KEY` | API key generated in ERPNext (Settings → API Access → Generate Keys). | `"8d4a583c6091756"` |
| `ERP_API_SECRET` | API secret generated in ERPNext (paired with the API key). | `"8549b3a0f8f8c7a"` |
| `BRIDGE_URL` | Full URL to the `db_bridge.php` file on your OpenCart server. | `"https://myshop.com/db_bridge.php"` |
| `SECRET` | Must EXACTLY match the `SECRET` constant inside `db_bridge.php`. | `"mYs3cr3tKey_ch4ngeMe"` |
| `DB_PREFIX` | OpenCart database table prefix. Usually `oc_`. | `"oc_"` |


### FILE 2:  `app/config/settings.py`  (ERP & OpenCart Settings)


#### A) ERPNext Store Settings

```python
erp_settig = {
    'store': ['Store Name 1 - ABBR', 'Store Name 2 - ABBR']
}
```

- `store` — List of ERPNext warehouse names used to calculate available quantity.
- Formula: `Available Qty = SUM(actual_qty - reserved_qty)` across all listed warehouses.
- Find warehouse names in ERPNext → Stock → Warehouse (include the abbreviation, e.g. `"Stores - MGD"`).


#### B) OpenCart Settings

```python
opencart_settings = {
    'languages': [1, 2],
    "tax_class_id": "9",
    "stock_status_id": "7",
}
```

| Setting | Description | How to Find |
|---|---|---|
| `languages` | List of language IDs. Product descriptions are inserted for each. | Admin → System → Localisation → Languages |
| `tax_class_id` | Tax class to apply. `"0"` = no tax. | Admin → System → Localisation → Taxes → Tax Classes |
| `stock_status_id` | Display label when qty = 0. Purely cosmetic. | Admin → System → Localisation → Stock Statuses |

Common default stock status IDs: `5` = In Stock, `6` = 2-3 Days, `7` = Out of Stock, `8` = Pre-Order.
These IDs may differ in your installation — always verify in admin.


### FILE 3:  `app/config/category_configs.py`  (Category Mapping)

Defines which ERPNext item groups are synced and maps them to OpenCart category names.

```python
categoris_names_convertion = {
    'ERPNext Category Name': 'OpenCart Category Name',
}
```

- **Key** = Exact Item Group name in ERPNext.
- **Value** = Exact Category name in OpenCart (any language).
- Only listed categories are synced — unlisted ones are skipped.

**IMPORTANT:**
1. Categories must ALREADY EXIST in OpenCart (the system does NOT create them).
2. Names must match EXACTLY (case-sensitive).

Example:
```python
categoris_names_convertion = {
    'JVC'                   : 'JVC',
    'Magic Unbreakable'     : 'Magic Unbreakable',
    'Electronics - Home'    : 'Home Electronics',      # Different names OK
    'Air Conditioners'      : 'تكييفات',               # Arabic name OK
}
```


---


## Usage


### Option 1 — Bulk Sync (Sync All Products)

Fetches ALL products from every category in `category_configs.py` and syncs them to OpenCart.
Use this for the initial import or to re-sync everything.

```
python initiate_sync.py
```

The script iterates through each mapped category, fetches item data/price/quantity from ERPNext,
and adds the product to OpenCart (including SEO URL and category linking). Retries up to 4 times on failure.


### Option 2 — Real-Time Sync (Webhook API Server)

Starts a FastAPI server that listens for ERPNext webhook requests.

```
python main.py
```

Server starts on `http://localhost:8000`. To keep it running in background on Linux:
```
nohup python3.11 main.py > server.log 2>&1 &
```


### API Endpoints

All endpoints require an `Authorization` header matching your `API_SECRET_KEY`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sync/add-product` | Add a new product to OpenCart |
| `PUT` | `/sync/update-product` | Update an existing product in OpenCart |
| `DELETE` | `/sync/delete-product` | Delete a product from OpenCart |
| `PUT` | `/sync/update-product-price` | Update only the price of a product |
| `PUT` | `/sync/update-product-quantity-sle` | Update product quantity (Stock Ledger Entry) |
| `PUT` | `/sync/update-product-quantity-so` | Update quantity for items in a Sales Order |
| `GET` | `/` | Test endpoint (verify server is running) |


---


## ERPNext Webhook Setup

You need to create **7 webhooks** in ERPNext to enable real-time sync.
Go to: **Home → Integrations → Webhook** and create each one as described below.

### Common Settings for ALL Webhooks

All 7 webhooks share these headers:

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `Authorization` | `Your_api_secret_key` |

Replace `Your_api_secret_key` with the actual `API_SECRET_KEY` value from your `.env` file.
Replace `{your-server}` in the URLs below with your actual server IP/domain and port.


### Webhook 1 — Insert Item (Add Product)

| Setting | Value |
|---|---|
| **DocType** | `Item` |
| **Event** | After Insert |
| **Request URL** | `http://{your-server}:8000/sync/add-product` |
| **Request Method** | POST |
| **Request Structure** | JSON |

**Request Body:**
```json
{
  "data": {{ doc | tojson | safe }}
}
```


### Webhook 2 — Update Item (Update Product)

| Setting | Value |
|---|---|
| **DocType** | `Item` |
| **Event** | on Update |
| **Request URL** | `http://{your-server}:8000/sync/update-product` |
| **Request Method** | PUT |
| **Request Structure** | JSON |

**Request Body:**
```json
{
  "data": {{ doc | tojson | safe }}
}
```


### Webhook 3 — Delete Item (Delete Product)

| Setting | Value |
|---|---|
| **DocType** | `Item` |
| **Event** | on Trash |
| **Request URL** | `http://{your-server}:8000/sync/delete-product` |
| **Request Method** | DELETE |
| **Request Structure** | JSON |

**Request Body:**
```json
{
  "data": {{ doc | tojson | safe }}
}
```


### Webhook 4 — Update Price

| Setting | Value |
|---|---|
| **DocType** | `Item Price` |
| **Event** | on Update |
| **Request URL** | `http://{your-server}:8000/sync/update-product-price` |
| **Request Method** | PUT |

**Webhook Data (Fields):**

| Fieldname | Key |
|---|---|
| `price_list_rate` | `price_list_rate` |
| `price_list` | `price_list` |
| `item_code` | `item_code` |


### Webhook 5 — Update Quantity (Stock Ledger Entry)

| Setting | Value |
|---|---|
| **DocType** | `Stock Ledger Entry` |
| **Event** | After Insert |
| **Request URL** | `http://{your-server}:8000/sync/update-product-quantity-sle` |
| **Request Method** | PUT |

**Webhook Data (Fields):**

| Fieldname | Key |
|---|---|
| `item_code` | `item_code` |


### Webhook 6 — Update Quantity on Sales Order Submit

| Setting | Value |
|---|---|
| **DocType** | `Sales Order` |
| **Event** | on Submit |
| **Request URL** | `http://{your-server}:8000/sync/update-product-quantity-so` |
| **Request Method** | PUT |

**Webhook Data (Fields):**

| Fieldname | Key |
|---|---|
| `items` | `items` |


### Webhook 7 — Update Quantity on Sales Order Cancel

| Setting | Value |
|---|---|
| **DocType** | `Sales Order` |
| **Event** | on Cancel |
| **Request URL** | `http://{your-server}:8000/sync/update-product-quantity-so` |
| **Request Method** | PUT |

**Webhook Data (Fields):**

| Fieldname | Key |
|---|---|
| `items` | `items` |


---


## How It Works

1. **Data Fetching** — The Item service fetches item data, prices (from "Standard Selling" price list), and available quantities from ERPNext REST API.

2. **Data Mapping** — The ERPToOpencart mapper transforms ERPNext fields into OpenCart product format, including SEO-friendly URL slugs.

3. **Database Operations** — OpenCart services build SQL queries and send them to `db_bridge.php` via HTTP POST. The bridge executes them on the OpenCart MySQL database.

4. **Category Linking** — The system maps ERPNext item groups to OpenCart categories via `categoris_names_convertion` and inserts the product-category relationship.


---


## Important Notes

- Do NOT change file paths within the project — imports depend on the directory structure.
- The `.env` file MUST be in the project root (same level as `main.py`).
- Categories must EXIST in OpenCart before syncing — the system does NOT create them.
- The `SECRET` in `.env` must EXACTLY match the `SECRET` in `db_bridge.php`.
- Secure your `db_bridge.php` — it executes raw SQL. Use a strong secret and consider IP restrictions.
- Price synced is from the "Standard Selling" price list in ERPNext.
- Product SKU in OpenCart = Item Code in ERPNext (unique identifier to match products).


---


## Troubleshooting

| Problem | Solution |
|---|---|
| "DB connection failed" error | Verify database credentials in `db_bridge.php` match your OpenCart `config.php`. |
| "Forbidden" error from bridge | `SECRET` in `.env` must exactly match `SECRET` in `db_bridge.php`. |
| 401 / 403 on webhook endpoints | Ensure ERPNext sends the correct `API_SECRET_KEY` in the `Authorization` header. |
| Products not syncing for a category | Verify category is listed in `category_configs.py` with exact ERPNext item group name. |
| Quantity showing 0 | Check warehouse names in `erp_settig['store']` match ERPNext exactly (incl. abbreviation). |
| Price showing 0 | Ensure the item has a price entry in the "Standard Selling" price list in ERPNext. |
| "No item codes found" warning | Item group name in `category_configs.py` doesn't match ERPNext. Check spelling/case. |
| Connection timeout errors | System retries up to 4 times. Check network connectivity to ERPNext and OpenCart. |


---

## License

This project is provided as-is for personal and commercial use.
