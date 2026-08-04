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
  getTopOutstandingCustomers: (limit = 5) => request(`/credit/top-outstanding?limit=${limit}`),
  parseOrder: (rawText, senderPhone) => request('/agents/parse-order', {
    method: 'POST',
    body: JSON.stringify({ raw_text: rawText, sender_phone: senderPhone || undefined }),
  }),
  createCustomer: (payload) => request('/customers', { method: 'POST', body: JSON.stringify(payload) }),
  updateCustomer: (id, patch) => request(`/customers/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  createOrder: (payload) => request('/orders', { method: 'POST', body: JSON.stringify(payload) }),
  createProduct: (payload) => request('/products', { method: 'POST', body: JSON.stringify(payload) }),
  createSupplier: (payload) => request('/suppliers', { method: 'POST', body: JSON.stringify(payload) }),
}
