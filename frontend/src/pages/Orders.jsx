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
