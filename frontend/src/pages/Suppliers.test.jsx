import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Suppliers from './Suppliers'
import { api } from '../api'

vi.mock('../api')

describe('Suppliers', () => {
  beforeEach(() => {
    api.getRateCards.mockResolvedValue([
      { supplier_id: 1, product_id: 1, price: 380, unit: 'bag', date: '2026-06-01', discount_tier_text: '5% above 500 bags' },
    ])
    api.getSuppliers.mockResolvedValue([{ id: 1, name: 'Ambuja Distributors' }])
    api.getProducts.mockResolvedValue([{ id: 1, name: 'Ambuja Cement' }])
  })

  it('lists rate cards grouped by product', async () => {
    render(<Suppliers />)
    await waitFor(() => expect(screen.getByText(/380/)).toBeInTheDocument())
    expect(screen.getByText(/5% above 500 bags/)).toBeInTheDocument()
    expect(screen.getByText('Ambuja Distributors')).toBeInTheDocument()
    expect(screen.getByText('Ambuja Cement')).toBeInTheDocument()
  })

  it('adds a new supplier', async () => {
    api.createSupplier.mockResolvedValue({ id: 2, name: 'Birla Distributors', contact: '9112233445' })
    render(<Suppliers />)
    await waitFor(() => expect(screen.getByText('Ambuja Distributors')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Birla Distributors' } })
    fireEvent.change(screen.getByLabelText('Contact'), { target: { value: '9112233445' } })
    fireEvent.click(screen.getByRole('button', { name: /add supplier/i }))

    await waitFor(() => expect(api.createSupplier).toHaveBeenCalledWith({ name: 'Birla Distributors', contact: '9112233445' }))
  })
})
