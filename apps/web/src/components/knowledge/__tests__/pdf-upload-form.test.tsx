import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { PdfUploadForm } from '../pdf-upload-form';

describe('PdfUploadForm', () => {
  it('renders drop zone with instructions', () => {
    render(<PdfUploadForm onSubmit={vi.fn()} />);
    expect(screen.getByText(/drag and drop a pdf here/i)).toBeInTheDocument();
    expect(screen.getByText('browse files')).toBeInTheDocument();
  });

  it('shows file info after selecting a PDF', async () => {
    const user = userEvent.setup();
    render(<PdfUploadForm onSubmit={vi.fn()} />);

    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument();
  });

  it('rejects non-PDF files', async () => {
    const user = userEvent.setup();
    render(<PdfUploadForm onSubmit={vi.fn()} />);

    const file = new File(['text'], 'test.txt', { type: 'text/plain' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);

    expect(screen.queryByText('test.txt')).not.toBeInTheDocument();
    expect(screen.getByText(/drag and drop a pdf here/i)).toBeInTheDocument();
  });

  it('removes file when Remove is clicked', async () => {
    const user = userEvent.setup();
    render(<PdfUploadForm onSubmit={vi.fn()} />);

    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    expect(screen.getByText('test.pdf')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /remove/i }));
    expect(screen.queryByText('test.pdf')).not.toBeInTheDocument();
    expect(screen.getByText(/drag and drop a pdf here/i)).toBeInTheDocument();
  });

  it('submit button is disabled when no file selected', () => {
    render(<PdfUploadForm onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: /upload pdf/i })).toBeDisabled();
  });

  it('calls onSubmit with FormData containing file and content_type', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PdfUploadForm onSubmit={onSubmit} />);

    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    await user.click(screen.getByRole('button', { name: /upload pdf/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const formData = onSubmit.mock.calls[0][0] as FormData;
    expect(formData.get('file')).toBeTruthy();
    expect(formData.get('content_type')).toBe('guide');
  });

  it('includes title in FormData when provided', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<PdfUploadForm onSubmit={onSubmit} />);

    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    await user.upload(input, file);
    await user.type(screen.getByLabelText(/title/i), 'My PDF');
    await user.click(screen.getByRole('button', { name: /upload pdf/i }));

    const formData = onSubmit.mock.calls[0][0] as FormData;
    expect(formData.get('title')).toBe('My PDF');
  });

  it('shows loading state', () => {
    render(<PdfUploadForm onSubmit={vi.fn()} isLoading />);
    expect(screen.getByRole('button', { name: /uploading/i })).toBeDisabled();
  });
});
