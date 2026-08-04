import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Suppliers() {
  const [rateCards, setRateCards] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [products, setProducts] = useState([])

  useEffect(() => {
    api.getRateCards().then(setRateCards).catch(() => {})
    api.getSuppliers().then(setSuppliers).catch(() => {})
    api.getProducts().then(setProducts).catch(() => {})
  }, [])

  const suppliersById = Object.fromEntries(suppliers.map((s) => [s.id, s]))
  const productsById = Object.fromEntries(products.map((p) => [p.id, p]))

  return (
    <section>
      <h2>Suppliers</h2>
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
