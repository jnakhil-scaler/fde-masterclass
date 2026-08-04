import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Orders from './Orders'
import { api } from '../api'

vi.mock('../api')

describe('Orders', () => {
  beforeEach(() => {
    api.getOrders.mockResolvedValue([
      {
        id: 1, order_date: '2026-08-01T10:00:00', customer_id: 3, customer_name: 'Sharma Contractor',
        source: 'manual', status: 'pending', total_amount: 3800,
        items: [{ product_id: 1, product_name: 'Ambuja Cement', qty: 10, unit_price: 380 }],
      },
    ])
    api.getCustomers.mockResolvedValue([{ id: 3, name: 'Sharma Contractor', phone: '9876543210', area: 'Indore' }])
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement', brand: 'Ambuja', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 340 }])
  })

  it('lists existing orders with customer and item details', async () => {
    render(<Orders />)
    await waitFor(() => expect(screen.getByRole('cell', { name: 'Sharma Contractor' })).toBeInTheDocument())
    expect(screen.getByText(/Ambuja Cement x10/)).toBeInTheDocument()
  })

  it('creates a new order and shows the risk badge', async () => {
    api.createOrder.mockResolvedValue({
      id: 42, customer_id: 3, status: 'pending', source: 'manual', total_amount: 3800,
      credit_risk: { risk_level: 'low', total_exposure: 3800, recommendation: 'Proceed as normal.' },
    })
    render(<Orders />)
    await waitFor(() => expect(screen.getByLabelText('Customer')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Customer'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Product'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Unit price'), { target: { value: '380' } })
    fireEvent.click(screen.getByRole('button', { name: /create order/i }))

    await waitFor(() => expect(screen.getByText(/Order #42/)).toBeInTheDocument())
    expect(screen.getByText(/low risk/i)).toBeInTheDocument()
    expect(api.createOrder).toHaveBeenCalledWith({
      customer_id: 3, source: 'manual', delivery_address: undefined, delivery_time: undefined,
      items: [{ product_id: 1, qty: 10, unit_price: 380 }],
    })
  })

  it('shows an error message if order creation fails', async () => {
    api.createOrder.mockRejectedValue(new Error('API error'))
    render(<Orders />)
    await waitFor(() => expect(screen.getByLabelText('Customer')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Customer'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Product'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Quantity'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Unit price'), { target: { value: '380' } })
    fireEvent.click(screen.getByRole('button', { name: /create order/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })
})
