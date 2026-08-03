import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [rawText, setRawText] = useState('')
  const [parsed, setParsed] = useState(null)

  useEffect(() => {
    api.getOrders().then(setOrders)
  }, [])

  const handleParse = async () => {
    const result = await api.parseOrder(rawText)
    setParsed(result)
  }

  return (
    <section>
      <h2>Orders</h2>
      <div>
        <label htmlFor="whatsapp-input">Paste WhatsApp message</label>
        <textarea id="whatsapp-input" value={rawText} onChange={(e) => setRawText(e.target.value)} />
        <button onClick={handleParse}>Parse order</button>
      </div>
      {parsed && (
        <div>
          <p>Delivery: {parsed.delivery_address} — {parsed.delivery_time}</p>
          <ul>
            {parsed.items.map((item, i) => (
              <li key={i}>{item.product_hint}: {item.qty} {item.unit}</li>
            ))}
          </ul>
        </div>
      )}
      <ul>
        {orders.map((o) => (
          <li key={o.id}>Order #{o.id} — {o.status}</li>
        ))}
      </ul>
    </section>
  )
}
