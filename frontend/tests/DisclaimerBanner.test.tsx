import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DisclaimerBanner } from '@/components/DisclaimerBanner';

describe('DisclaimerBanner', () => {
  it('renders the tax disclaimer text', () => {
    render(<DisclaimerBanner />);
    expect(screen.getByText(/tax advice/i)).toBeInTheDocument();
    expect(screen.getByText(/does not provide/i)).toBeInTheDocument();
  });

  it('has correct ARIA role', () => {
    render(<DisclaimerBanner />);
    expect(screen.getByRole('note')).toBeInTheDocument();
  });
});
