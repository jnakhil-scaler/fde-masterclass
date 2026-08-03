import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Customers from './Customers'
import { api } from '../api'

vi.mock('../api')

describe('Customers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a high-risk badge for a customer over 60 days overdue', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 410000, oldest_days_overdue: 82 })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders' }]} />)

    await waitFor(() => expect(screen.getByText('Vinod Builders')).toBeInTheDocument())
    expect(screen.getByText(/high risk/i)).toBeInTheDocument()
  })

  it('fetches its own customer list when no customers prop is given', async () => {
    api.getCustomers.mockResolvedValue([{ id: 2, name: 'Sharma Contractor' }])
    api.getCredit.mockResolvedValue({ total_outstanding: 50000, oldest_days_overdue: 10 })

    render(<Customers />)

    await waitFor(() => expect(screen.getByText('Sharma Contractor')).toBeInTheDocument())
    expect(api.getCustomers).toHaveBeenCalled()
  })
})
