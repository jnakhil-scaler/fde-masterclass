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

  return (
    <section>
      <h2>Customers</h2>
      <div className="card">
        <table>
          <thead>
            <tr><th>Customer</th><th>Outstanding</th><th>Risk</th></tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
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
