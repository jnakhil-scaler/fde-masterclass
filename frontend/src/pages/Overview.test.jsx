import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Overview from './Overview'
import { api } from '../api'

vi.mock('../api')

describe('Overview', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement', current_stock: 12 }])
    api.getOrders.mockResolvedValue([{ id: 1, customer_id: 1, status: 'pending' }])
  })

  it('shows low-stock alert when a product is under threshold', async () => {
    render(<Overview />)
    await waitFor(() => expect(screen.getByText(/Ambuja Cement/)).toBeInTheDocument())
    expect(screen.getByText(/low stock/i)).toBeInTheDocument()
  })
})
