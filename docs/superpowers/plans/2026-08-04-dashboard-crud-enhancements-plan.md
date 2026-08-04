# Dashboard CRUD Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Products page, turn Orders into a real order listing (moving the AI WhatsApp parser to its own tab), let customer phone numbers be seen and edited in the UI, and add manual "Add Customer" / "Add Order" / "Add Supplier" / "Add Product" forms — each wired to a real backend endpoint.

**Architecture:** No schema changes. Three backend additions (customer PATCH, credit top-outstanding aggregate, enriched order listing) plus new/rewritten React page components consuming them through `frontend/src/api.js`.

**Tech Stack:** FastAPI + SQLAlchemy + Postgres (backend, pytest); React + Vite (frontend, vitest + @testing-library/react). Existing CSS classes to reuse: `card`, `section-title`, `btn-primary`, `alert`/`alert-error`, `badge`/`badge-high`/`badge-medium`/`badge-low`, `empty-state`, plain `<table>`.

## Global Constraints

- No new database migrations — `Customer.phone`/`Customer.area` are already nullable columns; `Order.source` is a free-text `String(20)`, so a `"manual"` source value needs no schema change.
- Backend tests run with `cd backend && pytest`; `TEST_DATABASE_URL` is already set in `backend/.env` and loaded via `load_dotenv()` in `app/db.py` — no extra setup needed.
- Frontend tests run with `cd frontend && npm test` (= `vitest run`).
- Match existing code style: single-file page components (no extracted subcomponents), inline `useState`/`useEffect`, `api.js` as the only place `fetch` is called from.
- `backend/tests/test_orders_api.py` has a module-level `pytestmark = pytest.mark.skipif(not has_real_api_key(), ...)` because order creation invokes the live credit-risk agent — any new order test that does NOT go through `POST /orders` (e.g. testing `GET /orders`) must live in a separate test file so it isn't skipped when no API key is configured.

---

### Task 1: Backend — `PATCH /customers/{id}`

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/customers.py`
- Modify: `backend/tests/test_customers_api.py`

**Interfaces:**
- Produces: `CustomerUpdate` pydantic model (`backend/app/schemas.py`) with optional `name`, `phone`, `area`; `PATCH /customers/{customer_id}` endpoint returning `CustomerOut` (200) or 404.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_customers_api.py`:

```python
def test_patch_customer_updates_phone(db):
    created = client.post("/customers", json={"name": "Meena Traders"}).json()
    assert created["phone"] is None

    response = client.patch(f"/customers/{created['id']}", json={"phone": "9998887776"})
    assert response.status_code == 200
    assert response.json()["phone"] == "9998887776"

    fetched = client.get(f"/customers/{created['id']}").json()
    assert fetched["phone"] == "9998887776"


def test_patch_customer_leaves_unspecified_fields_untouched(db):
    created = client.post("/customers", json={"name": "Rakesh Traders", "area": "Rau"}).json()

    response = client.patch(f"/customers/{created['id']}", json={"phone": "9112233445"})
    assert response.status_code == 200
    assert response.json()["area"] == "Rau"


def test_patch_nonexistent_customer_returns_404(db):
    response = client.patch("/customers/999999", json={"phone": "9998887776"})
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_customers_api.py -v`
Expected: the 3 new tests FAIL with 405 Method Not Allowed (no PATCH route exists yet).

- [ ] **Step 3: Add the `CustomerUpdate` schema**

In `backend/app/schemas.py`, right after the existing `CustomerOut` class, add:

```python
class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    area: Optional[str] = None
```

- [ ] **Step 4: Add the PATCH endpoint**

In `backend/app/routers/customers.py`, change the import line to:

```python
from app.schemas import CustomerIn, CustomerOut, CustomerUpdate
```

Then add this endpoint (after `create_customer`, before `list_customers`):

```python
@router.patch("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(id=customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_customers_api.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas.py backend/app/routers/customers.py backend/tests/test_customers_api.py
git commit -m "feat: add PATCH /customers/{id} for editing phone/area/name"
```

---

### Task 2: Backend — `GET /credit/top-outstanding`

**Files:**
- Modify: `backend/app/routers/credit.py`
- Modify: `backend/tests/test_credit_api.py`

**Interfaces:**
- Produces: `GET /credit/top-outstanding?limit=<int>` (default 5) returning `[{"customer_id": int, "name": str, "outstanding": float}, ...]`, sorted descending by outstanding.
- Must be registered **before** the existing `@router.get("/{customer_id}")` route in the file, otherwise FastAPI routes a request for `/credit/top-outstanding` into the `{customer_id}` path parameter first and fails type conversion.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_credit_api.py`:

```python
def test_top_outstanding_customers_ranks_by_outstanding_desc(db):
    alpha = Customer(name="Alpha Traders")
    beta = Customer(name="Beta Traders")
    db.add_all([alpha, beta])
    db.commit()
    db.add(CreditLedger(customer_id=alpha.id, date=datetime.utcnow(), type="debit", amount=50000))
    db.add(CreditLedger(customer_id=beta.id, date=datetime.utcnow(), type="debit", amount=200000))
    db.commit()

    response = client.get("/credit/top-outstanding?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body[0] == {"customer_id": beta.id, "name": "Beta Traders", "outstanding": 200000.0}
    assert body[1] == {"customer_id": alpha.id, "name": "Alpha Traders", "outstanding": 50000.0}


def test_top_outstanding_customers_respects_limit(db):
    for i in range(3):
        customer = Customer(name=f"Customer {i}")
        db.add(customer)
        db.commit()
        db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow(), type="debit", amount=1000 * (i + 1)))
        db.commit()

    response = client.get("/credit/top-outstanding?limit=2")
    assert len(response.json()) == 2


def test_top_outstanding_customers_nets_credits_against_debits(db):
    customer = Customer(name="Gamma Traders")
    db.add(customer)
    db.commit()
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow(), type="debit", amount=100000))
    db.add(CreditLedger(customer_id=customer.id, date=datetime.utcnow(), type="credit", amount=30000))
    db.commit()

    response = client.get("/credit/top-outstanding?limit=5")
    assert response.json()[0]["outstanding"] == 70000.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_credit_api.py -v`
Expected: the 3 new tests FAIL (404 Not Found, or a 422 from `{customer_id}` trying to parse "top-outstanding" as an int).

- [ ] **Step 3: Implement the endpoint**

In `backend/app/routers/credit.py`, change the imports at the top to:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer, CreditLedger
```

Then insert this endpoint **immediately before** `def get_credit_ledger` (i.e., before the existing `@router.get("/{customer_id}")`):

```python
@router.get("/top-outstanding")
def get_top_outstanding_customers(limit: int = 5, db: Session = Depends(get_db)):
    signed_amount = case((CreditLedger.type == "debit", CreditLedger.amount), else_=-CreditLedger.amount)
    rows = (
        db.query(Customer.id, Customer.name, func.sum(signed_amount).label("outstanding"))
        .join(CreditLedger, CreditLedger.customer_id == Customer.id)
        .group_by(Customer.id, Customer.name)
        .order_by(func.sum(signed_amount).desc())
        .limit(limit)
        .all()
    )
    return [{"customer_id": r.id, "name": r.name, "outstanding": float(r.outstanding)} for r in rows]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_credit_api.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/credit.py backend/tests/test_credit_api.py
git commit -m "feat: add GET /credit/top-outstanding for the Overview dashboard"
```

---

### Task 3: Backend — enrich `GET /orders`

**Files:**
- Modify: `backend/app/routers/orders.py`
- Create: `backend/tests/test_orders_listing_api.py`

**Interfaces:**
- Produces: `GET /orders` now returns a list of `{id, order_date (ISO string), customer_id, customer_name, source, status, total_amount, items: [{product_id, product_name, qty, unit_price}]}`, newest first. `POST /orders` and `create_order_from_items` are unchanged.
- This is a new test file (not `test_orders_api.py`) specifically so it isn't affected by that file's `has_real_api_key` skip marker — none of these tests call `POST /orders`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_orders_listing_api.py`:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.models import Customer, Product, Order, OrderItem

client = TestClient(app)


def test_list_orders_includes_customer_and_item_details(db):
    customer = Customer(name="Priya Enterprises")
    db.add(customer)
    db.commit()
    product = Product(name="Ambuja Cement", brand="Ambuja", category="Cement", unit="bag", hsn_code="2523", current_stock=100)
    db.add(product)
    db.commit()
    order = Order(customer_id=customer.id, source="manual", total_amount=3800)
    order.items.append(OrderItem(product_id=product.id, qty=10, unit_price=380))
    db.add(order)
    db.commit()

    response = client.get("/orders")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    listed = body[0]
    assert listed["customer_name"] == "Priya Enterprises"
    assert listed["source"] == "manual"
    assert listed["total_amount"] == 3800.0
    assert listed["items"] == [{"product_id": product.id, "product_name": "Ambuja Cement", "qty": 10, "unit_price": 380.0}]


def test_list_orders_is_newest_first(db):
    customer = Customer(name="Rohan Enterprises")
    db.add(customer)
    db.commit()
    older = Order(customer_id=customer.id, source="manual", total_amount=100)
    db.add(older)
    db.commit()
    newer = Order(customer_id=customer.id, source="manual", total_amount=200)
    db.add(newer)
    db.commit()

    response = client.get("/orders")
    ids = [o["id"] for o in response.json()]
    assert ids.index(newer.id) < ids.index(older.id)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_orders_listing_api.py -v`
Expected: FAIL — `KeyError: 'customer_name'` (current response only has `id`, `customer_id`, `status`, `source`).

- [ ] **Step 3: Implement the enriched listing**

In `backend/app/routers/orders.py`, change the import line to:

```python
from app.models import Order, OrderItem, Customer, Product
```

Then replace the existing `list_orders` function with:

```python
@router.get("")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.order_date.desc()).all()
    result = []
    for o in orders:
        customer = db.query(Customer).filter_by(id=o.customer_id).first()
        items = []
        for item in o.items:
            product = db.query(Product).filter_by(id=item.product_id).first()
            items.append({
                "product_id": item.product_id,
                "product_name": product.name if product else f"Product {item.product_id}",
                "qty": item.qty,
                "unit_price": float(item.unit_price),
            })
        result.append({
            "id": o.id,
            "order_date": o.order_date.isoformat(),
            "customer_id": o.customer_id,
            "customer_name": customer.name if customer else f"Customer {o.customer_id}",
            "source": o.source,
            "status": o.status,
            "total_amount": float(o.total_amount),
            "items": items,
        })
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_orders_listing_api.py -v`
Expected: both tests PASS.

Also run the pre-existing order tests to confirm nothing else broke:
Run: `cd backend && pytest tests/test_orders_api.py -v`
Expected: PASS (or SKIPPED if no real API key is configured — that's the existing, unrelated behavior).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/orders.py backend/tests/test_orders_listing_api.py
git commit -m "feat: enrich GET /orders with customer name and item details for the Orders page"
```

---

### Task 4: Frontend — `api.js` write operations

**Files:**
- Modify: `frontend/src/api.js`

**Interfaces:**
- Produces: `api.createCustomer(payload)`, `api.updateCustomer(id, patch)`, `api.createOrder(payload)`, `api.createProduct(payload)`, `api.createSupplier(payload)`, `api.getTopOutstandingCustomers(limit = 5)`. All POST/PATCH helpers `JSON.stringify` the payload and reuse the existing `request()` helper (which already sets `Content-Type: application/json` and throws on non-OK responses).
- Consumed by: Tasks 5–11 (Products, Orders, Parser, Customers, Suppliers, Overview pages).

- [ ] **Step 1: Add the new functions**

Replace the full contents of `frontend/src/api.js` with:

```js
const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) throw new Error(`Request to ${path} failed: ${response.status}`)
  return response.json()
}

export const api = {
  getProducts: () => request('/products'),
  getOrders: () => request('/orders'),
  getSuppliers: () => request('/suppliers'),
  getCustomers: () => request('/customers'),
  getRateCards: () => request('/suppliers/rate-cards'),
  getCredit: (customerId) => request(`/credit/${customerId}`),
  getTopOutstandingCustomers: (limit = 5) => request(`/credit/top-outstanding?limit=${limit}`),
  parseOrder: (rawText, senderPhone) => request('/agents/parse-order', {
    method: 'POST',
    body: JSON.stringify({ raw_text: rawText, sender_phone: senderPhone || undefined }),
  }),
  createCustomer: (payload) => request('/customers', { method: 'POST', body: JSON.stringify(payload) }),
  updateCustomer: (id, patch) => request(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  createOrder: (payload) => request('/orders', { method: 'POST', body: JSON.stringify(payload) }),
  createProduct: (payload) => request('/products', { method: 'POST', body: JSON.stringify(payload) }),
  createSupplier: (payload) => request('/suppliers', { method: 'POST', body: JSON.stringify(payload) }),
}
```

- [ ] **Step 2: Run the full frontend test suite to confirm nothing broke**

Run: `cd frontend && npm test`
Expected: all existing tests still PASS (this file has no dedicated test — every page test mocks `../api` entirely, so these additions are exercised by Tasks 5–11's tests instead).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.js
git commit -m "feat: add create/update API client functions for customers, orders, products, suppliers"
```

---

### Task 5: Frontend — Products page

**Files:**
- Create: `frontend/src/pages/Products.jsx`
- Create: `frontend/src/pages/Products.test.jsx`

**Interfaces:**
- Consumes: `api.getProducts()` (existing, returns `[{id, name, brand, category, unit, hsn_code, current_stock}]`), `api.createProduct(payload)` (Task 4).
- Produces: default-exported `Products` component, to be wired into `App.jsx` in Task 8.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Products.test.jsx`:

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Products from './Products'
import { api } from '../api'

vi.mock('../api')

describe('Products', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([
      { id: 1, name: 'Ambuja Cement', brand: 'Ambuja', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 340 },
      { id: 2, name: 'TMT Sariya 10mm', brand: 'Generic', category: 'Steel', unit: 'ton', hsn_code: '7213', current_stock: 8 },
    ])
  })

  it('lists all products', async () => {
    render(<Products />)
    await waitFor(() => expect(screen.getByText('Ambuja Cement')).toBeInTheDocument())
    expect(screen.getByText('TMT Sariya 10mm')).toBeInTheDocument()
  })

  it('filters products by search text', async () => {
    render(<Products />)
    await waitFor(() => expect(screen.getByText('Ambuja Cement')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/filter/i), { target: { value: 'sariya' } })
    expect(screen.queryByText('Ambuja Cement')).not.toBeInTheDocument()
    expect(screen.getByText('TMT Sariya 10mm')).toBeInTheDocument()
  })

  it('adds a new product', async () => {
    api.createProduct.mockResolvedValue({ id: 3, name: 'Birla Cement', brand: 'Birla', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 100 })
    render(<Products />)
    await waitFor(() => expect(screen.getByText('Ambuja Cement')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Birla Cement' } })
    fireEvent.change(screen.getByLabelText('Brand'), { target: { value: 'Birla' } })
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'Cement' } })
    fireEvent.change(screen.getByLabelText('Unit'), { target: { value: 'bag' } })
    fireEvent.change(screen.getByLabelText('HSN Code'), { target: { value: '2523' } })
    fireEvent.change(screen.getByLabelText('Current Stock'), { target: { value: '100' } })
    fireEvent.click(screen.getByRole('button', { name: /add product/i }))

    await waitFor(() => expect(screen.getByText('Birla Cement')).toBeInTheDocument())
    expect(api.createProduct).toHaveBeenCalledWith({
      name: 'Birla Cement', brand: 'Birla', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 100,
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Products.test.jsx`
Expected: FAIL — `Failed to resolve import "./Products"` (file doesn't exist yet).

- [ ] **Step 3: Implement the Products page**

Create `frontend/src/pages/Products.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Products() {
  const [products, setProducts] = useState([])
  const [filterText, setFilterText] = useState('')
  const [form, setForm] = useState({ name: '', brand: '', category: '', unit: '', hsn_code: '', current_stock: '' })
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getProducts().then(setProducts).catch(() => {})
  }, [])

  const filtered = products.filter((p) => {
    const needle = filterText.trim().toLowerCase()
    if (!needle) return true
    return [p.name, p.brand, p.category].some((field) => field?.toLowerCase().includes(needle))
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const created = await api.createProduct({ ...form, current_stock: Number(form.current_stock) || 0 })
      setProducts((prev) => [created, ...prev])
      setForm({ name: '', brand: '', category: '', unit: '', hsn_code: '', current_stock: '' })
    } catch (err) {
      setError('Could not add this product. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section>
      <h2>Products</h2>
      <div className="card">
        <div className="section-title">Add Product</div>
        <form onSubmit={handleSubmit}>
          <label htmlFor="product-name">Name</label>
          <input type="text" id="product-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <label htmlFor="product-brand">Brand</label>
          <input type="text" id="product-brand" value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} required />
          <label htmlFor="product-category">Category</label>
          <input type="text" id="product-category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required />
          <label htmlFor="product-unit">Unit</label>
          <input type="text" id="product-unit" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} required />
          <label htmlFor="product-hsn">HSN Code</label>
          <input type="text" id="product-hsn" value={form.hsn_code} onChange={(e) => setForm({ ...form, hsn_code: e.target.value })} required />
          <label htmlFor="product-stock">Current Stock</label>
          <input type="text" id="product-stock" value={form.current_stock} onChange={(e) => setForm({ ...form, current_stock: e.target.value })} />
          <button className="btn-primary" type="submit" disabled={isSaving}>{isSaving ? 'Adding…' : 'Add product'}</button>
        </form>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <div className="alert-title">Add failed</div>
          {error}
        </div>
      )}

      <div className="card">
        <div className="section-title">Catalog</div>
        <label htmlFor="product-filter">Filter</label>
        <input type="text" id="product-filter" value={filterText} onChange={(e) => setFilterText(e.target.value)} placeholder="Search by name, brand, or category" />
        <table>
          <thead>
            <tr><th>Name</th><th>Brand</th><th>Category</th><th>Unit</th><th>HSN</th><th>Stock</th></tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id}>
                <td>{p.name}</td>
                <td>{p.brand}</td>
                <td>{p.category}</td>
                <td>{p.unit}</td>
                <td>{p.hsn_code}</td>
                <td>{p.current_stock}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && <p className="empty-state">No products match.</p>}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Products.test.jsx`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Products.jsx frontend/src/pages/Products.test.jsx
git commit -m "feat: add Products page with catalog listing, filter, and manual add form"
```

---

### Task 6: Frontend — extract the AI parser into its own Parser page

**Files:**
- Create: `frontend/src/pages/Parser.jsx`
- Create: `frontend/src/pages/Parser.test.jsx`

**Interfaces:**
- Consumes: `api.parseOrder(rawText, senderPhone)` (existing, unchanged).
- Produces: default-exported `Parser` component, to be wired into `App.jsx` in Task 8. Functionally identical to the AI-parser section currently embedded in `Orders.jsx`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/Parser.test.jsx` (this is the current `Orders.test.jsx` content, minus the `getOrders` mock which no longer applies):

```jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Parser from './Parser'
import { api } from '../api'

vi.mock('../api')

describe('Parser', () => {
  beforeEach(() => {
    api.parseOrder.mockResolvedValue({
      items: [{ product_hint: 'TMT Sariya 10mm', qty: 2, unit: 'ton' }],
      delivery_address: 'Sharma site',
      delivery_time: 'tomorrow morning',
    })
  })

  it('parses a pasted WhatsApp message and shows the structured result', async () => {
    render(<Parser />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), {
      target: { value: 'bhai 10mm sariya 2 ton kal subah Sharma site pe' },
    })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByText(/Sharma site/)).toBeInTheDocument())
    expect(screen.getByText(/TMT Sariya 10mm/)).toBeInTheDocument()
  })

  it('shows an error message if parsing fails', async () => {
    api.parseOrder.mockRejectedValue(new Error('API error'))
    render(<Parser />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), { target: { value: 'test message' } })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('shows the created order and risk badge when parseOrder returns one', async () => {
    api.parseOrder.mockResolvedValue({
      items: [{ product_hint: 'TMT Sariya 10mm', qty: 2, unit: 'ton' }],
      delivery_address: 'Sharma site',
      delivery_time: 'tomorrow morning',
      created_order: {
        id: 42,
        customer_id: 7,
        status: 'pending',
        source: 'whatsapp',
        total_amount: 350000,
        credit_risk: { risk_level: 'high', total_exposure: 760000, recommendation: 'Require advance payment.' },
      },
    })
    render(<Parser />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), { target: { value: 'test' } })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByText(/Order #42/)).toBeInTheDocument())
    expect(screen.getByText(/high risk/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Parser.test.jsx`
Expected: FAIL — `Failed to resolve import "./Parser"`.

- [ ] **Step 3: Implement the Parser page**

Create `frontend/src/pages/Parser.jsx`:

```jsx
import { useState } from 'react'
import { api } from '../api'

function riskBadgeClass(riskLevel) {
  if (riskLevel === 'high') return 'badge badge-high'
  if (riskLevel === 'medium') return 'badge badge-medium'
  if (riskLevel === 'low') return 'badge badge-low'
  return 'badge'
}

export default function Parser() {
  const [rawText, setRawText] = useState('')
  const [senderPhone, setSenderPhone] = useState('')
  const [parsed, setParsed] = useState(null)
  const [parseError, setParseError] = useState(null)
  const [isParsing, setIsParsing] = useState(false)

  const handleParse = async () => {
    setIsParsing(true)
    setParseError(null)
    try {
      const result = await api.parseOrder(rawText, senderPhone)
      setParsed(result)
    } catch (err) {
      setParseError('Could not parse this message. Please try again.')
    } finally {
      setIsParsing(false)
    }
  }

  return (
    <section>
      <h2>WhatsApp Parser</h2>
      <div className="card">
        <div className="section-title">AI Order Parser</div>
        <label htmlFor="whatsapp-input">Paste WhatsApp message</label>
        <textarea id="whatsapp-input" value={rawText} onChange={(e) => setRawText(e.target.value)} placeholder="e.g. bhai 10mm sariya 2 ton pipe 1 inch 50 piece kal subah Sharma site pe bhijwa dena" />
        <label htmlFor="sender-phone-input">Sender phone (optional — links to a real customer and creates the order)</label>
        <input type="text" id="sender-phone-input" value={senderPhone} onChange={(e) => setSenderPhone(e.target.value)} placeholder="+91XXXXXXXXXX" />
        <div>
          <button className="btn-primary" onClick={handleParse} disabled={!rawText.trim() || isParsing}>
            {isParsing ? 'Parsing…' : 'Parse order'}
          </button>
        </div>
      </div>

      {parseError && (
        <div className="alert alert-error" role="alert">
          <div className="alert-title">Parse failed</div>
          {parseError}
        </div>
      )}

      {parsed && (
        <div className="card">
          <div className="section-title">Parsed Result</div>
          <p><strong>Delivery:</strong> {parsed.delivery_address} — {parsed.delivery_time}</p>
          <ul>
            {parsed.items.map((item, i) => (
              <li key={i}>{item.product_hint}: {item.qty} {item.unit}</li>
            ))}
          </ul>
        </div>
      )}

      {parsed?.created_order && (
        <div className="card">
          <div className="section-title">Order Created</div>
          <p>Order #{parsed.created_order.id} — ₹{parsed.created_order.total_amount.toLocaleString()}</p>
          <span className={riskBadgeClass(parsed.created_order.credit_risk.risk_level)}>
            {parsed.created_order.credit_risk.risk_level} risk
          </span>
          <p className="muted">{parsed.created_order.credit_risk.recommendation}</p>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Parser.test.jsx`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Parser.jsx frontend/src/pages/Parser.test.jsx
git commit -m "feat: extract AI WhatsApp parser into its own Parser page"
```

---

### Task 7: Frontend — rewrite Orders page as a real listing + manual add form

**Files:**
- Modify: `frontend/src/pages/Orders.jsx` (full rewrite)
- Modify: `frontend/src/pages/Orders.test.jsx` (full rewrite)

**Interfaces:**
- Consumes: `api.getOrders()` (Task 3's enriched shape), `api.getCustomers()` (existing), `api.getProducts()` (existing), `api.createOrder(payload)` (Task 4). `createOrder`'s response shape is `{id, customer_id, status, source, total_amount, credit_risk}` (from `create_order_from_items` in `backend/app/routers/orders.py`) — NOT the enriched listing shape, so after creating an order the page must re-fetch the list rather than construct an enriched row itself.
- Produces: default-exported `Orders` component (replaces the old parser-based one), wired into `App.jsx` (already imported there; no App.jsx change needed for the import path, only Task 8's tab reordering).

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/pages/Orders.test.jsx`:

```jsx
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Orders from './Orders'
import { api } from '../api'

vi.mock('../api')

describe('Orders', () => {
  beforeEach(() => {
    api.getOrders.mockResolvedValue([
      {
        id: 1, order_date: '2026-08-01T10:00:00', customer_id: 3, customer_name: 'Sharma Contractor',
        source: 'manual', status: 'pending', total_amount: 3800,
        items: [{ product_id: 1, product_name: 'Ambuja Cement', qty: 10, unit_price: 380 }],
      },
    ])
    api.getCustomers.mockResolvedValue([{ id: 3, name: 'Sharma Contractor', phone: '9876543210', area: 'Indore' }])
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement', brand: 'Ambuja', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 340 }])
  })

  it('lists existing orders with customer and item details', async () => {
    render(<Orders />)
    await waitFor(() => expect(screen.getByRole('cell', { name: 'Sharma Contractor' })).toBeInTheDocument())
    expect(screen.getByText(/Ambuja Cement x10/)).toBeInTheDocument()
  })

  it('creates a new order and shows the risk badge', async () => {
    api.createOrder.mockResolvedValue({
      id: 42, customer_id: 3, status: 'pending', source: 'manual', total_amount: 3800,
      credit_risk: { risk_level: 'low', total_exposure: 3800, recommendation: 'Proceed as normal.' },
    })
    render(<Orders />)
    await waitFor(() => expect(screen.getByLabelText('Customer')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Customer'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Product'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Unit price'), { target: { value: '380' } })
    fireEvent.click(screen.getByRole('button', { name: /create order/i }))

    await waitFor(() => expect(screen.getByText(/Order #42/)).toBeInTheDocument())
    expect(screen.getByText(/low risk/i)).toBeInTheDocument()
    expect(api.createOrder).toHaveBeenCalledWith({
      customer_id: 3, source: 'manual', delivery_address: undefined, delivery_time: undefined,
      items: [{ product_id: 1, qty: 10, unit_price: 380 }],
    })
  })

  it('shows an error message if order creation fails', async () => {
    api.createOrder.mockRejectedValue(new Error('API error'))
    render(<Orders />)
    await waitFor(() => expect(screen.getByLabelText('Customer')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Customer'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Product'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Unit price'), { target: { value: '380' } })
    fireEvent.click(screen.getByRole('button', { name: /create order/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Orders.test.jsx`
Expected: FAIL — the current `Orders.jsx` has no `Customer`/`Product`/`Quantity`/`Unit price` labeled fields and no order table with a "Sharma Contractor" cell.

- [ ] **Step 3: Implement the rewritten Orders page**

Replace the full contents of `frontend/src/pages/Orders.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

function riskBadgeClass(riskLevel) {
  if (riskLevel === 'high') return 'badge badge-high'
  if (riskLevel === 'medium') return 'badge badge-medium'
  if (riskLevel === 'low') return 'badge badge-low'
  return 'badge'
}

const emptyItem = () => ({ product_id: '', qty: '', unit_price: '' })

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [customers, setCustomers] = useState([])
  const [products, setProducts] = useState([])
  const [customerId, setCustomerId] = useState('')
  const [deliveryAddress, setDeliveryAddress] = useState('')
  const [deliveryTime, setDeliveryTime] = useState('')
  const [items, setItems] = useState([emptyItem()])
  const [createdOrder, setCreatedOrder] = useState(null)
  const [error, setError] = useState(null)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    api.getOrders().then(setOrders).catch(() => {})
    api.getCustomers().then(setCustomers).catch(() => {})
    api.getProducts().then(setProducts).catch(() => {})
  }, [])

  const updateItem = (index, field, value) => {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, [field]: value } : it)))
  }

  const addItemRow = () => setItems((prev) => [...prev, emptyItem()])
  const removeItemRow = (index) => setItems((prev) => prev.filter((_, i) => i !== index))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const payload = {
        customer_id: Number(customerId),
        source: 'manual',
        delivery_address: deliveryAddress || undefined,
        delivery_time: deliveryTime || undefined,
        items: items.map((it) => ({
          product_id: Number(it.product_id), qty: Number(it.qty), unit_price: Number(it.unit_price),
        })),
      }
      const created = await api.createOrder(payload)
      setCreatedOrder(created)
      setCustomerId('')
      setDeliveryAddress('')
      setDeliveryTime('')
      setItems([emptyItem()])
      api.getOrders().then(setOrders).catch(() => {})
    } catch (err) {
      setError('Could not create this order. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section>
      <h2>Orders</h2>
      <div className="card">
        <div className="section-title">Add Order</div>
        <form onSubmit={handleSubmit}>
          <label htmlFor="order-customer">Customer</label>
          <select id="order-customer" value={customerId} onChange={(e) => setCustomerId(e.target.value)} required>
            <option value="">Select a customer</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          {items.map((item, index) => (
            <div key={index}>
              <label htmlFor={`order-item-product-${index}`}>Product</label>
              <select
                id={`order-item-product-${index}`}
                value={item.product_id}
                onChange={(e) => updateItem(index, 'product_id', e.target.value)}
                required
              >
                <option value="">Select a product</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
              <label htmlFor={`order-item-qty-${index}`}>Quantity</label>
              <input type="text" id={`order-item-qty-${index}`} value={item.qty} onChange={(e) => updateItem(index, 'qty', e.target.value)} required />
              <label htmlFor={`order-item-price-${index}`}>Unit price</label>
              <input type="text" id={`order-item-price-${index}`} value={item.unit_price} onChange={(e) => updateItem(index, 'unit_price', e.target.value)} required />
              {items.length > 1 && (
                <button type="button" onClick={() => removeItemRow(index)}>Remove item</button>
              )}
            </div>
          ))}
          <button type="button" onClick={addItemRow}>Add item</button>

          <label htmlFor="order-delivery-address">Delivery address (optional)</label>
          <input type="text" id="order-delivery-address" value={deliveryAddress} onChange={(e) => setDeliveryAddress(e.target.value)} />
          <label htmlFor="order-delivery-time">Delivery time (optional)</label>
          <input type="text" id="order-delivery-time" value={deliveryTime} onChange={(e) => setDeliveryTime(e.target.value)} />

          <button className="btn-primary" type="submit" disabled={!customerId || isSaving}>
            {isSaving ? 'Creating…' : 'Create order'}
          </button>
        </form>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <div className="alert-title">Create failed</div>
          {error}
        </div>
      )}

      {createdOrder && (
        <div className="card">
          <div className="section-title">Order Created</div>
          <p>Order #{createdOrder.id} — ₹{createdOrder.total_amount.toLocaleString()}</p>
          <span className={riskBadgeClass(createdOrder.credit_risk.risk_level)}>
            {createdOrder.credit_risk.risk_level} risk
          </span>
          <p className="muted">{createdOrder.credit_risk.recommendation}</p>
        </div>
      )}

      <div className="card">
        <div className="section-title">All Orders</div>
        {orders.length === 0 ? (
          <p className="empty-state">No orders yet.</p>
        ) : (
          <table>
            <thead>
              <tr><th>Order #</th><th>Date</th><th>Customer</th><th>Source</th><th>Items</th><th>Total</th><th>Status</th></tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.id}</td>
                  <td>{new Date(o.order_date).toLocaleDateString()}</td>
                  <td>{o.customer_name}</td>
                  <td>{o.source}</td>
                  <td>{o.items.map((it) => `${it.product_name} x${it.qty}`).join(', ')}</td>
                  <td>₹{o.total_amount.toLocaleString()}</td>
                  <td>{o.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Orders.test.jsx`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Orders.jsx frontend/src/pages/Orders.test.jsx
git commit -m "feat: rewrite Orders page as a real order listing with a manual add-order form"
```

---

### Task 8: Frontend — nav update (Products + Parser tabs)

**Files:**
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/App.test.jsx`

**Interfaces:**
- Consumes: `Products` (Task 5), `Parser` (Task 6), `Orders` (Task 7) default exports.
- Produces: nav order `Overview | Orders | Products | Customers | Suppliers | Parser`.

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/App.test.jsx`:

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from './App'
import { api } from './api'

vi.mock('./api')

describe('App', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([])
    api.getOrders.mockResolvedValue([])
    api.getTopOutstandingCustomers.mockResolvedValue([])
    api.getCustomers.mockResolvedValue([])
  })

  it('renders all tabs and defaults to Overview', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Orders' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Products' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Customers' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Suppliers' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Parser' })).toBeInTheDocument()
  })

  it('switches tabs on click', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('tab', { name: 'Orders' }))
    expect(screen.getByRole('tab', { name: 'Orders' })).toHaveAttribute('aria-selected', 'true')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/App.test.jsx`
Expected: FAIL — no tab named "Products" or "Parser" yet.

- [ ] **Step 3: Update the nav**

Replace the full contents of `frontend/src/App.jsx`:

```jsx
import { useState } from 'react'
import Overview from './pages/Overview'
import Orders from './pages/Orders'
import Products from './pages/Products'
import Customers from './pages/Customers'
import Suppliers from './pages/Suppliers'
import Parser from './pages/Parser'

const TABS = {
  Overview: Overview,
  Orders: Orders,
  Products: Products,
  Customers: Customers,
  Suppliers: Suppliers,
  Parser: Parser,
}

export default function App() {
  const [activeTab, setActiveTab] = useState('Overview')
  const ActiveComponent = TABS[activeTab]

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">Gupta Building Materials</span>
          <span className="brand-tag">Indore, Madhya Pradesh</span>
        </div>
        <nav className="tabs" role="tablist">
          {Object.keys(TABS).map((tab) => (
            <button
              key={tab}
              className="tab"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>
      <main className="page">
        <ActiveComponent />
      </main>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/App.test.jsx`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx frontend/src/App.test.jsx
git commit -m "feat: add Products and Parser tabs to the dashboard nav"
```

---

### Task 9: Frontend — Customers page: phone column, inline edit, add-customer form

**Files:**
- Modify: `frontend/src/pages/Customers.jsx`
- Modify: `frontend/src/pages/Customers.test.jsx`

**Interfaces:**
- Consumes: `api.getCustomers()` / `api.getCredit(id)` (existing, unchanged), `api.updateCustomer(id, patch)` and `api.createCustomer(payload)` (Task 4).
- Produces: default-exported `Customers` component, same `{ customers }` optional prop as before (kept for the existing "high-risk badge" test).

- [ ] **Step 1: Write the failing tests**

Replace the full contents of `frontend/src/pages/Customers.test.jsx`:

```jsx
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Customers from './Customers'
import { api } from '../api'

vi.mock('../api')

describe('Customers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a high-risk badge for a customer over 60 days overdue', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 410000, oldest_days_overdue: 82 })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders' }]} />)

    await waitFor(() => expect(screen.getByText('Vinod Builders')).toBeInTheDocument())
    expect(screen.getByText(/high risk/i)).toBeInTheDocument()
  })

  it('fetches its own customer list when no customers prop is given', async () => {
    api.getCustomers.mockResolvedValue([{ id: 2, name: 'Sharma Contractor' }])
    api.getCredit.mockResolvedValue({ total_outstanding: 50000, oldest_days_overdue: 10 })

    render(<Customers />)

    await waitFor(() => expect(screen.getByText('Sharma Contractor')).toBeInTheDocument())
    expect(api.getCustomers).toHaveBeenCalled()
  })

  it('displays the customer phone number', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 0, oldest_days_overdue: 0 })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders', phone: '9876543210' }]} />)

    await waitFor(() => expect(screen.getByText('9876543210')).toBeInTheDocument())
  })

  it('edits a missing phone number inline', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 0, oldest_days_overdue: 0 })
    api.updateCustomer.mockResolvedValue({ id: 1, name: 'Vinod Builders', phone: '9998887776', area: null })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders', phone: null }]} />)

    const row = await screen.findByRole('row', { name: /Vinod Builders/i })
    fireEvent.click(within(row).getByRole('button', { name: /edit/i }))
    fireEvent.change(within(row).getByRole('textbox', { name: /phone/i }), { target: { value: '9998887776' } })
    fireEvent.click(within(row).getByRole('button', { name: /save/i }))

    await waitFor(() => expect(api.updateCustomer).toHaveBeenCalledWith(1, { phone: '9998887776' }))
    expect(await screen.findByText('9998887776')).toBeInTheDocument()
  })

  it('adds a new customer', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 0, oldest_days_overdue: 0 })
    api.createCustomer.mockResolvedValue({ id: 3, name: 'Meena Traders', phone: '9001122334', area: 'Rau' })
    render(<Customers customers={[]} />)

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Meena Traders' } })
    fireEvent.change(screen.getByLabelText('Phone'), { target: { value: '9001122334' } })
    fireEvent.change(screen.getByLabelText('Area'), { target: { value: 'Rau' } })
    fireEvent.click(screen.getByRole('button', { name: /add customer/i }))

    await waitFor(() => expect(screen.getByText('Meena Traders')).toBeInTheDocument())
    expect(api.createCustomer).toHaveBeenCalledWith({ name: 'Meena Traders', phone: '9001122334', area: 'Rau' })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/pages/Customers.test.jsx`
Expected: the 3 new tests FAIL (no phone column, no Edit/Save buttons, no Add Customer form yet).

- [ ] **Step 3: Implement the updated Customers page**

Replace the full contents of `frontend/src/pages/Customers.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

function riskBadge(agingDays) {
  if (agingDays > 60) return 'High risk'
  if (agingDays > 30) return 'Medium risk'
  return 'Low risk'
}

function riskBadgeClass(agingDays) {
  if (agingDays > 60) return 'badge badge-high'
  if (agingDays > 30) return 'badge badge-medium'
  return 'badge badge-low'
}

export default function Customers({ customers: customersProp }) {
  const [customers, setCustomers] = useState(customersProp || [])
  const [aging, setAging] = useState({})
  const [editingId, setEditingId] = useState(null)
  const [editingPhone, setEditingPhone] = useState('')
  const [form, setForm] = useState({ name: '', phone: '', area: '' })
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!customersProp) {
      api.getCustomers().then(setCustomers).catch(() => {})
    }
  }, [customersProp])

  useEffect(() => {
    customers.forEach((c) => {
      api.getCredit(c.id).then((result) => setAging((prev) => ({ ...prev, [c.id]: result }))).catch(() => {})
    })
  }, [customers])

  const startEditingPhone = (customer) => {
    setEditingId(customer.id)
    setEditingPhone(customer.phone || '')
  }

  const cancelEditingPhone = () => {
    setEditingId(null)
    setEditingPhone('')
  }

  const savePhone = async (customerId) => {
    try {
      const updated = await api.updateCustomer(customerId, { phone: editingPhone })
      setCustomers((prev) => prev.map((c) => (c.id === customerId ? updated : c)))
    } catch (err) {
      setError('Could not update this phone number. Please try again.')
    } finally {
      setEditingId(null)
      setEditingPhone('')
    }
  }

  const handleAddCustomer = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const created = await api.createCustomer(form)
      setCustomers((prev) => [created, ...prev])
      setForm({ name: '', phone: '', area: '' })
    } catch (err) {
      setError('Could not add this customer. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section>
      <h2>Customers</h2>
      <div className="card">
        <div className="section-title">Add Customer</div>
        <form onSubmit={handleAddCustomer}>
          <label htmlFor="customer-name">Name</label>
          <input type="text" id="customer-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <label htmlFor="customer-phone">Phone</label>
          <input type="text" id="customer-phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+91XXXXXXXXXX" />
          <label htmlFor="customer-area">Area</label>
          <input type="text" id="customer-area" value={form.area} onChange={(e) => setForm({ ...form, area: e.target.value })} />
          <button className="btn-primary" type="submit" disabled={!form.name.trim() || isSaving}>
            {isSaving ? 'Adding…' : 'Add customer'}
          </button>
        </form>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <div className="alert-title">Action failed</div>
          {error}
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr><th>Customer</th><th>Phone</th><th>Outstanding</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>
                  {editingId === c.id ? (
                    <>
                      <input
                        type="text"
                        aria-label="Phone number"
                        value={editingPhone}
                        onChange={(e) => setEditingPhone(e.target.value)}
                      />
                      <button type="button" onClick={() => savePhone(c.id)}>Save</button>
                      <button type="button" onClick={cancelEditingPhone}>Cancel</button>
                    </>
                  ) : (
                    <>
                      {c.phone || '—'}
                      <button type="button" onClick={() => startEditingPhone(c)}>Edit</button>
                    </>
                  )}
                </td>
                <td>{aging[c.id] ? `₹${aging[c.id].total_outstanding.toLocaleString()}` : '—'}</td>
                <td>
                  {aging[c.id] ? (
                    <span className={riskBadgeClass(aging[c.id].oldest_days_overdue)}>
                      {riskBadge(aging[c.id].oldest_days_overdue)}
                    </span>
                  ) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {customers.length === 0 && <p className="empty-state">No customers yet.</p>}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/Customers.test.jsx`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Customers.jsx frontend/src/pages/Customers.test.jsx
git commit -m "feat: show and edit customer phone numbers, add manual add-customer form"
```

---

### Task 10: Frontend — Suppliers page: add-supplier form

**Files:**
- Modify: `frontend/src/pages/Suppliers.jsx`
- Modify: `frontend/src/pages/Suppliers.test.jsx`

**Interfaces:**
- Consumes: `api.getRateCards()`, `api.getSuppliers()`, `api.getProducts()` (existing, unchanged), `api.createSupplier(payload)` (Task 4).

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/pages/Suppliers.test.jsx`:

```jsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Suppliers from './Suppliers'
import { api } from '../api'

vi.mock('../api')

describe('Suppliers', () => {
  beforeEach(() => {
    api.getRateCards.mockResolvedValue([
      { supplier_id: 1, product_id: 1, price: 380, unit: 'bag', date: '2026-06-01', discount_tier_text: '5% above 500 bags' },
    ])
    api.getSuppliers.mockResolvedValue([{ id: 1, name: 'Ambuja Distributors' }])
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement' }])
  })

  it('lists rate cards grouped by product', async () => {
    render(<Suppliers />)
    await waitFor(() => expect(screen.getByText(/380/)).toBeInTheDocument())
    expect(screen.getByText(/5% above 500 bags/)).toBeInTheDocument()
    expect(screen.getByText('Ambuja Distributors')).toBeInTheDocument()
    expect(screen.getByText('Ambuja Cement')).toBeInTheDocument()
  })

  it('adds a new supplier', async () => {
    api.createSupplier.mockResolvedValue({ id: 2, name: 'Birla Distributors', contact: '9112233445' })
    render(<Suppliers />)
    await waitFor(() => expect(screen.getByText('Ambuja Distributors')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Birla Distributors' } })
    fireEvent.change(screen.getByLabelText('Contact'), { target: { value: '9112233445' } })
    fireEvent.click(screen.getByRole('button', { name: /add supplier/i }))

    await waitFor(() => expect(api.createSupplier).toHaveBeenCalledWith({ name: 'Birla Distributors', contact: '9112233445' }))
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/pages/Suppliers.test.jsx`
Expected: the new "adds a new supplier" test FAILS (no form yet).

- [ ] **Step 3: Implement the updated Suppliers page**

Replace the full contents of `frontend/src/pages/Suppliers.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Suppliers() {
  const [rateCards, setRateCards] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])
  const [form, setForm] = useState({ name: '', contact: '' })
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getRateCards().then(setRateCards).catch(() => {})
    api.getSuppliers().then(setSuppliers).catch(() => {})
    api.getProducts().then(setProducts).catch(() => {})
  }, [])

  const suppliersById = Object.fromEntries(suppliers.map((s) => [s.id, s]))
  const productsById = Object.fromEntries(products.map((p) => [p.id, p]))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsSaving(true)
    setError(null)
    try {
      const created = await api.createSupplier(form)
      setSuppliers((prev) => [...prev, created])
      setForm({ name: '', contact: '' })
    } catch (err) {
      setError('Could not add this supplier. Please try again.')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <section>
      <h2>Suppliers</h2>
      <div className="card">
        <div className="section-title">Add Supplier</div>
        <form onSubmit={handleSubmit}>
          <label htmlFor="supplier-name">Name</label>
          <input type="text" id="supplier-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <label htmlFor="supplier-contact">Contact</label>
          <input type="text" id="supplier-contact" value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} placeholder="Name - +91XXXXXXXXXX" />
          <button className="btn-primary" type="submit" disabled={!form.name.trim() || isSaving}>
            {isSaving ? 'Adding…' : 'Add supplier'}
          </button>
        </form>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <div className="alert-title">Add failed</div>
          {error}
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr><th>Supplier</th><th>Product</th><th>Price</th><th>Discount</th></tr>
          </thead>
          <tbody>
            {rateCards.map((c, i) => (
              <tr key={i}>
                <td>{suppliersById[c.supplier_id]?.name ?? `Supplier ${c.supplier_id}`}</td>
                <td>{productsById[c.product_id]?.name ?? `Product ${c.product_id}`}</td>
                <td>{c.price ?? 'call for rate'} / {c.unit}</td>
                <td>{c.discount_tier_text || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rateCards.length === 0 && <p className="empty-state">No rate cards yet.</p>}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/pages/Suppliers.test.jsx`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Suppliers.jsx frontend/src/pages/Suppliers.test.jsx
git commit -m "feat: add manual add-supplier form to Suppliers page"
```

---

### Task 11: Frontend — Overview page: Top 5 Outstanding Customers widget

**Files:**
- Modify: `frontend/src/pages/Overview.jsx`
- Modify: `frontend/src/pages/Overview.test.jsx`

**Interfaces:**
- Consumes: `api.getTopOutstandingCustomers(5)` (Task 4 client, Task 2 endpoint), returning `[{customer_id, name, outstanding}]`.

- [ ] **Step 1: Write the failing test**

Replace the full contents of `frontend/src/pages/Overview.test.jsx`:

```jsx
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Overview from './Overview'
import { api } from '../api'

vi.mock('../api')

describe('Overview', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement', current_stock: 12 }])
    api.getOrders.mockResolvedValue([{ id: 1, customer_id: 1, status: 'pending' }])
    api.getTopOutstandingCustomers.mockResolvedValue([])
  })

  it('shows low-stock alert when a product is under threshold', async () => {
    render(<Overview />)
    await waitFor(() => expect(screen.getByText(/Ambuja Cement/)).toBeInTheDocument())
    expect(screen.getByText(/low stock/i)).toBeInTheDocument()
  })

  it('shows the top outstanding customers', async () => {
    api.getTopOutstandingCustomers.mockResolvedValue([
      { customer_id: 1, name: 'Vinod Builders', outstanding: 410000 },
      { customer_id: 2, name: 'Sharma Contractor', outstanding: 50000 },
    ])
    render(<Overview />)
    await waitFor(() => expect(screen.getByText('Vinod Builders')).toBeInTheDocument())
    expect(screen.getByText('Sharma Contractor')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `cd frontend && npx vitest run src/pages/Overview.test.jsx`
Expected: "shows the top outstanding customers" FAILS (no such widget yet).

- [ ] **Step 3: Implement the widget**

Replace the full contents of `frontend/src/pages/Overview.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api'

const LOW_STOCK_THRESHOLD = 50

export default function Overview() {
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [topOutstanding, setTopOutstanding] = useState([])

  useEffect(() => {
    api.getProducts().then(setProducts).catch(() => {})
    api.getOrders().then(setOrders).catch(() => {})
    api.getTopOutstandingCustomers(5).then(setTopOutstanding).catch(() => {})
  }, [])

  const lowStock = products.filter((p) => p.current_stock < LOW_STOCK_THRESHOLD).slice(0, 5)

  return (
    <section>
      <h2>Overview</h2>
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{products.length}</div>
          <div className="stat-label">Products</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{orders.length}</div>
          <div className="stat-label">Orders today</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{lowStock.length}</div>
          <div className="stat-label">Running critically low</div>
        </div>
      </div>
      {lowStock.length > 0 && (
        <div className="alert" role="alert">
          <div className="alert-title">Low stock alert</div>
          <ul>
            {lowStock.map((p) => (
              <li key={p.id}>{p.name} — {p.current_stock} left</li>
            ))}
          </ul>
        </div>
      )}
      {topOutstanding.length > 0 && (
        <div className="card">
          <div className="section-title">Top 5 Outstanding Customers</div>
          <table>
            <thead>
              <tr><th>Customer</th><th>Outstanding</th></tr>
            </thead>
            <tbody>
              {topOutstanding.map((c) => (
                <tr key={c.customer_id}>
                  <td>{c.name}</td>
                  <td>₹{c.outstanding.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/pages/Overview.test.jsx`
Expected: both tests PASS.

- [ ] **Step 5: Run the full test suites one last time**

Run: `cd backend && pytest -v`
Run: `cd frontend && npm test`
Expected: everything PASSes (backend order-creation tests SKIP if no real API key is configured, which is pre-existing behavior unrelated to this work).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/Overview.jsx frontend/src/pages/Overview.test.jsx
git commit -m "feat: show top 5 outstanding customers on the Overview page"
```
