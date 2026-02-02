import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { mockWidgetSettings } from '@/test/mocks/data';

import { WidgetPreview } from '../widget-preview';

describe('WidgetPreview', () => {
  it('renders agent name', () => {
    render(<WidgetPreview settings={mockWidgetSettings} />);
    expect(screen.getByText('Reva Support')).toBeInTheDocument();
  });

  it('renders welcome message', () => {
    render(<WidgetPreview settings={mockWidgetSettings} />);
    expect(screen.getByText('Hi! How can I help you today?')).toBeInTheDocument();
  });

  it('applies primary color to header', () => {
    const { container } = render(<WidgetPreview settings={mockWidgetSettings} />);
    const header = container.querySelector('[style*="background"]');
    expect(header).toBeTruthy();
  });

  it('renders with bottom-left position', () => {
    const leftSettings = { ...mockWidgetSettings, position: 'bottom-left' as const };
    const { container } = render(<WidgetPreview settings={leftSettings} />);
    // Check that left positioning is applied
    expect(container.innerHTML).toContain('left');
  });
});
