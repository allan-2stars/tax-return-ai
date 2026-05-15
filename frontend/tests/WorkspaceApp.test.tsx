import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WorkspaceApp } from '@/components/workspace/WorkspaceApp';

vi.mock('@/lib/api', () => ({
  api: {
    listSessions: vi.fn(async () => []),
    getSessionStats: vi.fn(async () => ({
      session_id: 's1',
      document_count: 0,
      classified_document_count: 0,
      income_item_count: 0,
      deduction_item_count: 0,
      needs_review_item_count: 0,
      total_item_count: 0,
    })),
  },
}));

const KEY = 'taxai_mock_auth_v1';

describe('WorkspaceApp shell states', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('renders locked state', () => {
    window.localStorage.setItem(KEY, JSON.stringify({ initialized: true }));
    render(<WorkspaceApp />);
    expect(screen.getByText('Unlock Workspace')).toBeInTheDocument();
  });

  it('renders unlocked app shell', async () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({ initialized: true, passwordHint: 'ab', recoveryKey: 'AAAAAA-BBBBBB-CCCCCC-DDDDDD', sessionExpiresAt: Date.now() + 60_000 })
    );
    render(<WorkspaceApp />);
    expect(await screen.findByTestId('unlocked-shell')).toBeInTheDocument();
    expect(screen.getByText('Tax Return AI')).toBeInTheDocument();
  });

  it('renders sidebar navigation', async () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({ initialized: true, passwordHint: 'ab', recoveryKey: 'AAAAAA-BBBBBB-CCCCCC-DDDDDD', sessionExpiresAt: Date.now() + 60_000 })
    );
    render(<WorkspaceApp />);
    expect(await screen.findByRole('navigation', { name: 'Primary' })).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Review Items')).toBeInTheDocument();
    expect(screen.getByText('Review Pack')).toBeInTheDocument();
  });

  it('renders tax year selector', async () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({ initialized: true, passwordHint: 'ab', recoveryKey: 'AAAAAA-BBBBBB-CCCCCC-DDDDDD', sessionExpiresAt: Date.now() + 60_000 })
    );
    render(<WorkspaceApp />);
    expect(await screen.findByTestId('tax-year-selector')).toBeInTheDocument();
    expect(screen.getByText('FY2025')).toBeInTheDocument();
    expect(screen.getByText('FY2024')).toBeInTheDocument();
  });

  it('renders dashboard guided steps', async () => {
    window.localStorage.setItem(
      KEY,
      JSON.stringify({ initialized: true, passwordHint: 'ab', recoveryKey: 'AAAAAA-BBBBBB-CCCCCC-DDDDDD', sessionExpiresAt: Date.now() + 60_000 })
    );
    render(<WorkspaceApp />);
    expect(await screen.findByTestId('guided-steps')).toBeInTheDocument();
    expect(screen.getByText('Step 1: Add documents')).toBeInTheDocument();
    expect(screen.getByText('Step 2: Review extracted items')).toBeInTheDocument();
    expect(screen.getByText('Step 3: Resolve issues')).toBeInTheDocument();
    expect(screen.getByText('Step 4: Generate review pack')).toBeInTheDocument();
  });

  it('renders session expired screen', () => {
    window.localStorage.setItem(KEY, JSON.stringify({ initialized: true, sessionExpiresAt: Date.now() - 60_000 }));
    render(<WorkspaceApp />);
    expect(screen.getByText('Session Expired')).toBeInTheDocument();
  });
});
