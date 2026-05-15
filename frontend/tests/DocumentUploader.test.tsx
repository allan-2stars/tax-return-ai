import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DocumentUploader } from '@/components/DocumentUploader';

// Mock the global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('DocumentUploader', () => {
  const defaultProps = {
    sessionId: 'session-123',
    financialYear: '2025-2026',
    onUploaded: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders file input and upload button', () => {
    render(<DocumentUploader {...defaultProps} />);
    expect(screen.getByText('Upload')).toBeInTheDocument();
  });

  it('renders category selector', () => {
    render(<DocumentUploader {...defaultProps} />);
    expect(screen.getByDisplayValue('Receipt')).toBeInTheDocument();
  });

  it('disables upload button when no file selected', () => {
    render(<DocumentUploader {...defaultProps} />);
    expect(screen.getByText('Upload')).toBeDisabled();
  });

  it('shows JobStatusBanner after upload', async () => {
    const userEvent = await import('@testing-library/user-event').then((m) => m.default);
    const user = userEvent.setup();

    // Mock upload response
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        document_id: 'doc-1',
        job_id: 'job-1',
        job_type: 'ingestion',
        job_status: 'queued',
        message: 'Document uploaded. Ingestion pipeline queued.',
      }),
    });

    render(<DocumentUploader {...defaultProps} />);

    // Select a file using the file input
    const fileInput = screen.getByLabelText(/file/i) || document.querySelector('input[type="file"]');
    if (fileInput) {
      const file = new File(['dummy content'], 'test.pdf', { type: 'application/pdf' });
      await user.upload(fileInput, file);
    }

    // Click upload
    const uploadBtn = screen.getByText('Upload');
    await user.click(uploadBtn);

    // After upload, the component should show the job status banner
    expect(screen.getByText(/Waiting for job|ingestion/i)).toBeInTheDocument();
  });
});
