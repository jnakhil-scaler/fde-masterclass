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
