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
      <p>{products.length} products, {orders.length} orders today</p>
      {lowStock.length > 0 && (
        <div role="alert">
          Low stock alert:
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
