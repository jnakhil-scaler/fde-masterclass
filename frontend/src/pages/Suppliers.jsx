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
