import { describe, expect, it } from 'vitest';

import { renderMarkdown } from '../markdown';

describe('renderMarkdown', () => {
  // --- Basic formatting ---
  it('renders bold text', () => {
    const result = renderMarkdown('**bold**');
    expect(result).toContain('<strong>bold</strong>');
  });

  it('renders italic text', () => {
    const result = renderMarkdown('*italic*');
    expect(result).toContain('<em>italic</em>');
  });

  it('renders inline code', () => {
    const result = renderMarkdown('use `console.log`');
    expect(result).toContain('<code>console.log</code>');
  });

  // --- Lists ---
  it('renders unordered lists', () => {
    const result = renderMarkdown('- Item 1\n- Item 2\n- Item 3');
    expect(result).toContain('<ul>');
    expect(result).toContain('<li>');
    expect(result).toContain('Item 1');
    expect(result).toContain('Item 2');
  });

  it('renders ordered lists', () => {
    const result = renderMarkdown('1. First\n2. Second');
    expect(result).toContain('<ol>');
    expect(result).toContain('<li>');
    expect(result).toContain('First');
  });

  // --- Links ---
  it('renders links with target="_blank" and rel="noopener noreferrer"', () => {
    const result = renderMarkdown('[Click here](https://example.com)');
    expect(result).toContain('href="https://example.com"');
    expect(result).toContain('target="_blank"');
    expect(result).toContain('rel="noopener noreferrer"');
  });

  // --- Images ---
  it('renders images with src and alt', () => {
    const result = renderMarkdown('![Product](https://cdn.example.com/image.jpg)');
    expect(result).toContain('<img');
    expect(result).toContain('src="https://cdn.example.com/image.jpg"');
    expect(result).toContain('alt="Product"');
  });

  it('adds loading="lazy" to images', () => {
    const result = renderMarkdown('![Alt](https://cdn.example.com/img.jpg)');
    expect(result).toContain('loading="lazy"');
  });

  // --- Headings ---
  it('downgrades h1 to h3', () => {
    const result = renderMarkdown('# Big Heading');
    expect(result).toContain('<h3');
    expect(result).not.toContain('<h1');
  });

  it('downgrades h2 to h3', () => {
    const result = renderMarkdown('## Medium Heading');
    expect(result).toContain('<h3');
    expect(result).not.toContain('<h2');
  });

  it('keeps h3 as h3', () => {
    const result = renderMarkdown('### Subheading');
    expect(result).toContain('<h3');
  });

  // --- Line breaks ---
  it('converts newlines to br tags', () => {
    const result = renderMarkdown('Line 1\nLine 2');
    expect(result).toContain('<br');
  });

  // --- Code blocks ---
  it('renders fenced code blocks', () => {
    const result = renderMarkdown('```\nconst x = 1;\n```');
    expect(result).toContain('<pre>');
    expect(result).toContain('<code>');
  });

  // --- XSS prevention ---
  it('strips script tags', () => {
    const result = renderMarkdown('<script>alert("xss")</script>');
    expect(result).not.toContain('<script');
    expect(result).not.toContain('alert');
  });

  it('strips onclick attributes', () => {
    const result = renderMarkdown('<a onclick="alert(1)" href="#">click</a>');
    expect(result).not.toContain('onclick');
  });

  it('strips javascript: URIs in links', () => {
    const result = renderMarkdown('[click](javascript:alert(1))');
    expect(result).not.toContain('javascript:');
  });

  it('strips onerror on images', () => {
    const result = renderMarkdown('<img src="x" onerror="alert(1)">');
    expect(result).not.toContain('onerror');
  });

  it('strips iframe tags', () => {
    const result = renderMarkdown('<iframe src="https://evil.com"></iframe>');
    expect(result).not.toContain('<iframe');
  });

  it('strips style tags', () => {
    const result = renderMarkdown('<style>body { display: none }</style>');
    expect(result).not.toContain('<style');
  });

  it('strips event handlers from allowed tags', () => {
    const result = renderMarkdown('<strong onmouseover="alert(1)">text</strong>');
    expect(result).toContain('<strong>text</strong>');
    expect(result).not.toContain('onmouseover');
  });

  // --- Edge cases ---
  it('returns empty string for empty input', () => {
    expect(renderMarkdown('')).toBe('');
  });

  it('handles plain text without markdown', () => {
    const result = renderMarkdown('Just a plain message');
    expect(result).toContain('Just a plain message');
  });

  it('handles unclosed bold gracefully', () => {
    const result = renderMarkdown('**incomplete bold');
    expect(result).toBeTruthy();
    expect(result).toContain('incomplete bold');
  });

  it('handles unclosed link gracefully', () => {
    const result = renderMarkdown('[link text](https://example');
    expect(result).toBeTruthy();
  });

  it('handles unclosed code block gracefully', () => {
    const result = renderMarkdown('```\npartial code block');
    expect(result).toBeTruthy();
    expect(result).toContain('partial code block');
  });
});
