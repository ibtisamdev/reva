/**
 * Widget configuration module.
 * Reads configuration from window.RevaConfig and provides theme utilities.
 */

import type { WidgetConfig } from '../types';

// Default API URL from Vite env or fallback
const DEFAULT_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// === Color Utility Functions ===

/**
 * Parse a hex color to RGB components.
 */
function hexToRgb(hex: string): [number, number, number] | null {
  // Remove # if present and handle shorthand
  const cleanHex = hex.replace('#', '');
  const fullHex =
    cleanHex.length === 3
      ? cleanHex
          .split('')
          .map((c) => c + c)
          .join('')
      : cleanHex;

  const result = /^([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(fullHex);
  return result
    ? [parseInt(result[1], 16), parseInt(result[2], 16), parseInt(result[3], 16)]
    : null;
}

/**
 * Convert RGB to hex color.
 */
function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) => {
    const clamped = Math.max(0, Math.min(255, Math.round(n)));
    return clamped.toString(16).padStart(2, '0');
  };
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * Calculate relative luminance for WCAG contrast calculations.
 * https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
function getLuminance(hex: string): number {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0.5;

  const [r, g, b] = rgb.map((c) => {
    const sRGB = c / 255;
    return sRGB <= 0.03928 ? sRGB / 12.92 : Math.pow((sRGB + 0.055) / 1.055, 2.4);
  });

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Darken a hex color by a percentage.
 */
function darken(hex: string, percent: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;

  const factor = 1 - percent / 100;
  return rgbToHex(rgb[0] * factor, rgb[1] * factor, rgb[2] * factor);
}

/**
 * Get contrasting foreground color (white or dark) for accessibility.
 * Uses WCAG luminance threshold.
 */
function getContrastColor(hex: string): string {
  const luminance = getLuminance(hex);
  // Use dark text for light backgrounds, white for dark backgrounds
  return luminance > 0.5 ? '#1f2937' : '#ffffff';
}

// === Theme Variables ===

/**
 * Generate CSS custom properties for a given primary color.
 * Ensures accessibility by calculating appropriate contrast colors.
 */
export function getThemeVariables(primaryColor?: string): Record<string, string> {
  if (!primaryColor) return {};

  const foreground = getContrastColor(primaryColor);
  const hoverColor = darken(primaryColor, 12);

  return {
    '--reva-primary': primaryColor,
    '--reva-primary-hover': hoverColor,
    '--reva-primary-foreground': foreground,
    '--reva-user-bg': primaryColor,
    '--reva-user-text': foreground,
  };
}

// === Configuration ===

/**
 * Get widget configuration from window.RevaConfig.
 * Provides defaults for missing values.
 */
export function getConfig(): WidgetConfig {
  const config = window.RevaConfig || {};

  // Warn if storeId is missing (required for API calls)
  if (!config.storeId) {
    console.warn(
      'Reva Widget: storeId is not configured. Set window.RevaConfig.storeId before loading the widget.'
    );
  }

  return {
    storeId: config.storeId || '',
    apiUrl: config.apiUrl || DEFAULT_API_URL,
    theme: {
      primaryColor: config.theme?.primaryColor,
    },
    position: config.position || 'right',
  };
}
