import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Suppliers() {
  const [rateCards, setRateCards] = useState([])

  useEffect(() => {
    api.getRateCards().then(setRateCards).catch(() => {})
  }, [])

  return (
    <section>
      <h2>Suppliers</h2>
      <table>
        <thead>
          <tr><th>Supplier</th><th>Product</th><th>Price</th><th>Discount</th></tr>
        </thead>
        <tbody>
          {rateCards.map((c, i) => (
            <tr key={i}>
              <td>{c.supplier_id}</td>
              <td>{c.product_id}</td>
              <td>{c.price ?? 'call for rate'} / {c.unit}</td>
              <td>{c.discount_tier_text || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
