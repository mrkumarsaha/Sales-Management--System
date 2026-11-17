"""
Sales Management System
Backend: Flask + SQLite
Frontend: HTML/CSS/JavaScript
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sales.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")


@app.after_request
def add_cors_headers(response):
    # Allows the UI to also be run from VS Code Live Server if needed.
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with closing(get_db()) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                price REAL NOT NULL CHECK(price >= 0),
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0)
            );

            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                total REAL NOT NULL CHECK(total >= 0),
                sale_date TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            );
        """)
        conn.commit()

        if conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"] == 0:
            conn.executescript("""
                INSERT INTO products (name, category, price, stock) VALUES
                    ('Wireless Mouse', 'Electronics', 15.99, 120),
                    ('Office Chair', 'Furniture', 89.50, 40),
                    ('Notebook Pack', 'Stationery', 4.25, 300);

                INSERT INTO customers (name, email, phone) VALUES
                    ('Ava Sharma', 'ava.sharma@example.com', '9876500001'),
                    ('Ravi Kumar', 'ravi.kumar@example.com', '9876500002');
            """)
            conn.commit()


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def error(message, status=400):
    return jsonify({"error": message}), status


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ----------------------------- Products ------------------------------------

@app.route("/api/products", methods=["GET"])
def get_products():
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows])


@app.route("/api/products", methods=["POST"])
def add_product():
    data = json_body()
    name = str(data.get("name") or "").strip()
    category = str(data.get("category") or "").strip()

    if not name:
        return error("Product name is required.")

    try:
        price = float(data.get("price"))
        stock = int(data.get("stock", 0))
    except (TypeError, ValueError):
        return error("Price must be a number and stock must be an integer.")

    if price < 0:
        return error("Price cannot be negative.")
    if stock < 0:
        return error("Stock cannot be negative.")

    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
            (name, category, price, stock),
        )
        conn.commit()
        return jsonify({"id": cur.lastrowid, "message": "Product added successfully."}), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = json_body()

    with closing(get_db()) as conn:
        existing = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not existing:
            return error("Product not found.", 404)

        name = str(data.get("name", existing["name"]) or "").strip()
        category = str(data.get("category", existing["category"] or "") or "").strip()

        try:
            price = float(data.get("price", existing["price"]))
            stock = int(data.get("stock", existing["stock"]))
        except (TypeError, ValueError):
            return error("Price must be a number and stock must be an integer.")

        if not name:
            return error("Product name is required.")
        if price < 0 or stock < 0:
            return error("Price and stock cannot be negative.")

        conn.execute(
            """UPDATE products
               SET name = ?, category = ?, price = ?, stock = ?
               WHERE id = ?""",
            (name, category, price, stock, product_id),
        )
        conn.commit()
        return jsonify({"updated": True})


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    with closing(get_db()) as conn:
        product = conn.execute(
            "SELECT id FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return error("Product not found.", 404)

        # Keep sales history consistent instead of silently cascading it.
        sales_count = conn.execute(
            "SELECT COUNT(*) AS c FROM sales WHERE product_id = ?", (product_id,)
        ).fetchone()["c"]
        if sales_count:
            return error(
                "This product has sales history and cannot be deleted. "
                "Delete its sales first if you really want to remove it."
            , 409)

        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return jsonify({"deleted": True})


# ----------------------------- Customers -----------------------------------

@app.route("/api/customers", methods=["GET"])
def get_customers():
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows])


@app.route("/api/customers", methods=["POST"])
def add_customer():
    data = json_body()
    name = str(data.get("name") or "").strip()
    email = str(data.get("email") or "").strip()
    phone = str(data.get("phone") or "").strip()

    if not name:
        return error("Customer name is required.")

    with closing(get_db()) as conn:
        cur = conn.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)",
            (name, email, phone),
        )
        conn.commit()
        return jsonify({"id": cur.lastrowid, "message": "Customer added successfully."}), 201


@app.route("/api/customers/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    with closing(get_db()) as conn:
        customer = conn.execute(
            "SELECT id FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if not customer:
            return error("Customer not found.", 404)

        sales_count = conn.execute(
            "SELECT COUNT(*) AS c FROM sales WHERE customer_id = ?", (customer_id,)
        ).fetchone()["c"]
        if sales_count:
            return error(
                "This customer has sales history and cannot be deleted. "
                "Delete the related sales first if you really want to remove the customer.",
                409,
            )

        conn.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        return jsonify({"deleted": True})


# -------------------------------- Sales ------------------------------------

@app.route("/api/sales", methods=["GET"])
def get_sales():
    with closing(get_db()) as conn:
        rows = conn.execute("""
            SELECT
                s.id,
                s.quantity,
                s.total,
                s.sale_date,
                p.id AS product_id,
                p.name AS product_name,
                p.price AS product_price,
                c.id AS customer_id,
                c.name AS customer_name
            FROM sales s
            JOIN products p ON p.id = s.product_id
            JOIN customers c ON c.id = s.customer_id
            ORDER BY s.id DESC
        """).fetchall()
        return jsonify([dict(row) for row in rows])


@app.route("/api/sales", methods=["POST"])
def add_sale():
    data = json_body()

    try:
        product_id = int(data.get("product_id"))
        customer_id = int(data.get("customer_id"))
        quantity = int(data.get("quantity"))
    except (TypeError, ValueError):
        return error("Product, customer and quantity must be valid values.")

    if product_id <= 0 or customer_id <= 0:
        return error("Product and customer are required.")
    if quantity <= 0:
        return error("Quantity must be a positive integer.")

    with closing(get_db()) as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        customer = conn.execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()

        if not product:
            return error("Product not found.", 404)
        if not customer:
            return error("Customer not found.", 404)
        if product["stock"] < quantity:
            return error(f"Insufficient stock. Available: {product['stock']}.")

        total = round(float(product["price"]) * quantity, 2)
        sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            cur = conn.execute(
                """INSERT INTO sales
                   (product_id, customer_id, quantity, total, sale_date)
                   VALUES (?, ?, ?, ?, ?)""",
                (product_id, customer_id, quantity, total, sale_date),
            )
            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (quantity, product_id),
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise

        return jsonify({"id": cur.lastrowid, "total": total}), 201


@app.route("/api/sales/<int:sale_id>", methods=["DELETE"])
def delete_sale(sale_id):
    with closing(get_db()) as conn:
        sale = conn.execute(
            "SELECT * FROM sales WHERE id = ?", (sale_id,)
        ).fetchone()
        if not sale:
            return error("Sale not found.", 404)

        # Restock the sold quantity when a sale is removed.
        conn.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (sale["quantity"], sale["product_id"]),
        )
        conn.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        conn.commit()
        return jsonify({"deleted": True})


# ----------------------------- Dashboard -----------------------------------

@app.route("/api/summary", methods=["GET"])
def get_summary():
    with closing(get_db()) as conn:
        total_revenue = conn.execute(
            "SELECT COALESCE(SUM(total), 0) AS v FROM sales"
        ).fetchone()["v"]
        total_sales = conn.execute(
            "SELECT COUNT(*) AS v FROM sales"
        ).fetchone()["v"]
        total_products = conn.execute(
            "SELECT COUNT(*) AS v FROM products"
        ).fetchone()["v"]
        total_customers = conn.execute(
            "SELECT COUNT(*) AS v FROM customers"
        ).fetchone()["v"]

        low_stock = conn.execute(
            """SELECT id, name, stock
               FROM products
               WHERE stock <= 10
               ORDER BY stock ASC, name ASC"""
        ).fetchall()

        top_products = conn.execute("""
            SELECT
                p.name,
                SUM(s.quantity) AS units_sold,
                ROUND(SUM(s.total), 2) AS revenue
            FROM sales s
            JOIN products p ON p.id = s.product_id
            GROUP BY p.id
            ORDER BY revenue DESC
            LIMIT 5
        """).fetchall()

        monthly_sales = conn.execute("""
            SELECT strftime('%Y-%m', sale_date) AS month,
                   ROUND(SUM(total), 2) AS revenue,
                   COUNT(*) AS sales_count
            FROM sales
            WHERE date(sale_date) >= date('now', 'start of month', '-5 months')
            GROUP BY strftime('%Y-%m', sale_date)
            ORDER BY month
        """).fetchall()

        category_sales = conn.execute("""
            SELECT COALESCE(NULLIF(TRIM(p.category), ''), 'Uncategorized') AS category,
                   ROUND(SUM(s.total), 2) AS revenue
            FROM sales s
            JOIN products p ON p.id = s.product_id
            GROUP BY COALESCE(NULLIF(TRIM(p.category), ''), 'Uncategorized')
            ORDER BY revenue DESC
        """).fetchall()

        return jsonify({
            "total_revenue": round(float(total_revenue or 0), 2),
            "total_sales": total_sales,
            "total_products": total_products,
            "total_customers": total_customers,
            "low_stock": [dict(row) for row in low_stock],
            "top_products": [dict(row) for row in top_products],
            "monthly_sales": [dict(row) for row in monthly_sales],
            "category_sales": [dict(row) for row in category_sales],
        })


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Route not found."}), 404


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
