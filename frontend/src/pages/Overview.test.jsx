import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Overview from './Overview'
import { api } from '../api'

vi.mock('../api')

describe('Overview', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement', current_stock: 12 }])
    api.getOrders.mockResolvedValue([{ id: 1, customer_id: 1, status: 'pending' }])
    api.getTopOutstandingCustomers.mockResolvedValue([])
  })

  it('shows low-stock alert when a product is under threshold', async () => {
    render(<Overview />)
    await waitFor(() => expect(screen.getByText(/Ambuja Cement/)).toBeInTheDocument())
    expect(screen.getByText(/low stock/i)).toBeInTheDocument()
  })

  it('shows the top outstanding customers', async () => {
    api.getTopOutstandingCustomers.mockResolvedValue([
      { customer_id: 1, name: 'Vinod Builders', outstanding: 410000 },
      { customer_id: 2, name: 'Sharma Contractor', outstanding: 50000 },
    ])
    render(<Overview />)
    await waitFor(() => expect(screen.getByText('Vinod Builders')).toBeInTheDocument())
    expect(screen.getByText('Sharma Contractor')).toBeInTheDocument()
  })
})
