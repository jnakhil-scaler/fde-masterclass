import { useState } from 'react'
import { api } from '../api'

function riskBadgeClass(riskLevel) {
  if (riskLevel === 'high') return 'badge badge-high'
  if (riskLevel === 'medium') return 'badge badge-medium'
  if (riskLevel === 'low') return 'badge badge-low'
  return 'badge'
}

export default function Parser() {
  const [rawText, setRawText] = useState('')
  const [senderPhone, setSenderPhone] = useState('')
  const [parsed, setParsed] = useState(null)
  const [parseError, setParseError] = useState(null)
  const [isParsing, setIsParsing] = useState(false)

  const handleParse = async () => {
    setIsParsing(true)
    setParseError(null)
    try {
      const result = await api.parseOrder(rawText, senderPhone)
      setParsed(result)
    } catch (err) {
      setParseError('Could not parse this message. Please try again.')
    } finally {
      setIsParsing(false)
    }
  }

  return (
    <section>
      <h2>WhatsApp Parser</h2>
      <div className="card">
        <div className="section-title">AI Order Parser</div>
        <label htmlFor="whatsapp-input">Paste WhatsApp message</label>
        <textarea id="whatsapp-input" value={rawText} onChange={(e) => setRawText(e.target.value)} placeholder="e.g. bhai 10mm sariya 2 ton pipe 1 inch 50 piece kal subah Sharma site pe bhijwa dena" />
        <label htmlFor="sender-phone-input">Sender phone (optional — links to a real customer and creates the order)</label>
        <input type="text" id="sender-phone-input" value={senderPhone} onChange={(e) => setSenderPhone(e.target.value)} placeholder="+91XXXXXXXXXX" />
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

      {parsed?.created_order && (
        <div className="card">
          <div className="section-title">Order Created</div>
          <p>Order #{parsed.created_order.id} — ₹{parsed.created_order.total_amount.toLocaleString()}</p>
          <span className={riskBadgeClass(parsed.created_order.credit_risk.risk_level)}>
            {parsed.created_order.credit_risk.risk_level} risk
          </span>
          <p className="muted">{parsed.created_order.credit_risk.recommendation}</p>
        </div>
      )}
    </section>
  )
}
