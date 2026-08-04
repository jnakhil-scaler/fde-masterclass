import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from './App'
import { api } from './api'

vi.mock('./api')

describe('App', () => {
  beforeEach(() => {
    api.getProducts.mockResolvedValue([])
    api.getOrders.mockResolvedValue([])
    api.getTopOutstandingCustomers.mockResolvedValue([])
    api.getCustomers.mockResolvedValue([])
  })

  it('renders all tabs and defaults to Overview', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Orders' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Products' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Customers' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Suppliers' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Parser' })).toBeInTheDocument()
  })

  it('switches tabs on click', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('tab', { name: 'Orders' }))
    expect(screen.getByRole('tab', { name: 'Orders' })).toHaveAttribute('aria-selected', 'true')
  })
})
