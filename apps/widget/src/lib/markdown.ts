/**
 * Markdown parsing and HTML sanitization for chat messages.
 * Uses marked for parsing and DOMPurify for XSS prevention.
 *
 * SECURITY: The widget runs in the host page DOM without iframe isolation.
 * All HTML output MUST be sanitized before rendering via dangerouslySetInnerHTML.
 */

import DOMPurify from 'dompurify';
import { Marked } from 'marked';

// Configure marked instance optimized for chat messages
const marked = new Marked({
  gfm: true, // GitHub Flavored Markdown (tables, strikethrough)
  breaks: true, // Convert \n to <br> (important for chat messages)
});

// DOMPurify: strict allowlist of safe tags and attributes
const PURIFY_CONFIG = {
  RETURN_TRUSTED_TYPE: false as const,
  ALLOWED_TAGS: [
    // Inline formatting
    'b',
    'i',
    'em',
    'strong',
    'code',
    'del',
    's',
    // Block elements
    'p',
    'br',
    'hr',
    // Headings (h3-h6 only; h1/h2 are downgraded before parsing)
    'h3',
    'h4',
    'h5',
    'h6',
    // Lists
    'ul',
    'ol',
    'li',
    // Links and images
    'a',
    'img',
    // Code blocks
    'pre',
  ],
  ALLOWED_ATTR: [
    'href',
    'target',
    'rel',
    'src',
    'alt',
    'title',
    'width',
    'height',
    'class',
    'loading',
  ],
  ALLOWED_URI_REGEXP: /^(?:(?:https?|data):)/i,
};

// Force links to open in new tab and images to lazy-load
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
  if (node.tagName === 'IMG') {
    node.setAttribute('loading', 'lazy');
  }
});

/**
 * Downgrade h1 and h2 to h3 — they're too large for a chat bubble.
 */
function downgradeHeadings(content: string): string {
  return content.replace(/^#{1,2}\s/gm, '### ');
}

/**
 * Parse markdown content to sanitized HTML for chat display.
 *
 * @param content - Raw markdown string from assistant response
 * @returns Sanitized HTML string safe for dangerouslySetInnerHTML
 */
export function renderMarkdown(content: string): string {
  if (!content) return '';

  const processed = downgradeHeadings(content);
  const rawHtml = marked.parse(processed) as string;
  return DOMPurify.sanitize(rawHtml, PURIFY_CONFIG);
}
