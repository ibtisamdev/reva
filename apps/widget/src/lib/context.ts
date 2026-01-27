/**
 * Page context detection for contextual AI responses.
 * Detects current page URL, title, and product information.
 */

import type { PageContext } from '../types';

/**
 * Extract product handle from Shopify-style product URLs.
 * Handles URLs like:
 * - /products/my-product
 * - /products/my-product?variant=123
 * - /collections/all/products/my-product
 */
function extractProductHandle(url: string): string | undefined {
  // Match /products/{handle} pattern
  const match = url.match(/\/products\/([^/?#]+)/);
  return match?.[1];
}

/**
 * Get the current page context for sending with chat messages.
 * This helps the AI provide more relevant, contextual responses.
 */
export function getPageContext(): PageContext {
  const url = window.location.href;
  const productHandle = extractProductHandle(url);

  return {
    page_url: url,
    page_title: document.title,
    // In Shopify, the URL uses the product handle, not numeric ID
    // The handle serves as a human-readable identifier
    product_handle: productHandle,
    // If we need the numeric product ID, it would need to come from
    // Shopify's Liquid template or the page's meta tags
    product_id: productHandle,
  };
}

/**
 * Listen for page navigation changes (SPA support).
 * Calls the callback when the URL changes.
 * Returns a cleanup function to stop listening.
 */
export function onPageChange(callback: () => void): () => void {
  // Handle browser back/forward navigation
  const handlePopState = () => callback();
  window.addEventListener('popstate', handlePopState);

  // Intercept pushState and replaceState for SPA navigation
  const originalPushState = history.pushState.bind(history);
  const originalReplaceState = history.replaceState.bind(history);

  history.pushState = function (...args) {
    originalPushState(...args);
    callback();
  };

  history.replaceState = function (...args) {
    originalReplaceState(...args);
    callback();
  };

  // Return cleanup function
  return () => {
    window.removeEventListener('popstate', handlePopState);
    history.pushState = originalPushState;
    history.replaceState = originalReplaceState;
  };
}
