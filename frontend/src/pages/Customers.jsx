import { useEffect, useState } from 'react'
import { api } from '../api'

function riskBadge(agingDays) {
  if (agingDays > 60) return 'High risk'
  if (agingDays > 30) return 'Medium risk'
  return 'Low risk'
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
      <table>
        <tbody>
          {customers.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{aging[c.id] ? `₹${aging[c.id].total_outstanding.toLocaleString()}` : '—'}</td>
              <td>{aging[c.id] ? riskBadge(aging[c.id].oldest_days_overdue) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
