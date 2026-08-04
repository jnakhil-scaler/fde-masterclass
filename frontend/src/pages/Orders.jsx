import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [rawText, setRawText] = useState('')
  const [parsed, setParsed] = useState(null)
  const [parseError, setParseError] = useState(null)
  const [isParsing, setIsParsing] = useState(false)

  useEffect(() => {
    api.getOrders().then(setOrders).catch(() => {})
  }, [])

  const handleParse = async () => {
    setIsParsing(true)
    setParseError(null)
    try {
      const result = await api.parseOrder(rawText)
      setParsed(result)
    } catch (err) {
      setParseError('Could not parse this message. Please try again.')
    } finally {
      setIsParsing(false)
    }
  }

  return (
    <section>
      <h2>Orders</h2>
      <div className="card">
        <div className="section-title">AI Order Parser</div>
        <label htmlFor="whatsapp-input">Paste WhatsApp message</label>
        <textarea id="whatsapp-input" value={rawText} onChange={(e) => setRawText(e.target.value)} placeholder="e.g. bhai 10mm sariya 2 ton pipe 1 inch 50 piece kal subah Sharma site pe bhijwa dena" />
        <div>
          <button className="btn-primary" onClick={handleParse} disabled={!rawText.trim() || isParsing}>
            {isParsing ? 'Parsing…' : 'Parse order'}
          </button>
        </div>
      </div>

      {parseError && (
        <div className="alert alert-error" role="alert">
          <div className="alert-title">Parse failed</div>
          {parseError}
        </div>
      )}

      {parsed && (
        <div className="card">
          <div className="section-title">Parsed Result</div>
          <p><strong>Delivery:</strong> {parsed.delivery_address} — {parsed.delivery_time}</p>
          <ul>
            {parsed.items.map((item, i) => (
              <li key={i}>{item.product_hint}: {item.qty} {item.unit}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <div className="section-title">Recent Orders</div>
        {orders.length === 0 ? (
          <p className="empty-state">No orders yet.</p>
        ) : (
          <ul>
            {orders.map((o) => (
              <li key={o.id}>Order #{o.id} — {o.status}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
