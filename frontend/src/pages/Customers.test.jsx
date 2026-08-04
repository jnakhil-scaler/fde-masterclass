import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
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

  it('displays the customer phone number', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 0, oldest_days_overdue: 0 })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders', phone: '9876543210' }]} />)

    await waitFor(() => expect(screen.getByText('9876543210')).toBeInTheDocument())
  })

  it('edits a missing phone number inline', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 0, oldest_days_overdue: 0 })
    api.updateCustomer.mockResolvedValue({ id: 1, name: 'Vinod Builders', phone: '9998887776', area: null })
    render(<Customers customers={[{ id: 1, name: 'Vinod Builders', phone: null }]} />)

    const row = await screen.findByRole('row', { name: /Vinod Builders/i })
    fireEvent.click(within(row).getByRole('button', { name: /edit/i }))
    fireEvent.change(within(row).getByRole('textbox', { name: /phone/i }), { target: { value: '9998887776' } })
    fireEvent.click(within(row).getByRole('button', { name: /save/i }))

    await waitFor(() => expect(api.updateCustomer).toHaveBeenCalledWith(1, { phone: '9998887776' }))
    expect(await screen.findByText('9998887776')).toBeInTheDocument()
  })

  it('adds a new customer', async () => {
    api.getCredit.mockResolvedValue({ total_outstanding: 0, oldest_days_overdue: 0 })
    api.createCustomer.mockResolvedValue({ id: 3, name: 'Meena Traders', phone: '9001122334', area: 'Rau' })
    render(<Customers customers={[]} />)

    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Meena Traders' } })
    fireEvent.change(screen.getByLabelText('Phone'), { target: { value: '9001122334' } })
    fireEvent.change(screen.getByLabelText('Area'), { target: { value: 'Rau' } })
    fireEvent.click(screen.getByRole('button', { name: /add customer/i }))

    await waitFor(() => expect(screen.getByText('Meena Traders')).toBeInTheDocument())
    expect(api.createCustomer).toHaveBeenCalledWith({ name: 'Meena Traders', phone: '9001122334', area: 'Rau' })
  })
})
