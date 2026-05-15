import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SessionCard } from '@/components/SessionCard';

const mockSession = {
  id: 'session-123',
  title: 'FY2025-2026 — Individual',
  financial_year: '2025-2026',
  status: 'draft',
  notes: 'My test session notes',
  created_at: '2026-05-14T01:22:07.709811',
  updated_at: '2026-05-14T01:22:07.709816',
};

describe('SessionCard', () => {
  it('renders session title', () => {
    const onSelect = vi.fn();
    render(<SessionCard session={mockSession} onSelect={onSelect} />);
    expect(screen.getByText('FY2025-2026 — Individual')).toBeInTheDocument();
  });

  it('renders notes', () => {
    const onSelect = vi.fn();
    render(<SessionCard session={mockSession} onSelect={onSelect} />);
    expect(screen.getByText('My test session notes')).toBeInTheDocument();
  });

  it('renders financial year', () => {
    const onSelect = vi.fn();
    render(<SessionCard session={mockSession} onSelect={onSelect} />);
    expect(screen.getByText(/FY 2025-2026/)).toBeInTheDocument();
  });

  it('renders status badge', () => {
    const onSelect = vi.fn();
    render(<SessionCard session={mockSession} onSelect={onSelect} />);
    expect(screen.getByText('draft')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = vi.fn();
    render(<SessionCard session={mockSession} onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onSelect).toHaveBeenCalledWith('session-123');
  });
});
