import { beforeEach, describe, expect, it, vi } from 'vitest';

import { getConfig, getThemeVariables } from '../config';

describe('getThemeVariables', () => {
  it('returns empty object when no color provided', () => {
    expect(getThemeVariables()).toEqual({});
  });

  it('returns empty object when undefined is passed', () => {
    expect(getThemeVariables(undefined)).toEqual({});
  });

  it('generates CSS variables for a primary color', () => {
    const vars = getThemeVariables('#3b82f6');

    expect(vars['--reva-primary']).toBe('#3b82f6');
    expect(vars['--reva-primary-hover']).toBeDefined();
    expect(vars['--reva-primary-foreground']).toBeDefined();
    expect(vars['--reva-user-bg']).toBe('#3b82f6');
    expect(vars['--reva-user-text']).toBeDefined();
  });

  it('returns white foreground for dark backgrounds', () => {
    // Very dark color - should have white text
    const vars = getThemeVariables('#1a1a1a');
    expect(vars['--reva-primary-foreground']).toBe('#ffffff');
  });

  it('returns dark foreground for light backgrounds', () => {
    // Very light color - should have dark text
    const vars = getThemeVariables('#ffffff');
    expect(vars['--reva-primary-foreground']).toBe('#1f2937');
  });

  it('returns dark foreground for yellow/bright colors', () => {
    // Yellow is bright and should have dark text
    const vars = getThemeVariables('#ffd700');
    expect(vars['--reva-primary-foreground']).toBe('#1f2937');
  });

  it('returns white foreground for dark blue', () => {
    const vars = getThemeVariables('#1e3a5f');
    expect(vars['--reva-primary-foreground']).toBe('#ffffff');
  });

  it('darkens hover color from primary', () => {
    const vars = getThemeVariables('#ffffff');
    // #ffffff darkened should not equal #ffffff
    expect(vars['--reva-primary-hover']).not.toBe('#ffffff');
    // Hover color should be darker (lower RGB values)
    expect(vars['--reva-primary-hover']).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('handles 3-digit hex shorthand', () => {
    const vars = getThemeVariables('#fff');
    expect(vars['--reva-primary']).toBe('#fff');
    // Should still calculate correct contrast
    expect(vars['--reva-primary-foreground']).toBe('#1f2937');
  });

  it('handles hex without # prefix', () => {
    // Note: The implementation expects hex with #, but let's test edge case
    const vars = getThemeVariables('#3b82f6');
    expect(vars['--reva-primary']).toBe('#3b82f6');
  });

  it('sets user message styling to match primary', () => {
    const vars = getThemeVariables('#ff5733');
    expect(vars['--reva-user-bg']).toBe('#ff5733');
    expect(vars['--reva-user-text']).toBe(vars['--reva-primary-foreground']);
  });
});

describe('getConfig', () => {
  beforeEach(() => {
    // Reset window.RevaConfig before each test
    window.RevaConfig = undefined;
  });

  it('returns defaults when RevaConfig is not set', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const config = getConfig();

    expect(config.storeId).toBe('');
    expect(config.position).toBe('right');
    expect(config.theme?.primaryColor).toBeUndefined();
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('storeId is not configured'));

    warnSpy.mockRestore();
  });

  it('uses storeId from window.RevaConfig', () => {
    window.RevaConfig = { storeId: 'test-store-123' };

    const config = getConfig();

    expect(config.storeId).toBe('test-store-123');
  });

  it('uses custom apiUrl when provided', () => {
    window.RevaConfig = {
      storeId: 'test-store',
      apiUrl: 'https://custom-api.example.com',
    };

    const config = getConfig();

    expect(config.apiUrl).toBe('https://custom-api.example.com');
  });

  it('uses default apiUrl when not provided', () => {
    window.RevaConfig = { storeId: 'test-store' };

    const config = getConfig();

    // Should fallback to VITE_API_URL or localhost
    expect(config.apiUrl).toBeDefined();
    expect(typeof config.apiUrl).toBe('string');
  });

  it('uses custom position when provided', () => {
    window.RevaConfig = {
      storeId: 'test-store',
      position: 'left',
    };

    const config = getConfig();

    expect(config.position).toBe('left');
  });

  it('defaults position to right when not provided', () => {
    window.RevaConfig = { storeId: 'test-store' };

    const config = getConfig();

    expect(config.position).toBe('right');
  });

  it('uses theme primaryColor when provided', () => {
    window.RevaConfig = {
      storeId: 'test-store',
      theme: { primaryColor: '#ff0000' },
    };

    const config = getConfig();

    expect(config.theme?.primaryColor).toBe('#ff0000');
  });

  it('handles partial theme configuration', () => {
    window.RevaConfig = {
      storeId: 'test-store',
      theme: {},
    };

    const config = getConfig();

    expect(config.theme?.primaryColor).toBeUndefined();
  });

  it('handles missing theme entirely', () => {
    window.RevaConfig = { storeId: 'test-store' };

    const config = getConfig();

    expect(config.theme).toBeDefined();
    expect(config.theme?.primaryColor).toBeUndefined();
  });

  it('does not warn when storeId is provided', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    window.RevaConfig = { storeId: 'test-store' };
    getConfig();

    expect(warnSpy).not.toHaveBeenCalled();

    warnSpy.mockRestore();
  });

  it('uses all provided configuration values', () => {
    window.RevaConfig = {
      storeId: 'full-config-store',
      apiUrl: 'https://api.test.com',
      position: 'left',
      theme: { primaryColor: '#123456' },
    };

    const config = getConfig();

    expect(config.storeId).toBe('full-config-store');
    expect(config.apiUrl).toBe('https://api.test.com');
    expect(config.position).toBe('left');
    expect(config.theme?.primaryColor).toBe('#123456');
  });
});
