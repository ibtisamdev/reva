import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { UrlUploadForm } from '../url-upload-form';

describe('UrlUploadForm', () => {
  it('renders URL input, title input, content type select, and submit button', () => {
    render(<UrlUploadForm onSubmit={vi.fn()} />);
    expect(screen.getByLabelText('URL')).toBeInTheDocument();
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/content type/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /import url/i })).toBeInTheDocument();
  });

  it('submit button is disabled when URL is empty', () => {
    render(<UrlUploadForm onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: /import url/i })).toBeDisabled();
  });

  it('calls onSubmit with url and default content_type', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlUploadForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('URL'), 'https://example.com/page');
    await user.click(screen.getByRole('button', { name: /import url/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      url: 'https://example.com/page',
      title: undefined,
      content_type: 'page',
    });
  });

  it('calls onSubmit with title when provided', async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UrlUploadForm onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText('URL'), 'https://example.com');
    await user.type(screen.getByLabelText(/title/i), 'My Page');
    await user.click(screen.getByRole('button', { name: /import url/i }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'My Page' })
    );
  });

  it('shows loading state', () => {
    render(<UrlUploadForm onSubmit={vi.fn()} isLoading />);
    expect(screen.getByRole('button', { name: /importing/i })).toBeDisabled();
  });
});
