import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getPageContext, onPageChange } from '../context';

describe('getPageContext', () => {
  const originalLocation = window.location;
  const originalTitle = document.title;

  beforeEach(() => {
    // Mock window.location
    Object.defineProperty(window, 'location', {
      value: { href: 'https://shop.example.com/' },
      writable: true,
      configurable: true,
    });
    // Mock document.title
    Object.defineProperty(document, 'title', {
      value: 'Test Page',
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    // Restore originals
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(document, 'title', {
      value: originalTitle,
      writable: true,
      configurable: true,
    });
  });

  it('returns current page URL', () => {
    window.location.href = 'https://shop.example.com/about';

    const context = getPageContext();

    expect(context.page_url).toBe('https://shop.example.com/about');
  });

  it('returns current page title', () => {
    Object.defineProperty(document, 'title', {
      value: 'About Us - My Store',
      writable: true,
      configurable: true,
    });

    const context = getPageContext();

    expect(context.page_title).toBe('About Us - My Store');
  });

  it('extracts product handle from /products/slug URL', () => {
    window.location.href = 'https://shop.example.com/products/awesome-widget';

    const context = getPageContext();

    expect(context.product_handle).toBe('awesome-widget');
    expect(context.product_id).toBe('awesome-widget');
  });

  it('extracts product handle from URL with query params', () => {
    window.location.href = 'https://shop.example.com/products/awesome-widget?variant=123';

    const context = getPageContext();

    expect(context.product_handle).toBe('awesome-widget');
  });

  it('extracts product handle from URL with hash', () => {
    window.location.href = 'https://shop.example.com/products/awesome-widget#reviews';

    const context = getPageContext();

    expect(context.product_handle).toBe('awesome-widget');
  });

  it('extracts product handle from collections URL', () => {
    window.location.href = 'https://shop.example.com/collections/all/products/my-product';

    const context = getPageContext();

    expect(context.product_handle).toBe('my-product');
  });

  it('extracts product handle from nested collections URL', () => {
    window.location.href = 'https://shop.example.com/collections/summer-sale/products/beach-towel';

    const context = getPageContext();

    expect(context.product_handle).toBe('beach-towel');
  });

  it('returns undefined handle for non-product pages', () => {
    window.location.href = 'https://shop.example.com/about';

    const context = getPageContext();

    expect(context.product_handle).toBeUndefined();
    expect(context.product_id).toBeUndefined();
  });

  it('returns undefined handle for home page', () => {
    window.location.href = 'https://shop.example.com/';

    const context = getPageContext();

    expect(context.product_handle).toBeUndefined();
  });

  it('returns undefined handle for collections page without product', () => {
    window.location.href = 'https://shop.example.com/collections/all';

    const context = getPageContext();

    expect(context.product_handle).toBeUndefined();
  });

  it('returns undefined handle for cart page', () => {
    window.location.href = 'https://shop.example.com/cart';

    const context = getPageContext();

    expect(context.product_handle).toBeUndefined();
  });

  it('handles product handles with hyphens', () => {
    window.location.href = 'https://shop.example.com/products/super-awesome-product-v2';

    const context = getPageContext();

    expect(context.product_handle).toBe('super-awesome-product-v2');
  });

  it('handles product handles with numbers', () => {
    window.location.href = 'https://shop.example.com/products/product-123';

    const context = getPageContext();

    expect(context.product_handle).toBe('product-123');
  });
});

describe('onPageChange', () => {
  let originalPushState: typeof history.pushState;
  let originalReplaceState: typeof history.replaceState;

  beforeEach(() => {
    originalPushState = history.pushState;
    originalReplaceState = history.replaceState;
  });

  afterEach(() => {
    // Restore original history methods
    history.pushState = originalPushState;
    history.replaceState = originalReplaceState;
  });

  it('calls callback on pushState', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    history.pushState({}, '', '/new-page');

    expect(callback).toHaveBeenCalledTimes(1);

    cleanup();
  });

  it('calls callback on replaceState', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    history.replaceState({}, '', '/replaced-page');

    expect(callback).toHaveBeenCalledTimes(1);

    cleanup();
  });

  it('calls callback multiple times for multiple navigations', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    history.pushState({}, '', '/page-1');
    history.pushState({}, '', '/page-2');
    history.replaceState({}, '', '/page-3');

    expect(callback).toHaveBeenCalledTimes(3);

    cleanup();
  });

  it('restores original pushState on cleanup', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    // Before cleanup, pushState should be patched (calling it triggers callback)
    history.pushState({}, '', '/test');
    expect(callback).toHaveBeenCalledTimes(1);

    cleanup();

    // After cleanup, pushState should no longer trigger callback
    callback.mockClear();
    history.pushState({}, '', '/after-cleanup');
    expect(callback).not.toHaveBeenCalled();
  });

  it('restores original replaceState on cleanup', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    // Before cleanup, replaceState should be patched (calling it triggers callback)
    history.replaceState({}, '', '/test');
    expect(callback).toHaveBeenCalledTimes(1);

    cleanup();

    // After cleanup, replaceState should no longer trigger callback
    callback.mockClear();
    history.replaceState({}, '', '/after-cleanup');
    expect(callback).not.toHaveBeenCalled();
  });

  it('stops calling callback after cleanup', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    history.pushState({}, '', '/before-cleanup');
    expect(callback).toHaveBeenCalledTimes(1);

    cleanup();

    // After cleanup, pushState calls should not trigger callback
    history.pushState({}, '', '/after-cleanup');
    expect(callback).toHaveBeenCalledTimes(1); // Still 1, not 2
  });

  it('passes through arguments to original pushState', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    const state = { page: 'test' };
    const title = 'Test Title';
    const url = '/test-url';

    history.pushState(state, title, url);

    // The navigation should have worked (we can't easily verify state, but URL can be checked)
    // The callback was called
    expect(callback).toHaveBeenCalled();

    cleanup();
  });

  it('handles popstate event', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    // Simulate popstate (browser back/forward)
    window.dispatchEvent(new PopStateEvent('popstate'));

    expect(callback).toHaveBeenCalledTimes(1);

    cleanup();
  });

  it('removes popstate listener on cleanup', () => {
    const callback = vi.fn();
    const cleanup = onPageChange(callback);

    cleanup();

    // After cleanup, popstate should not trigger callback
    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(callback).not.toHaveBeenCalled();
  });
});
