# Sales Management System

A simple Sales Management System built with **Python Flask + SQLite + HTML/CSS/JavaScript**.

## Features

- Product management: add, view and delete products
- Customer management: add, view and delete customers
- Sales management: record and delete sales
- Automatic stock deduction when a sale is recorded
- Automatic stock restoration when a sale is deleted
- Dashboard with revenue, sales, product/customer counts, top products and low-stock alerts
- Monthly revenue bar chart (last 6 months)
- Revenue-by-category doughnut chart (Chart.js)
- Indian Rupee (₹) currency formatting
- Input validation for price, stock and quantity
- Safe deletion: products/customers with sales history cannot be deleted accidentally
- Frontend uses `/api` relative URLs, so there is no frontend/backend port mismatch

## Run the project

Open a terminal in this folder:

```bash
cd sales_management
python -m pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

or:

```text
http://localhost:5000
```

## Important

Do **not** open `static/index.html` directly with double-click. Run `python app.py` first and open the Flask URL above.

The existing `sales.db` is kept so your current data is not unnecessarily deleted.

The dashboard charts use Chart.js from a CDN, so an internet connection is needed
for the chart library to load. The rest of the app continues to work without it.

## Project structure

```text
sales_management/
├── app.py
├── requirements.txt
├── sales.db
├── README.md
└── static/
    ├── index.html
    ├── style.css
    └── script.js
```

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend health check |
| GET | `/api/products` | List products |
| POST | `/api/products` | Add product |
| PUT | `/api/products/<id>` | Update product |
| DELETE | `/api/products/<id>` | Delete product |
| GET | `/api/customers` | List customers |
| POST | `/api/customers` | Add customer |
| DELETE | `/api/customers/<id>` | Delete customer |
| GET | `/api/sales` | List sales |
| POST | `/api/sales` | Record a sale |
| DELETE | `/api/sales/<id>` | Delete a sale and restore stock |
| GET | `/api/summary` | Dashboard statistics |
