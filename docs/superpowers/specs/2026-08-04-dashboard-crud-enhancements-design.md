# Dashboard CRUD Enhancements — Design Spec

## 1. Context

Follow-up to the initial Gupta Building Materials FDE demo build (see `2026-08-03-gupta-traders-fde-demo-design.md`). The dashboard currently has four tabs (Overview, Orders, Customers, Suppliers), but:

- There's no page to view the product catalog.
- The Orders tab *is* the AI WhatsApp-parser tool — there's no actual order listing.
- Customers don't show phone numbers in the UI, even though the data is already there and is what links a WhatsApp sender to a real customer.
- There's no way to manually add a customer, order, supplier, or product — everything comes from the seeded data or the WhatsApp parser.
- Overview only shows a low-stock alert; there's no visibility into which customers carry the most outstanding credit.

This spec covers adding those without changing the existing data model.

## 2. Goals / Non-Goals

**Goals:**
- A Products page (view + manual add).
- A real Orders listing page (view + manual add), separate from the AI parser.
- The AI WhatsApp parser moved to its own "Parser" tab, functionally unchanged.
- Customers page shows phone numbers and supports editing them inline (so any customer missing one — now or in the future — can get one, since phone is the WhatsApp-to-customer matching key).
- Manual "Add Customer" (Customers page) and "Add Supplier" (Suppliers page) forms.
- Overview shows a Top-5-outstanding-customers widget alongside the existing low-stock alert.
- Every add-flow has a real backend endpoint and is wired end-to-end (no mock data).

**Non-Goals:**
- No schema/model changes — `Customer.phone`/`area` are already nullable columns; `Order.source` is a free-text column, no enum migration needed for a `"manual"` source value.
- No pagination or virtualized lists for the Products table — ~500 rows renders fine as one page for this demo's scale.
- Not touching the existing per-customer `GET /credit/{id}` N+1 fetch pattern already on the Customers page — unrelated to this work.
- No auth/permissions on the new write endpoints — matches the existing demo-scope posture (see original spec §2 Non-Goals).

## 3. Navigation

`frontend/src/App.jsx` tabs become: **Overview | Orders | Products | Customers | Suppliers | Parser**.

"Parser" is today's Orders-page content (paste-WhatsApp-message → `POST /agents/parse-order` → optional auto-created order) moved verbatim into its own page/tab. Orders becomes a pure listing + manual-add page.

## 4. Backend changes

### 4.1 `GET /orders` — enriched response

Currently returns `{id, customer_id, status, source}` per order — not enough for a real listing without N+1 calls. Change `list_orders` in `backend/app/routers/orders.py` to join `Customer` and `OrderItem`/`Product`, returning per order:

```json
{
  "id": 1, "order_date": "2026-08-01T10:00:00", "customer_id": 3,
  "customer_name": "Sharma Contractor", "source": "manual", "status": "pending",
  "total_amount": 12500.0,
  "items": [{"product_id": 5, "product_name": "UltraTech Cement", "qty": 10, "unit_price": 380.0}]
}
```

`OrderIn`/`create_order` are unchanged — this only touches the list response shape.

### 4.2 `PATCH /customers/{id}` — new endpoint

`backend/app/routers/customers.py`. New schema `CustomerUpdate` (all fields optional: `phone`, `area`, `name`). Partial update — only provided fields change. Returns `CustomerOut`. 404 if customer doesn't exist. This is what "unlocks" editing a phone number from the UI.

### 4.3 `GET /credit/top-outstanding` — new endpoint

`backend/app/routers/credit.py`. Query param `limit` (default 5). SQL aggregation over `credit_ledger` grouped by `customer_id` (`SUM(debit) - SUM(credit)`), joined to `customers` for `name`, ordered descending, limited. Returns:

```json
[{"customer_id": 12, "name": "Vinod Builders", "outstanding": 410000.0}, ...]
```

Done as one aggregate query rather than looping every customer in Python — this endpoint runs on every Overview page load.

### 4.4 No changes needed
`POST /products`, `POST /customers`, `POST /suppliers`, `POST /orders` already exist and already do exactly what's needed for the new "Add" forms — the frontend just needs to call them.

## 5. Frontend changes

### 5.1 Products page (new) — `frontend/src/pages/Products.jsx`
- Table: Name, Brand, Category, Unit, HSN Code, Stock.
- Text input filters the table client-side by name/brand/category (case-insensitive substring).
- "Add Product" form (name, brand, category, unit, hsn_code, current_stock) → `POST /products`, prepends to the table on success.

### 5.2 Orders page — rewritten `frontend/src/pages/Orders.jsx`
- Table: Order #, Date, Customer, Source, Items (summary string, e.g. "UltraTech Cement x10, TMT Bar x5"), Total, Status.
- "Add Order" form: customer `<select>` (from `GET /customers`), repeatable item rows (product `<select>` + qty + unit price, "add item" / remove-row controls), delivery address/time (optional text inputs). Submits with `source: "manual"` → `POST /orders`. On success, prepend the new order to the table and show the same credit-risk badge treatment the old parser flow used.

### 5.3 Parser page (new) — `frontend/src/pages/Parser.jsx`
Cut-and-paste of the current AI-parser section from `Orders.jsx` (textarea, sender-phone input, parse button, parsed-result card, created-order card with risk badge) — no functional changes.

### 5.4 Customers page — `frontend/src/pages/Customers.jsx`
- Add a **Phone** column.
- Inline edit: pencil icon next to the phone value → becomes a text input + save/cancel → `PATCH /customers/{id}` → updates row on success. Works the same whether the cell currently has a phone or is empty.
- "Add Customer" form (name, phone, area) → `POST /customers`, prepends to the table.

### 5.5 Suppliers page — `frontend/src/pages/Suppliers.jsx`
- "Add Supplier" form (name, contact) → `POST /suppliers`, prepends to the table.

### 5.6 Overview page — `frontend/src/pages/Overview.jsx`
- Keep the existing stat grid and low-stock alert unchanged.
- Add a "Top 5 Outstanding Customers" card fed by `GET /credit/top-outstanding?limit=5`: ranked list of name + outstanding amount.

### 5.7 `frontend/src/api.js`
None of the create/update calls exist yet (today's `api.js` is read-only: `getProducts`, `getOrders`, `getSuppliers`, `getCustomers`, `getRateCards`, `getCredit`, `parseOrder`). Add: `createCustomer(payload)`, `updateCustomer(id, patch)`, `createOrder(payload)`, `createProduct(payload)`, `createSupplier(payload)`, `getTopOutstandingCustomers(limit)`.

## 6. Testing

Matches existing conventions:
- Backend: pytest cases added to `test_orders_api.py` (enriched list shape), `test_customers_api.py` (PATCH endpoint, partial update, 404), `test_credit_api.py` (top-outstanding ordering/limit).
- Frontend: vitest + RTL for each new/changed component, mocking `api.js` — new `Products.test.jsx`, `Parser.test.jsx`; updates to `Orders.test.jsx`, `Customers.test.jsx`, `Suppliers.test.jsx`, `Overview.test.jsx`.
