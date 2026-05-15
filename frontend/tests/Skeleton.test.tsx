import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SkeletonCard, SkeletonTable, SkeletonText } from '@/components/Skeleton';

describe('SkeletonCard', () => {
  it('renders with animate-pulse class', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders placeholder divs inside the card', () => {
    const { container } = render(<SkeletonCard />);
    const bars = container.querySelectorAll('.animate-pulse > div');
    expect(bars.length).toBeGreaterThanOrEqual(3);
  });
});

describe('SkeletonTable', () => {
  it('renders with animate-pulse class', () => {
    const { container } = render(<SkeletonTable />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders multiple placeholder rows', () => {
    const { container } = render(<SkeletonTable />);
    const rows = container.querySelectorAll('.animate-pulse > div');
    expect(rows.length).toBeGreaterThanOrEqual(4);
  });
});

describe('SkeletonText', () => {
  it('renders specified number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />);
    const lines = container.querySelectorAll('.animate-pulse > div');
    expect(lines.length).toBe(5);
  });

  it('defaults to 3 lines', () => {
    const { container } = render(<SkeletonText />);
    const lines = container.querySelectorAll('.animate-pulse > div');
    expect(lines.length).toBe(3);
  });

  it('renders a single line when lines is 1', () => {
    const { container } = render(<SkeletonText lines={1} />);
    const lines = container.querySelectorAll('.animate-pulse > div');
    expect(lines.length).toBe(1);
  });

  it('each line has bg-gray-100 and rounded classes', () => {
    const { container } = render(<SkeletonText lines={2} />);
    const lines = container.querySelectorAll('.animate-pulse > div');
    lines.forEach((line) => {
      expect(line.className).toContain('bg-gray-100');
      expect(line.className).toContain('rounded');
    });
  });
});
