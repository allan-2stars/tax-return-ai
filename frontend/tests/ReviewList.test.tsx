import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReviewList } from '@/components/ReviewList';

const mockItems = [
  {
    id: 'item-1',
    item_type: 'income',
    category: 'salary_wages',
    amount: 85000,
    description: 'Annual salary from ABC Corp',
    confidence: 0.95,
    needs_review: false,
    review_reason: null,
    ato_reference_hint: 'Salary/Wages',
    session_id: 'session-123',
    reviewed_at: null,
    reviewed_by: null,
    created_at: '2026-05-14T01:22:07.709811',
  },
  {
    id: 'item-2',
    item_type: 'deduction',
    category: 'tools_equipment',
    amount: 149.50,
    description: 'USB hub and keyboard',
    confidence: 0.68,
    needs_review: true,
    review_reason: 'Low confidence — requires human review.',
    ato_reference_hint: 'D5',
    session_id: 'session-123',
    reviewed_at: null,
    reviewed_by: null,
    created_at: '2026-05-14T01:22:07.709811',
  },
];

describe('ReviewList', () => {
  it('shows empty message when no items', () => {
    render(<ReviewList items={[]} />);
    expect(screen.getByText(/No items to review/i)).toBeInTheDocument();
  });

  it('renders all items', () => {
    render(<ReviewList items={mockItems} />);
    expect(screen.getByText(/Annual salary from ABC Corp/)).toBeInTheDocument();
    expect(screen.getByText(/USB hub and keyboard/)).toBeInTheDocument();
  });

  it('shows amounts', () => {
    render(<ReviewList items={mockItems} />);
    expect(screen.getByText('85000.00')).toBeInTheDocument();
    expect(screen.getByText('149.50')).toBeInTheDocument();
  });

  it('shows ATO reference hints', () => {
    render(<ReviewList items={mockItems} />);
    expect(screen.getByText('Salary/Wages')).toBeInTheDocument();
    expect(screen.getByText('D5')).toBeInTheDocument();
  });

  it('shows review reason for flagged items', () => {
    render(<ReviewList items={mockItems} />);
    expect(screen.getByText(/Low confidence/i)).toBeInTheDocument();
  });

  it('shows approve button for flagged items', () => {
    const onToggle = vi.fn();
    render(<ReviewList items={mockItems} onToggleReview={onToggle} />);
    const approveBtn = screen.getByText('Approve');
    expect(approveBtn).toBeInTheDocument();
    fireEvent.click(approveBtn);
    expect(onToggle).toHaveBeenCalledWith('item-2', false);
  });

  it('shows flag button for approved items', () => {
    const onToggle = vi.fn();
    render(<ReviewList items={mockItems} onToggleReview={onToggle} />);
    const flagBtn = screen.getByText('Flag');
    expect(flagBtn).toBeInTheDocument();
  });

  it('shows delete button when handler provided', () => {
    const onDelete = vi.fn();
    render(<ReviewList items={mockItems} onDelete={onDelete} />);
    const deleteBtns = screen.getAllByText('Delete');
    expect(deleteBtns).toHaveLength(2);
  });
});
