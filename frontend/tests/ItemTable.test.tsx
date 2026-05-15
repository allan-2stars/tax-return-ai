import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ItemTable } from '@/components/ItemTable';
import type { TaxItem } from '@/lib/api';

const mockItems: TaxItem[] = [
  {
    id: 'item-1',
    session_id: 'session-1',
    item_type: 'income',
    category: 'salary_wages',
    amount: 85000,
    description: 'Annual salary',
    confidence: 0.95,
    needs_review: false,
    review_reason: null,
    ato_reference_hint: null,
    reviewed_at: null,
    reviewed_by: null,
    created_at: '2026-05-14T01:22:07.709811',
  },
  {
    id: 'item-2',
    session_id: 'session-1',
    item_type: 'deduction',
    category: 'tools_equipment',
    amount: 350,
    description: 'Office supplies',
    confidence: 0.65,
    needs_review: true,
    review_reason: 'Low confidence',
    ato_reference_hint: 'D5',
    reviewed_at: null,
    reviewed_by: null,
    created_at: '2026-05-14T01:22:07.709811',
  },
];

// Helper to get formatters like toFixed working
const formatAmount = (val: number | null): string => {
  if (val == null) return '\u2014';
  return `$${val.toFixed(2)}`;
};

describe('ItemTable', () => {
  it('renders income section with items', () => {
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    // The category is rendered with replace(/_/g, " ")
    expect(screen.getByText('salary wages')).toBeInTheDocument();
    expect(screen.getByText(formatAmount(85000))).toBeInTheDocument();
  });

  it('shows needs_review section for flagged items', () => {
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    expect(screen.getByText('Needs Review (1)')).toBeInTheDocument();
  });

  it('renders Approved status for reviewed items', () => {
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    expect(screen.getByText('Approved')).toBeInTheDocument();
  });

  it('renders Review status for flagged items', () => {
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    expect(screen.getByText('Review')).toBeInTheDocument();
  });

  it('renders Approve button for needs_review items', () => {
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    // item-2 has needs_review=true, so its button shows "Approve"
    expect(screen.getByText('Approve')).toBeInTheDocument();
  });

  it('renders Flag button for non-review items', () => {
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    // item-1 has needs_review=false, so its button shows "Flag"
    expect(screen.getByText('Flag')).toBeInTheDocument();
  });

  it('renders empty state when no items', () => {
    render(
      <ItemTable
        items={[]}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    expect(screen.getByText(/No items yet/)).toBeInTheDocument();
  });

  it('does not render category sections when no matching items', () => {
    const onlyDeduction: TaxItem[] = [mockItems[1]];
    render(
      <ItemTable
        items={onlyDeduction}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    // Deductions section should render, but Income should not
    expect(screen.queryByText('Income (1)')).not.toBeInTheDocument();
    expect(screen.getByText('Deductions (1)')).toBeInTheDocument();
  });

  it('calls onToggleReview with correct params when Approve is clicked', () => {
    const onToggleReview = vi.fn();
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={onToggleReview}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    // item-2 has needs_review=true, clicking "Approve" toggles it to false
    fireEvent.click(screen.getByText('Approve'));
    expect(onToggleReview).toHaveBeenCalledWith('item-2', false);
  });

  it('calls onToggleReview with correct params when Flag is clicked', () => {
    const onToggleReview = vi.fn();
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={onToggleReview}
        onDelete={vi.fn()}
        onUpdateItem={vi.fn()}
      />
    );
    // item-1 has needs_review=false, clicking "Flag" toggles it to true
    fireEvent.click(screen.getByText('Flag'));
    expect(onToggleReview).toHaveBeenCalledWith('item-1', true);
  });

  it('calls onDelete when delete is clicked', () => {
    const onDelete = vi.fn();
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={onDelete}
        onUpdateItem={vi.fn()}
      />
    );
    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);
    expect(onDelete).toHaveBeenCalledWith('item-2');
  });

  it('allows inline amount editing via click and Enter', async () => {
    const onUpdateItem = vi.fn().mockResolvedValue(undefined);
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={onUpdateItem}
      />
    );
    // Click on the amount to start editing
    fireEvent.click(screen.getByText(formatAmount(85000)));

    // Should show an input with the amount value
    const input = screen.getByDisplayValue('85000');
    expect(input).toBeInTheDocument();

    // Change and save
    fireEvent.change(input, { target: { value: '90000' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
    expect(onUpdateItem).toHaveBeenCalledWith('item-1', { amount: 90000 });
  });

  it('allows cancelling inline editing with Escape', () => {
    const onUpdateItem = vi.fn().mockResolvedValue(undefined);
    render(
      <ItemTable
        items={mockItems}
        onToggleReview={vi.fn()}
        onDelete={vi.fn()}
        onUpdateItem={onUpdateItem}
      />
    );
    // Click on the amount to start editing
    fireEvent.click(screen.getByText(formatAmount(85000)));

    // Input should appear
    const input = screen.getByDisplayValue('85000');
    expect(input).toBeInTheDocument();

    // Press Escape to cancel
    fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });

    // Should revert to showing the amount text
    expect(screen.getByText(formatAmount(85000))).toBeInTheDocument();
    expect(onUpdateItem).not.toHaveBeenCalled();
  });
});
