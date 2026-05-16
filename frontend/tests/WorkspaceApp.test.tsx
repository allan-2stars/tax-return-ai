import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { WorkspaceApp } from '@/components/workspace/WorkspaceApp';
import { api, ApiError } from '@/lib/api';

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    api: {
      authSetupStatus: vi.fn(),
      authSession: vi.fn(),
      authSetup: vi.fn(),
      authUnlock: vi.fn(),
      authRecoverReset: vi.fn(),
      authLock: vi.fn(),
      authLogout: vi.fn(),
      authLockKeepalive: vi.fn(),
      authLogoutKeepalive: vi.fn(),
      listWorkspaces: vi.fn(),
      listWorkspaceDocuments: vi.fn(),
      uploadWorkspaceDocument: vi.fn(),
      listJobs: vi.fn(),
      getWorkspaceReviewSummary: vi.fn(),
      listWorkspaceItems: vi.fn(),
      setWorkspaceItemReviewStatus: vi.fn(),
      listWorkspaceManualReviewDocuments: vi.fn(),
      createWorkspaceManualItem: vi.fn(),
      applyWorkspaceManualReviewAction: vi.fn(),
      listWorkspaceReviewPacks: vi.fn(),
      generateWorkspaceReviewPack: vi.fn(),
      workspaceReviewPackDownloadUrl: vi.fn(),
      downloadWorkspaceReviewPack: vi.fn(),
      deleteWorkspaceReviewPack: vi.fn(),
      listWorkspaceAuditEvents: vi.fn(),
      getWorkspaceSecurityStatus: vi.fn(),
    },
  };
});

const apiMock = vi.mocked(api);

describe('WorkspaceApp API-backed states', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    Object.defineProperty(globalThis, 'crypto', {
      value: {
        subtle: {
          digest: vi.fn(async () => new Uint8Array(32).buffer),
        },
      },
      configurable: true,
    });
    Object.defineProperty(Element.prototype, 'scrollIntoView', {
      value: vi.fn(),
      configurable: true,
      writable: true,
    });
    apiMock.authLogout.mockResolvedValue({ ok: true });
    apiMock.authLock.mockResolvedValue({ ok: true });
    apiMock.downloadWorkspaceReviewPack.mockResolvedValue({
      blob: new Blob(['enc'], { type: 'application/octet-stream' }),
      filename: 'tax-review-pack-e1.enc.zip',
    });
    apiMock.listWorkspaceReviewPacks.mockResolvedValue([]);
    apiMock.listWorkspaceManualReviewDocuments.mockResolvedValue([]);
    apiMock.createWorkspaceManualItem.mockResolvedValue({
      id: "mi1",
      session_id: "s1",
      item_type: "needs_review",
      category: "needs_review",
      amount: null,
      description: "manual",
      confidence: 0,
      needs_review: true,
      review_status: "needs_review",
      review_reason: null,
      ato_reference_hint: null,
      reviewed_at: null,
      reviewed_by: "user",
      created_at: "",
    });
    apiMock.applyWorkspaceManualReviewAction.mockResolvedValue({ ok: true });
    apiMock.listWorkspaceDocuments.mockResolvedValue([]);
    apiMock.uploadWorkspaceDocument.mockResolvedValue({
      document_id: 'd1',
      job_id: 'j1',
      job_type: 'ingestion_pipeline',
      job_status: 'queued',
      message: 'Document upload accepted',
    });
    apiMock.listJobs.mockResolvedValue([]);
    apiMock.listWorkspaceAuditEvents.mockResolvedValue([]);
    apiMock.getWorkspaceSecurityStatus.mockResolvedValue({
      encryption_enabled: 'field_level_partial',
      export_encryption_enabled: true,
      session_status: 'UNLOCKED',
      recovery_key_configured: true,
      last_unlock_at: null,
      plaintext_readiness: {
        document_pages: { total_rows: 0, plaintext_only_rows: 0, encrypted_rows: 0, mixed_rows: 0, migration_completion_percent: 100 },
        tax_items: { total_rows: 0, plaintext_only_rows: 0, encrypted_rows: 0, mixed_rows: 0, migration_completion_percent: 100 },
        classification_results: { total_rows: 0, plaintext_only_rows: 0, encrypted_rows: 0, mixed_rows: 0, migration_completion_percent: 100 },
        overall_migration_completion_percent: 100,
      },
      migration_readiness: { can_disable_plaintext_fallback: true, blocking_tables: [], legacy_read_paths: [] },
      operational_visibility: { backup_status: 'manual_runbook', locked_write_counter: 0, failed_unlock_counter: 0, capability_metrics: {} },
      recent_security_events: [],
    });
    apiMock.workspaceReviewPackDownloadUrl.mockImplementation((workspaceId: string, exportId: string) => `/api/workspaces/${workspaceId}/review-pack/${exportId}/download`);
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

  it('requires unlock after refresh when session is authenticated but lock state is returned', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'LOCKED' });
    render(<WorkspaceApp />);
    expect(await screen.findByText('Unlock Workspace')).toBeInTheDocument();
    expect(screen.queryByTestId('unlocked-shell')).toBeNull();
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

  it('shows graceful fallback when workspace context is missing', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open Documents' }));
    expect(await screen.findByText('No workspace selected. Choose a Tax Year Workspace to continue.')).toBeInTheDocument();
  });

  it('opens workspace sections from dashboard actions without legacy route links', async () => {
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
    const beforePath = window.location.pathname;
    fireEvent.click(screen.getByRole('button', { name: 'Open Documents' }));
    expect(await screen.findByTestId('documents-panel')).toBeInTheDocument();
    expect(screen.getByText('Upload Document')).toBeInTheDocument();
    expect(window.location.pathname).toBe(beforePath);
    expect(window.location.pathname).not.toContain('/documents');
    expect(window.location.pathname).not.toContain('/session/');
    fireEvent.click(screen.getByRole('button', { name: 'Review Items' }));
    expect(await screen.findByTestId('review-items-panel')).toBeInTheDocument();
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
    expect(actionPanel.textContent).not.toContain('Needs Review');
    expect(actionPanel.textContent).toContain('Exclude');
    expect(actionPanel.textContent).toContain('Tax Agent Review');
  });

  it('hides current-status action button for each item row', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 4, draft: 0, needs_review: 1, confirmed: 1, excluded: 1, tax_agent_review: 1, ready_for_export: false, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([
      { id: 'n1', session_id: 's1', item_type: 'deduction', category: 'tools_equipment', amount: 10, description: 'a', confidence: 0.9, needs_review: true, review_status: 'needs_review', review_reason: null, ato_reference_hint: null, reviewed_at: null, reviewed_by: null, created_at: '' },
      { id: 'c1', session_id: 's1', item_type: 'deduction', category: 'tools_equipment', amount: 10, description: 'b', confidence: 0.9, needs_review: false, review_status: 'confirmed', review_reason: null, ato_reference_hint: null, reviewed_at: null, reviewed_by: null, created_at: '' },
      { id: 'e1', session_id: 's1', item_type: 'deduction', category: 'tools_equipment', amount: 10, description: 'c', confidence: 0.9, needs_review: false, review_status: 'excluded', review_reason: null, ato_reference_hint: null, reviewed_at: null, reviewed_by: null, created_at: '' },
      { id: 't1', session_id: 's1', item_type: 'deduction', category: 'tools_equipment', amount: 10, description: 'd', confidence: 0.9, needs_review: true, review_status: 'tax_agent_review', review_reason: null, ato_reference_hint: null, reviewed_at: null, reviewed_by: null, created_at: '' },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Items' }));
    const rows = await screen.findAllByTestId('review-item-row');
    expect(rows[0].textContent).not.toContain('Needs Review');
    expect(rows[1].textContent).not.toContain('Confirm');
    expect(rows[2].textContent).not.toContain('Exclude');
    expect(rows[3].textContent).not.toContain('Tax Agent Review');
  });

  it('shows generate controls when review pack is ready', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    expect(await screen.findByRole('button', { name: 'Generate Encrypted Review Pack' })).toBeInTheDocument();
    expect(screen.getByText('This password is required to open the encrypted review pack. It cannot be recovered.')).toBeInTheDocument();
  });

  it('renders export history in review pack page', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceReviewPacks.mockResolvedValue([
      {
        id: 'e1',
        workspace_id: 'w1',
        filename: 'tax-review-pack-e1.enc.zip',
        status: 'ready',
        format: 'enc_zip_v1',
        encrypted: true,
        kdf: 'pbkdf2_sha256_600k',
        encryption_version: '1.0',
        kdf_params_summary: '{\"iterations\":600000}',
        created_at: '2026-01-01T00:00:00Z',
        downloaded_at: null,
        file_size: 100,
        sha256: 'abc',
        item_count: 1,
        document_count: 1,
        blocking_reasons: '[]',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    expect(await screen.findByTestId('export-history')).toBeInTheDocument();
    expect(screen.getByText('tax-review-pack-e1.enc.zip')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('renders recent workspace audit events', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceAuditEvents.mockResolvedValue([
      { id: 'a1', entity_type: 'export_package', entity_id: 'e1', action: 'review_pack_downloaded', changed_by: 'user', details: null, created_at: '2026-05-15T00:00:00Z' },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click((await screen.findByText('Recent Activity')).closest('button') as HTMLButtonElement);
    expect(await screen.findByTestId('audit-events-panel')).toBeInTheDocument();
    expect(screen.getByText('review pack downloaded')).toBeInTheDocument();
  });

  it('does not render legacy /session/:id navigation links', async () => {
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
    await screen.findByTestId('unlocked-shell');
    const legacyLink = document.querySelector('a[href^=\"/session/\"]');
    expect(legacyLink).toBeNull();
    const legacySectionLink = document.querySelector('a[href^=\"/documents\"], a[href^=\"/items\"], a[href^=\"/issues\"], a[href^=\"/review-pack\"]');
    expect(legacySectionLink).toBeNull();
    expect(screen.queryByRole('button', { name: 'Go to current workflow' })).toBeNull();
  });

  it('renders Documents empty state and no placeholder workflow bridge button', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    expect(await screen.findByTestId('documents-panel')).toBeInTheDocument();
    expect(screen.getByTestId('documents-empty-state')).toHaveTextContent(
      'No documents yet. Upload your first document to begin.'
    );
    expect(screen.queryByRole('button', { name: 'Go to current workflow' })).toBeNull();
  });

  it('shows explicit manual-review outcome when document has no extracted items', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, manual_review_documents: 1, ready_for_export: false, blocking_reasons: ['1 document(s) need manual review before export.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceManualReviewDocuments.mockResolvedValue([
      {
        id: 'd1',
        filename: 'scan.pdf',
        status: 'needs_review',
        status_reason: 'Classification produced no items — manual review required.',
        provider_mode: 'manual',
        item_count: 0,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd1',
        session_id: 's1',
        original_filename: 'scan.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 1234,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'needs_review',
        status_reason: 'Classification produced no items — manual review required.',
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    apiMock.listJobs.mockResolvedValue([
      {
        id: 'j1',
        session_id: 's1',
        document_id: 'd1',
        job_type: 'ingestion',
        status: 'succeeded',
        progress: 1,
        progress_message: 'No review items detected — manual review required',
        error_message: null,
        result_summary: '{"status":"needs_review","reason":"classification_produced_no_items","item_count":0}',
        queued_at: null,
        started_at: null,
        completed_at: null,
        created_at: null,
        updated_at: null,
      },
    ]);

    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    expect(await screen.findByText('Needs manual review. OCR/classification did not produce a complete item set for this document.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Review Items' }));
    expect(await screen.findByTestId('manual-review-document-card')).toBeInTheDocument();
    expect(screen.getByText('No extracted items yet. Review the documents below or add a manual item.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add manual item' })).toBeInTheDocument();
  });

  it('shows provider configuration warning for manual review when AI is not configured', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd2',
        session_id: 's1',
        original_filename: 'payslip.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 555,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'needs_review',
        status_reason: 'AI classification is not configured. Document needs manual review.',
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    apiMock.listJobs.mockResolvedValue([
      {
        id: 'j2',
        session_id: 's1',
        document_id: 'd2',
        job_type: 'ingestion',
        status: 'succeeded',
        progress: 1,
        progress_message: 'AI classification is not configured. Document needs manual review.',
        error_message: null,
        result_summary: '{"status":"needs_review","reason":"provider_not_configured"}',
        queued_at: null,
        started_at: null,
        completed_at: null,
        created_at: null,
        updated_at: null,
      },
    ]);

    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const warnings = await screen.findAllByText('AI classification is not configured. Document needs manual review.');
    expect(warnings.length).toBeGreaterThan(0);
  });

  it('blocks generate on password mismatch and shows length hint', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    fireEvent.change(screen.getByPlaceholderText('Export password'), { target: { value: 'short' } });
    fireEvent.change(screen.getByPlaceholderText('Confirm export password'), { target: { value: 'different' } });
    expect(screen.getByText('Minimum length: 12 characters.')).toBeInTheDocument();
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generate Encrypted Review Pack' })).toBeDisabled();
  });

  it('shows locked message when sensitive data key is unavailable', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockRejectedValue(new Error('API error 423'));
    render(<WorkspaceApp />);
    expect(await screen.findByText('Workspace is locked. Unlock to view sensitive tax data.')).toBeInTheDocument();
  });

  it('handles 401 sensitive errors with lock message', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockRejectedValue(new Error('API error 401'));
    render(<WorkspaceApp />);
    expect(await screen.findByText('Workspace is locked. Unlock to view sensitive tax data.')).toBeInTheDocument();
  });

  it('shows locked message when review status update is attempted while locked', async () => {
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
    apiMock.setWorkspaceItemReviewStatus.mockRejectedValue(new Error('API error 423'));
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Items' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Confirm' }));
    expect(await screen.findByText('Workspace is locked. Unlock to view sensitive tax data.')).toBeInTheDocument();
  });

  it('locks workspace when lock button is clicked', async () => {
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
    fireEvent.click(await screen.findByRole('button', { name: 'Lock Workspace' }));
    expect(apiMock.authLock).toHaveBeenCalledTimes(1);
    expect(await screen.findByText('Unlock Workspace')).toBeInTheDocument();
  });

  it('renders security status in settings panel', async () => {
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
    fireEvent.click(await screen.findByRole('button', { name: 'Settings' }));
    expect(await screen.findByTestId('security-settings-panel')).toBeInTheDocument();
    expect(screen.getByText(/Plaintext Migration Progress/)).toBeInTheDocument();
  });

  it('rejects unsupported upload type with friendly message', async () => {
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
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const badFile = new File(['dummy'], 'clip.mp4', { type: 'video/mp4' });
    fireEvent.change(input, { target: { files: [badFile] } });
    expect(await screen.findByText('Unsupported file type. Allowed formats: PDF, PNG, JPG/JPEG, CSV, TXT.')).toBeInTheDocument();
  });

  it('shows unlock message when upload fails due to locked workspace', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.uploadWorkspaceDocument.mockRejectedValue(new ApiError('Locked', 423, 'workspace_locked', false));
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const pdfFile = new File(['%PDF-1.4'], 'doc.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByText('Workspace is locked. Unlock to upload documents.')).toBeInTheDocument();
  });

  it('shows retry guidance for retryable processing failure', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.uploadWorkspaceDocument.mockRejectedValue(new ApiError('Temporary processing failure.', 503, 'temporary_processing_failure', true));
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const pdfFile = new File(['%PDF-1.4'], 'doc.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByText('Temporary processing failure. Try again.')).toBeInTheDocument();
  });

  it('uploads valid PDF successfully and shows processing started', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValueOnce([]).mockResolvedValueOnce([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const pdfFile = new File(['%PDF-1.4'], 'good.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByText('good.pdf uploaded. Processing has started.')).toBeInTheDocument();
  });

  it('shows duplicate message when refreshed documents include duplicate_detected', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd2',
        session_id: 's1',
        original_filename: 'dup.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'duplicate_detected',
        status_reason: null,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const pdfFile = new File(['%PDF-1.4'], 'dup.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByText('Duplicate file detected. Review and remove the duplicate copy if needed.')).toBeInTheDocument();
  });

  it('blocks exact duplicate upload and shows existing document actions', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([]);
    apiMock.uploadWorkspaceDocument.mockRejectedValue(
      new ApiError('This document was already uploaded.', 409, 'duplicate_file', false, {
        existing_document: {
          id: 'd-existing',
          original_filename: 'existing.pdf',
          created_at: '2026-05-16T00:00:00Z',
          status: 'classified',
        },
      })
    );
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const pdfFile = new File(['%PDF-1.4'], 'dup.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByTestId('duplicate-upload-info')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View existing document' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel upload' })).toBeInTheDocument();
  });

  it('cancel upload clears duplicate warning and selected file', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([]);
    apiMock.uploadWorkspaceDocument.mockRejectedValue(
      new ApiError('This document was already uploaded.', 409, 'duplicate_file', false, {
        existing_document: { id: 'd-existing', original_filename: 'existing.pdf', created_at: '2026-05-16T00:00:00Z', status: 'classified' },
      })
    );
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    fireEvent.change(input, { target: { files: [new File(['%PDF-1.4'], 'dup.pdf', { type: 'application/pdf' })] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByTestId('duplicate-upload-info')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel upload' }));
    expect(screen.queryByTestId('duplicate-upload-info')).toBeNull();
    expect(screen.queryByText(/Selected file:/)).toBeNull();
  });

  it('view existing document clears upload state and highlights the existing document row', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd-existing',
        session_id: 's1',
        original_filename: 'existing.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'classified',
        status_reason: null,
        item_count: 2,
        provider_mode: 'mock',
        retryable: false,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    apiMock.uploadWorkspaceDocument.mockRejectedValue(
      new ApiError('This document was already uploaded.', 409, 'duplicate_file', false, {
        existing_document: { id: 'd-existing', original_filename: 'existing.pdf', created_at: '2026-05-16T00:00:00Z', status: 'classified' },
      })
    );
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    fireEvent.change(input, { target: { files: [new File(['%PDF-1.4'], 'dup.pdf', { type: 'application/pdf' })] } });
    expect(screen.getByText(/Selected file:/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByTestId('duplicate-upload-info')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'View existing document' }));
    expect(screen.queryByTestId('duplicate-upload-info')).toBeNull();
    expect(screen.queryByText(/Selected file:/)).toBeNull();
    await waitFor(() => {
      const row = screen.getByText('existing.pdf').closest('article');
      expect(row?.className).toContain('bg-emerald-50');
    });
  });

  it('allows same filename with different content and shows warning only', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd-existing',
        session_id: 's1',
        original_filename: 'same.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
        category: null,
        financial_year: 'FY2025',
        status: 'classified',
        status_reason: null,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    const input = await screen.findByTestId('documents-file-input');
    const pdfFile = new File(['%PDF-1.4'], 'same.pdf', { type: 'application/pdf' });
    fireEvent.change(input, { target: { files: [pdfFile] } });
    fireEvent.click(screen.getByRole('button', { name: 'Upload document' }));
    expect(await screen.findByText('A document with this filename already exists.')).toBeInTheDocument();
    expect(screen.queryByText('same.pdf uploaded. Processing has started.')).toBeNull();
  });

  it('shows helpful review-items empty message when documents exist but no items extracted', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd1',
        session_id: 's1',
        original_filename: 'bank.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'needs_review',
        status_reason: 'Classification produced no items',
        provider_mode: 'manual',
        item_count: 0,
        retryable: false,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Items' }));
    expect(await screen.findByText('Documents exist but no items were extracted yet. Open Documents to review processing outcomes.')).toBeInTheDocument();
    expect(screen.getByText('Manual review mode is active for this workspace. You can still continue by reviewing document outcomes.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Documents' })).toBeInTheDocument();
  });

  it('shows retry button only for retryable failed document', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 0, draft: 0, needs_review: 0, confirmed: 0, excluded: 0, tax_agent_review: 0, ready_for_export: false, blocking_reasons: ['No review items available yet.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd1',
        session_id: 's1',
        original_filename: 'retryable.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'classification_failed',
        status_reason: 'Temporary processing failure',
        provider_mode: 'cloud',
        item_count: 0,
        retryable: true,
        created_at: '2026-05-16T00:00:00Z',
      },
      {
        id: 'd2',
        session_id: 's1',
        original_filename: 'manual.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'classification_failed',
        status_reason: 'Missing required fields',
        provider_mode: 'manual',
        item_count: 0,
        retryable: false,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Documents' }));
    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: 'Retry processing' }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole('button', { name: 'Replace document' }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole('button', { name: 'Delete failed document' }).length).toBeGreaterThan(0);
    });
  });

  it('shows review-pack blocker reason when export is disabled', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 2,
      draft: 0,
      needs_review: 2,
      confirmed: 0,
      excluded: 0,
      tax_agent_review: 0,
      ready_for_export: false,
      blocking_reasons: ['2 item(s) still need review.'],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    expect(await screen.findByTestId('review-pack-blockers')).toBeInTheDocument();
    expect(await screen.findByText('2 item(s) still need review.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Go to Review Items' })).toBeInTheDocument();
  });

  it('ready state explains encrypted review pack contents', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.listWorkspaceDocuments.mockResolvedValue([
      {
        id: 'd1',
        session_id: 's1',
        original_filename: 'receipt.pdf',
        mime_type: 'application/pdf',
        file_size_bytes: 100,
        file_hash: null,
        category: null,
        financial_year: 'FY2025',
        status: 'classified',
        status_reason: null,
        provider_mode: 'cloud',
        item_count: 2,
        retryable: false,
        created_at: '2026-05-16T00:00:00Z',
      },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 2, draft: 0, needs_review: 0, confirmed: 2, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    expect(await screen.findByText('Review summary prepared for human review')).toBeInTheDocument();
    expect(screen.getByText('Extracted item list for cross-checking')).toBeInTheDocument();
    expect(screen.getByText('Evidence reference index for supporting documents')).toBeInTheDocument();
    expect(screen.getByText('This package is prepared for human review, not a final tax return, and not submitted to ATO.')).toBeInTheDocument();
  });

  it('export history metadata and checksum copy action render', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceReviewPacks.mockResolvedValue([
      {
        id: 'e1',
        workspace_id: 'w1',
        filename: 'tax-review-pack-e1.enc.zip',
        status: 'ready',
        format: 'enc_zip_v1',
        encrypted: true,
        kdf: 'pbkdf2_sha256_600k',
        encryption_version: '1.0',
        kdf_params_summary: '{"iterations":600000}',
        created_at: '2026-01-01T00:00:00Z',
        downloaded_at: '2026-01-02T00:00:00Z',
        file_size: 100,
        sha256: 'abcdef1234567890',
        item_count: 1,
        document_count: 1,
        blocking_reasons: '[]',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    expect(await screen.findByText('tax-review-pack-e1.enc.zip')).toBeInTheDocument();
    expect(screen.getByText(/100 bytes · sha256 abcdef123456/)).toBeInTheDocument();
    expect(screen.getByText(/Downloaded:/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Copy checksum' })).toBeInTheDocument();
  });

  it('downloads existing export from history', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceReviewPacks.mockResolvedValue([
      {
        id: 'e1', workspace_id: 'w1', filename: 'tax-review-pack-e1.enc.zip', status: 'ready',
        format: 'enc_zip_v1', encrypted: true, kdf: 'pbkdf2_sha256_600k', encryption_version: '1.0',
        kdf_params_summary: '{"iterations":600000}', created_at: '2026-01-01T00:00:00Z', downloaded_at: null,
        file_size: 100, sha256: 'abcdef1234567890', item_count: 1, document_count: 1, blocking_reasons: '[]',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Download' }));
    await waitFor(() => {
      expect(apiMock.downloadWorkspaceReviewPack).toHaveBeenCalledWith('w1', 'e1');
    });
  });

  it('deleting nonexistent export shows graceful message and removes card', async () => {
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceReviewPacks.mockResolvedValue([
      {
        id: 'e1', workspace_id: 'w1', filename: 'tax-review-pack-e1.enc.zip', status: 'ready',
        format: 'enc_zip_v1', encrypted: true, kdf: 'pbkdf2_sha256_600k', encryption_version: '1.0',
        kdf_params_summary: '{"iterations":600000}', created_at: '2026-01-01T00:00:00Z', downloaded_at: null,
        file_size: 100, sha256: 'abcdef1234567890', item_count: 1, document_count: 1, blocking_reasons: '[]',
      },
    ]);
    apiMock.deleteWorkspaceReviewPack.mockRejectedValue(new ApiError('not found', 404));
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    expect(await screen.findByText('tax-review-pack-e1.enc.zip')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: 'Delete' }));
    expect(await screen.findByText('Review pack was already removed.')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText('tax-review-pack-e1.enc.zip')).toBeNull();
    });
  });

  it('checksum toast auto-dismisses and does not persist', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });
    apiMock.authSetupStatus.mockResolvedValue({ is_configured: true, auth_mode: 'local', has_active_user: true });
    apiMock.authSession.mockResolvedValue({ is_authenticated: true, app_state: 'UNLOCKED' });
    apiMock.listWorkspaces.mockResolvedValue([
      { id: 'w1', user_id: 'u1', tax_year: 'FY2025', label: 'FY2025 Workspace', status: 'active', created_at: '', updated_at: '', last_opened_at: null },
    ]);
    apiMock.getWorkspaceReviewSummary.mockResolvedValue({
      total_items: 1, draft: 0, needs_review: 0, confirmed: 1, excluded: 0, tax_agent_review: 0, ready_for_export: true, blocking_reasons: [],
    });
    apiMock.listWorkspaceItems.mockResolvedValue([]);
    apiMock.listWorkspaceReviewPacks.mockResolvedValue([
      {
        id: 'e1',
        workspace_id: 'w1',
        filename: 'tax-review-pack-e1.enc.zip',
        status: 'ready',
        format: 'enc_zip_v1',
        encrypted: true,
        kdf: 'pbkdf2_sha256_600k',
        encryption_version: '1.0',
        kdf_params_summary: '{"iterations":600000}',
        created_at: '2026-01-01T00:00:00Z',
        downloaded_at: null,
        file_size: 100,
        sha256: 'abcdef1234567890',
        item_count: 1,
        document_count: 1,
        blocking_reasons: '[]',
      },
    ]);
    render(<WorkspaceApp />);
    fireEvent.click(await screen.findByRole('button', { name: 'Review Pack' }));
    const copyButton = await screen.findByRole('button', { name: 'Copy checksum' });
    fireEvent.click(copyButton);
    expect(await screen.findByTestId('toast-notification')).toBeInTheDocument();
    await waitFor(
      () => {
        expect(screen.queryByTestId('toast-notification')).toBeNull();
      },
      { timeout: 4500 }
    );
    expect(screen.queryByText('Checksum copied for local verification.')).toBeNull();
  });
});
