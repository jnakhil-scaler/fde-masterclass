import { render, screen, waitFor } from '@testing-library/react'
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
})
