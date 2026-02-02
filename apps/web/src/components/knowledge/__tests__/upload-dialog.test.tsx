import { render, screen } from '@/test/utils';
import { describe, expect, it, vi } from 'vitest';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}));

import { UploadDialog } from '../upload-dialog';

describe('UploadDialog', () => {
  it('renders dialog with tabs when open', () => {
    render(<UploadDialog open={true} onOpenChange={vi.fn()} storeId="store-1" />);
    expect(screen.getByText('Add Knowledge Content')).toBeInTheDocument();
    expect(screen.getByText('Text')).toBeInTheDocument();
  });

  it('shows PDF and URL tabs', () => {
    render(<UploadDialog open={true} onOpenChange={vi.fn()} storeId="store-1" />);
    expect(screen.getByText('PDF')).toBeInTheDocument();
    expect(screen.getByText('URL')).toBeInTheDocument();
  });

  it('renders TextUploadForm in text tab', () => {
    render(<UploadDialog open={true} onOpenChange={vi.fn()} storeId="store-1" />);
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<UploadDialog open={false} onOpenChange={vi.fn()} storeId="store-1" />);
    expect(screen.queryByText('Add Knowledge Content')).not.toBeInTheDocument();
  });
});
