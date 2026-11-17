"use strict";

// The frontend is served by Flask, so using a relative API path avoids
// localhost/127.0.0.1 port mismatches and CORS problems.
const API = window.location.port === "5000"
  ? "/api"
  : "http://127.0.0.1:5000/api";

function getElement(id) {
  return document.getElementById(id);
}

function money(value) {
  const amount = Number(value ?? 0);
  return Number.isFinite(amount) ? "₹" + amount.toFixed(2) : "₹0.00";
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}

function showError(message, elementId = null) {
  if (elementId) {
    const element = getElement(elementId);
    if (element) element.textContent = message;
  } else {
    alert(message);
  }
}

async function api(path, options = {}) {
  const response = await fetch(API + path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Request failed (${response.status})`);
  }

  return data;
}

// ----------------------------- Navigation ----------------------------------

document.querySelectorAll(".nav-btn").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach((item) => {
      item.classList.remove("active");
    });
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.classList.remove("active");
    });

    button.classList.add("active");
    const tab = getElement(button.dataset.tab);
    if (tab) tab.classList.add("active");

    // Refresh dashboard whenever the user opens it.
    if (button.dataset.tab === "dashboard") {
      loadDashboard().catch((error) => console.error(error));
    }
  });
});

// ----------------------------- Dashboard -----------------------------------

let monthlyRevenueChart = null;
let categoryRevenueChart = null;

function renderDashboardCharts(summary) {
  // Chart.js is loaded from the CDN in index.html.
  if (typeof Chart === "undefined") {
    console.warn("Chart.js could not load. Check your internet connection.");
    return;
  }

  const monthly = summary.monthly_sales || [];
  const monthlyLabels = monthly.map(item => item.month);
  const monthlyValues = monthly.map(item => Number(item.revenue || 0));

  const monthlyCanvas = getElement("monthly-revenue-chart");
  if (monthlyCanvas) {
    if (monthlyRevenueChart) monthlyRevenueChart.destroy();
    monthlyRevenueChart = new Chart(monthlyCanvas, {
      type: "bar",
      data: {
        labels: monthlyLabels,
        datasets: [{
          label: "Revenue (₹)",
          data: monthlyValues,
          backgroundColor: "rgba(67, 97, 238, 0.72)",
          borderColor: "#4361ee",
          borderWidth: 1,
          borderRadius: 7
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { callback: value => "₹" + value } }
        }
      }
    });
  }

  const categories = summary.category_sales || [];
  const categoryCanvas = getElement("category-chart");
  if (categoryCanvas) {
    if (categoryRevenueChart) categoryRevenueChart.destroy();
    categoryRevenueChart = new Chart(categoryCanvas, {
      type: "doughnut",
      data: {
        labels: categories.map(item => item.category),
        datasets: [{
          data: categories.map(item => Number(item.revenue || 0)),
          backgroundColor: ["#4361ee", "#2ec4b6", "#ff9f1c", "#e76f51", "#9b5de5", "#64748b"]
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } }
      }
    });
  }
}

async function loadDashboard() {
  const summary = await api("/summary");

  getElement("stat-revenue").textContent = money(summary.total_revenue);
  getElement("stat-sales").textContent = summary.total_sales ?? 0;
  getElement("stat-products").textContent = summary.total_products ?? 0;
  getElement("stat-customers").textContent = summary.total_customers ?? 0;

  const topBody = getElement("top-products-body");
  topBody.innerHTML = summary.top_products?.length
    ? summary.top_products.map((product) => `
        <tr>
          <td>${escapeHTML(product.name)}</td>
          <td>${escapeHTML(product.units_sold)}</td>
          <td>${money(product.revenue)}</td>
        </tr>
      `).join("")
    : `<tr><td colspan="3">No sales yet</td></tr>`;

  renderDashboardCharts(summary);

  const lowBody = getElement("low-stock-body");
  lowBody.innerHTML = summary.low_stock?.length
    ? summary.low_stock.map((product) => `
        <tr>
          <td>${escapeHTML(product.name)}</td>
          <td class="low-stock-flag">${escapeHTML(product.stock)}</td>
        </tr>
      `).join("")
    : `<tr><td colspan="2">All stock levels healthy</td></tr>`;
}

// ----------------------------- Products ------------------------------------

async function loadProducts() {
  const products = await api("/products");
  const body = getElement("products-body");

  if (!products.length) {
    body.innerHTML = `<tr><td colspan="6">No products found</td></tr>`;
    return products;
  }

  body.innerHTML = products.map((product) => `
    <tr>
      <td>${escapeHTML(product.id)}</td>
      <td>${escapeHTML(product.name)}</td>
      <td>${escapeHTML(product.category || "-")}</td>
      <td>${money(product.price)}</td>
      <td>${escapeHTML(product.stock)}</td>
      <td>
        <button class="delete-btn" data-id="${escapeHTML(product.id)}" data-type="product">
          Delete
        </button>
      </td>
    </tr>
  `).join("");

  return products;
}

getElement("product-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = getElement("p-name").value.trim();
  const category = getElement("p-category").value.trim();
  const price = Number(getElement("p-price").value);
  const stock = Number(getElement("p-stock").value);

  if (!name || !Number.isFinite(price) || price < 0 ||
      !Number.isInteger(stock) || stock < 0) {
    alert("Enter a valid product name, price and non-negative stock.");
    return;
  }

  try {
    await api("/products", {
      method: "POST",
      body: JSON.stringify({ name, category, price, stock })
    });

    event.target.reset();
    await Promise.all([loadProducts(), populateSaleDropdowns(), loadDashboard()]);
    alert("Product added successfully!");
  } catch (error) {
    showError("Failed to add product: " + error.message);
  }
});

// ----------------------------- Customers -----------------------------------

async function loadCustomers() {
  const customers = await api("/customers");
  const body = getElement("customers-body");

  if (!customers.length) {
    body.innerHTML = `<tr><td colspan="5">No customers found</td></tr>`;
    return customers;
  }

  body.innerHTML = customers.map((customer) => `
    <tr>
      <td>${escapeHTML(customer.id)}</td>
      <td>${escapeHTML(customer.name)}</td>
      <td>${escapeHTML(customer.email || "-")}</td>
      <td>${escapeHTML(customer.phone || "-")}</td>
      <td>
        <button class="delete-btn" data-id="${escapeHTML(customer.id)}" data-type="customer">
          Delete
        </button>
      </td>
    </tr>
  `).join("");

  return customers;
}

getElement("customer-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const name = getElement("c-name").value.trim();
  const email = getElement("c-email").value.trim();
  const phone = getElement("c-phone").value.trim();

  if (!name) {
    alert("Customer name is required.");
    return;
  }

  try {
    await api("/customers", {
      method: "POST",
      body: JSON.stringify({ name, email, phone })
    });

    event.target.reset();
    await Promise.all([loadCustomers(), populateSaleDropdowns(), loadDashboard()]);
    alert("Customer added successfully!");
  } catch (error) {
    showError("Failed to add customer: " + error.message);
  }
});

// ----------------------------- Sales ---------------------------------------

async function populateSaleDropdowns() {
  const [products, customers] = await Promise.all([
    api("/products"),
    api("/customers")
  ]);

  const productSelect = getElement("s-product");
  const customerSelect = getElement("s-customer");

  productSelect.innerHTML =
    `<option value="">Select product</option>` +
    products.map((product) => `
      <option value="${escapeHTML(product.id)}">
        ${escapeHTML(product.name)} (${escapeHTML(product.stock)} in stock)
      </option>
    `).join("");

  customerSelect.innerHTML =
    `<option value="">Select customer</option>` +
    customers.map((customer) => `
      <option value="${escapeHTML(customer.id)}">
        ${escapeHTML(customer.name)}
      </option>
    `).join("");
}

async function loadSales() {
  const sales = await api("/sales");
  const body = getElement("sales-body");

  if (!sales.length) {
    body.innerHTML = `<tr><td colspan="7">No sales found</td></tr>`;
    return sales;
  }

  body.innerHTML = sales.map((sale) => `
    <tr>
      <td>${escapeHTML(sale.id)}</td>
      <td>${escapeHTML(sale.sale_date)}</td>
      <td>${escapeHTML(sale.product_name)}</td>
      <td>${escapeHTML(sale.customer_name)}</td>
      <td>${escapeHTML(sale.quantity)}</td>
      <td>${money(sale.total)}</td>
      <td>
        <button class="delete-btn" data-id="${escapeHTML(sale.id)}" data-type="sale">
          Delete
        </button>
      </td>
    </tr>
  `).join("");

  return sales;
}

getElement("sale-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  const errorElement = getElement("sale-error");
  errorElement.textContent = "";

  const productId = getElement("s-product").value;
  const customerId = getElement("s-customer").value;
  const quantity = Number(getElement("s-quantity").value);

  if (!productId || !customerId ||
      !Number.isInteger(quantity) || quantity <= 0) {
    showError("Select a product, customer and enter a valid quantity.", "sale-error");
    return;
  }

  try {
    await api("/sales", {
      method: "POST",
      body: JSON.stringify({
        product_id: productId,
        customer_id: customerId,
        quantity
      })
    });

    event.target.reset();

    await Promise.all([
      loadSales(),
      loadProducts(),
      populateSaleDropdowns(),
      loadDashboard()
    ]);

    alert("Sale recorded successfully!");
  } catch (error) {
    showError(error.message, "sale-error");
  }
});

// ----------------------------- Delete --------------------------------------

document.body.addEventListener("click", async (event) => {
  const button = event.target.closest(".delete-btn");
  if (!button) return;

  const id = button.dataset.id;
  const type = button.dataset.type;

  const endpoints = {
    product: "/products/",
    customer: "/customers/",
    sale: "/sales/"
  };

  if (!id || !endpoints[type]) return;

  if (!confirm(`Are you sure you want to delete this ${type}?`)) return;

  try {
    button.disabled = true;

    await api(endpoints[type] + encodeURIComponent(id), {
      method: "DELETE"
    });

    if (type === "product") {
      await Promise.all([loadProducts(), populateSaleDropdowns(), loadDashboard()]);
    } else if (type === "customer") {
      await Promise.all([loadCustomers(), populateSaleDropdowns(), loadDashboard()]);
    } else {
      await Promise.all([
        loadSales(),
        loadProducts(),
        populateSaleDropdowns(),
        loadDashboard()
      ]);
    }

    alert(`${type[0].toUpperCase() + type.slice(1)} deleted successfully!`);
  } catch (error) {
    button.disabled = false;
    showError(`Could not delete ${type}: ${error.message}`);
  }
});

// ----------------------------- Initialization ------------------------------

async function init() {
  try {
    await Promise.all([
      loadDashboard(),
      loadProducts(),
      loadCustomers(),
      loadSales(),
      populateSaleDropdowns()
    ]);
    console.log("Sales Management System initialized successfully.");
  } catch (error) {
    console.error("Initialization error:", error);
    showError(
      "Could not connect to the backend. Start the app with: python app.py"
    );
  }
}

document.addEventListener("DOMContentLoaded", init);
