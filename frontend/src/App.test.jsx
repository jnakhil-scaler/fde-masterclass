import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders all four tabs and defaults to Overview', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Orders' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Customers' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Suppliers' })).toBeInTheDocument()
  })

  it('switches tabs on click', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('tab', { name: 'Orders' }))
    expect(screen.getByRole('tab', { name: 'Orders' })).toHaveAttribute('aria-selected', 'true')
  })
})
