import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { WorkspaceApp } from '@/components/workspace/WorkspaceApp';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    authSetupStatus: vi.fn(),
    authSession: vi.fn(),
    authSetup: vi.fn(),
    authUnlock: vi.fn(),
    authLogout: vi.fn(),
    listWorkspaces: vi.fn(),
    getWorkspaceReviewSummary: vi.fn(),
    listWorkspaceItems: vi.fn(),
    setWorkspaceItemReviewStatus: vi.fn(),
  },
}));

const apiMock = vi.mocked(api);

describe('WorkspaceApp API-backed states', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders uninitialized setup screen', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: false, auth_mode: 'local', has_active_user: false });
    render(<WorkspaceApp />);
    expect(await screen.findByText('Create Master Password')).toBeInTheDocument();
  });

  it('renders locked screen', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: false, app_state: 'LOCKED' });
    render(<WorkspaceApp />);
    expect(await screen.findByText('Unlock Workspace')).toBeInTheDocument();
  });

  it('renders unlocked shell', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    expect(await screen.findByTestId('unlocked-shell')).toBeInTheDocument();
  });

  it('renders session expired state', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: false, app_state: 'SESSION_EXPIRED' });
    render(<WorkspaceApp />);
    expect(await screen.findByText('Session Expired')).toBeInTheDocument();
  });

  it('renders workspace selector options from API', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
      { id: 'w2', user_id: 'u1', tax_year: 'FY2024', label: 'FY2024 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    expect(await screen.findByTestId('tax-year-selector')).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: 'FY2025' })).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: 'FY2024' })).toBeInTheDocument();
  });

  it('uses selected workspace id in workflow links', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
      { id: 'w2', user_id: 'u1', tax_year: 'FY2024', label: 'FY2024 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    await screen.findByRole('option', { name: 'FY2024' });
    const selector = await screen.findByLabelText('Tax Year Workspace');
    expect((selector as HTMLSelectElement).value).toBe('w1');
    fireEvent.change(selector, { target: { value: 'w2' } });
    await waitFor(() => {
      expect((selector as HTMLSelectElement).value).toBe('w2');
    });
    await waitFor(() => {
      const link = screen.getByRole('link', { name: 'Open Documents' });
      expect(link.getAttribute('href')).toContain('workspace_id=w2');
    });
  });

  it('renders review progress and disables review pack when not ready', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 3, draft: 0, needs_review: 1, confirmed: 1, excluded: 1, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['1 item(s) still need review.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    expect(await screen.findByTestId('review-progress')).toBeInTheDocument();
    expect(screen.getByText(/Review progress:/)).toBeInTheDocument();
    const reviewPackStep = screen.getByText('Step 4: Generate review pack').closest('article');
    expect(reviewPackStep?.textContent).toContain('Blocked');
  });

  it('renders review filters and item status actions', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 1, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['1 item(s) still need review.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([
      {
        id: 'i1',
        session_id: 's1',
        item_type: 'deduction',
        category: 'tools_equipment',
        amount: 20,
        description: 'receipt',
        confidence: 0.9,
        needs_review: true,
        review_status: 'needs_review',
        review_reason: null,
        ato_reference_hint: null,
        reviewed_at: null,
        reviewed_by: null,
        created_at: '',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Items' }));
    expect(await screen.findByTestId('review-filters')).toBeInTheDocument();
    const actionPanel = await screen.findByTestId('item-status-actions');
    expect(actionPanel.textContent).toContain('Confirm');
    expect(actionPanel.textContent).toContain('Needs Review');
    expect(actionPanel.textContent).toContain('Exclude');
    expect(actionPanel.textContent).toContain('Tax Agent Review');
  });
});
