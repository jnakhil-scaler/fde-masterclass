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
