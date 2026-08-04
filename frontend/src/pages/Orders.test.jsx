import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Orders from './Orders'
import { api } from '../api'

vi.mock('../api')

describe('Orders', () => {
  beforeEach(() => {
    api.getOrders.mockResolvedValue([])
    api.parseOrder.mockResolvedValue({
      items: [{ product_hint: 'TMT Sariya 10mm', qty: 2, unit: 'ton' }],
      delivery_address: 'Sharma site',
      delivery_time: 'tomorrow morning',
    })
  })

  it('parses a pasted WhatsApp message and shows the structured result', async () => {
    render(<Orders />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), {
      target: { value: 'bhai 10mm sariya 2 ton kal subah Sharma site pe' },
    })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByText(/Sharma site/)).toBeInTheDocument())
    expect(screen.getByText(/TMT Sariya 10mm/)).toBeInTheDocument()
  })

  it('shows an error message if parsing fails', async () => {
    api.parseOrder.mockRejectedValue(new Error('API error'))
    render(<Orders />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), { target: { value: 'test message' } })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('shows the created order and risk badge when parseOrder returns one', async () => {
    api.parseOrder.mockResolvedValue({
      items: [{ product_hint: 'TMT Sariya 10mm', qty: 2, unit: 'ton' }],
      delivery_address: 'Sharma site',
      delivery_time: 'tomorrow morning',
      created_order: {
        id: 42,
        customer_id: 7,
        status: 'pending',
        source: 'whatsapp',
        total_amount: 350000,
        credit_risk: { risk_level: 'high', total_exposure: 760000, recommendation: 'Require advance payment.' },
      },
    })
    render(<Orders />)
    fireEvent.change(screen.getByLabelText(/paste whatsapp message/i), { target: { value: 'test' } })
    fireEvent.click(screen.getByRole('button', { name: /parse/i }))

    await waitFor(() => expect(screen.getByText(/Order #42/)).toBeInTheDocument())
    expect(screen.getByText(/high risk/i)).toBeInTheDocument()
  })
})
