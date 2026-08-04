import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Products from './Products'
import { api } from '../api'

vi.mock('../api')

describe('Products', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([
      { id: 1, name: 'Ambuja Cement', brand: 'Ambuja', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 340 },
      { id: 2, name: 'TMT Sariya 10mm', brand: 'Generic', category: 'Steel', unit: 'ton', hsn_code: '7213', current_stock: 8 },
    ])
  })

  it('lists all products', async () => {
    render(<Products />)
    await waitFor(() => expect(screen.getByText('Ambuja Cement')).toBeInTheDocument())
    expect(screen.getByText('TMT Sariya 10mm')).toBeInTheDocument()
  })

  it('filters products by search text', async () => {
    render(<Products />)
    await waitFor(() => expect(screen.getByText('Ambuja Cement')).toBeInTheDocument())
    fireEvent.change(screen.getByLabelText(/filter/i), { target: { value: 'sariya' } })
    expect(screen.queryByText('Ambuja Cement')).not.toBeInTheDocument()
    expect(screen.getByText('TMT Sariya 10mm')).toBeInTheDocument()
  })

  it('adds a new product', async () => {
    api.createProduct.mockResolvedValue({ id: 3, name: 'Birla Cement', brand: 'Birla', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 100 })
    render(<Products />)
    await waitFor(() => expect(screen.getByText('Ambuja Cement')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Birla Cement' } })
    fireEvent.change(screen.getByLabelText('Brand'), { target: { value: 'Birla' } })
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'Cement' } })
    fireEvent.change(screen.getByLabelText('Unit'), { target: { value: 'bag' } })
    fireEvent.change(screen.getByLabelText('HSN Code'), { target: { value: '2523' } })
    fireEvent.change(screen.getByLabelText('Current Stock'), { target: { value: '100' } })
    fireEvent.click(screen.getByRole('button', { name: /add product/i }))

    await waitFor(() => expect(screen.getByText('Birla Cement')).toBeInTheDocument())
    expect(api.createProduct).toHaveBeenCalledWith({
      name: 'Birla Cement', brand: 'Birla', category: 'Cement', unit: 'bag', hsn_code: '2523', current_stock: 100,
    })
  })
})
