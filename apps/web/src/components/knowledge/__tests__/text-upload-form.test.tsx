import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TextUploadForm } from '../text-upload-form';

describe('TextUploadForm', () => {
  it('renders title, content, content type, and source URL fields', () => {
    render(<TextUploadForm onSubmit={vi.fn()} />);
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Content')).toBeInTheDocument();
    expect(screen.getByLabelText('Content Type')).toBeInTheDocument();
    expect(screen.getByLabelText(/source url/i)).toBeInTheDocument();
  });

  it('submit button is disabled when required fields are empty', () => {
    render(<TextUploadForm onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: /upload/i })).toBeDisabled();
  });

  it('submit button is enabled when title and content are filled', async () => {
    const user = userEvent.setup();
    render(<TextUploadForm onSubmit={vi.fn()} />);

    await user.type(screen.getByLabelText(/title/i), 'Test Title');
    await user.type(screen.getByLabelText('Content'), 'Some content');

    expect(screen.getByRole('button', { name: /upload/i })).toBeEnabled();
  });

  it('calls onSubmit with trimmed data', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<TextUploadForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText(/title/i), '  Test Title  ');
    await user.type(screen.getByLabelText('Content'), '  Some content  ');
    await user.click(screen.getByRole('button', { name: /upload/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Test Title',
        content: 'Some content',
        content_type: 'faq',
      })
    );
  });

  it('shows loading state', () => {
    render(<TextUploadForm onSubmit={vi.fn()} isLoading />);
    expect(screen.getByRole('button', { name: /uploading/i })).toBeDisabled();
  });

  it('displays character count', async () => {
    const user = userEvent.setup();
    render(<TextUploadForm onSubmit={vi.fn()} />);
    await user.type(screen.getByLabelText('Content'), 'Hello');
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });
});
