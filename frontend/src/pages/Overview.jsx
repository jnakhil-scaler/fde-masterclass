import { useEffect, useState } from 'react'
import { api } from '../api'

const LOW_STOCK_THRESHOLD = 50

export default function Overview() {
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])

  useEffect(() => {
    api.getProducts().then(setProducts).catch(() => {})
    api.getOrders().then(setOrders).catch(() => {})
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
    </section>
  )
}
