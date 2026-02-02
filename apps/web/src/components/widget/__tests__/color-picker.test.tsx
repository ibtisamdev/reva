import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ColorPicker } from '../color-picker';

describe('ColorPicker', () => {
  it('renders color swatch with current value', () => {
    const { container } = render(<ColorPicker value="#0d9488" onChange={vi.fn()} />);
    const swatch = container.querySelector('[style*="background"]');
    expect(swatch).toBeTruthy();
  });

  it('renders hex input with current value', () => {
    render(<ColorPicker value="#0d9488" onChange={vi.fn()} />);
    expect(screen.getByDisplayValue('#0d9488')).toBeInTheDocument();
  });

  it('renders optional label', () => {
    render(<ColorPicker value="#0d9488" onChange={vi.fn()} label="Brand Color" />);
    expect(screen.getByText('Brand Color')).toBeInTheDocument();
  });

  it('calls onChange for valid hex input', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ColorPicker value="#0d9488" onChange={onChange} />);

    const input = screen.getByDisplayValue('#0d9488');
    await user.clear(input);
    await user.type(input, '#ff0000');

    expect(onChange).toHaveBeenCalledWith('#ff0000');
  });

  it('does not call onChange for invalid hex', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<ColorPicker value="#0d9488" onChange={onChange} />);

    const input = screen.getByDisplayValue('#0d9488');
    await user.clear(input);
    await user.type(input, 'not-hex');

    expect(onChange).not.toHaveBeenCalled();
  });
});
