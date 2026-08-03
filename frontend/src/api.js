const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) throw new Error(`Request to ${path} failed: ${response.status}`)
  return response.json()
}

export const api = {
  getProducts: () => request('/products'),
  getOrders: () => request('/orders'),
  getSuppliers: () => request('/suppliers'),
  getCustomers: () => request('/customers'),
  getRateCards: () => request('/suppliers/rate-cards'),
  getCredit: (customerId) => request(`/credit/${customerId}`),
  parseOrder: (rawText) => request('/agents/parse-order', { method: 'POST', body: JSON.stringify({ raw_text: rawText }) }),
}
