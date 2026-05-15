import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExportButton } from '@/components/ExportButton';

const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('ExportButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock URL.createObjectURL
    global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    global.URL.revokeObjectURL = vi.fn();
  });

  it('renders export button', () => {
    render(<ExportButton sessionId="session-123" />);
    expect(screen.getByText('Export Review Package')).toBeInTheDocument();
  });

  it('fetches export data on click', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session: { id: 'session-123' },
        summary: { total_documents: 2, total_items: 3 },
        income_items: [],
        deduction_items: [],
        needs_review_items: [],
        out_of_scope_items: [],
        source_documents: [],
        export_warnings: [],
        export_metadata: {
          generated_at: '2026-05-14T01:22:07.709811',
          disclaimer: 'Draft review package — not a tax return.',
          status: 'draft',
        },
      }),
    });

    render(<ExportButton sessionId="session-123" />);
    fireEvent.click(screen.getByText('Export Review Package'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/export/session-123'),
        expect.any(Object),
      );
    });
  });

  it('shows error alert on failed export', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

    render(<ExportButton sessionId="session-123" />);
    fireEvent.click(screen.getByText('Export Review Package'));

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalled();
    });

    alertSpy.mockRestore();
  });
});
