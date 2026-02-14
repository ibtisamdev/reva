import { render } from '@testing-library/preact';
import { describe, expect, it } from 'vitest';

import type { Product } from '../../types';
import { ProductCard } from '../ProductCard';

const baseProduct: Product = {
  product_id: 'prod-1',
  title: 'Stylish Summer Necklace',
  price: '44.99',
  image_url: 'https://cdn.example.com/necklace.jpg',
  in_stock: true,
  product_url: 'https://test-store.myshopify.com/products/stylish-summer-necklace',
};

describe('ProductCard', () => {
  it('renders title and price', () => {
    const { getByText } = render(<ProductCard product={baseProduct} />);
    expect(getByText('Stylish Summer Necklace')).toBeTruthy();
    expect(getByText('$44.99')).toBeTruthy();
  });

  it('renders image when provided', () => {
    const { container } = render(<ProductCard product={baseProduct} />);
    const img = container.querySelector('img');
    expect(img).toBeTruthy();
    expect(img?.getAttribute('src')).toBe('https://cdn.example.com/necklace.jpg');
    expect(img?.getAttribute('alt')).toBe('Stylish Summer Necklace');
  });

  it('shows placeholder when no image', () => {
    const product = { ...baseProduct, image_url: null };
    const { container } = render(<ProductCard product={product} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('.reva-product-card-placeholder')).toBeTruthy();
  });

  it('shows out of stock badge when not in stock', () => {
    const product = { ...baseProduct, in_stock: false };
    const { getByText } = render(<ProductCard product={product} />);
    expect(getByText('Out of stock')).toBeTruthy();
  });

  it('does not show out of stock badge when in stock', () => {
    const { queryByText } = render(<ProductCard product={baseProduct} />);
    expect(queryByText('Out of stock')).toBeNull();
  });

  it('handles null price', () => {
    const product = { ...baseProduct, price: null };
    const { queryByText } = render(<ProductCard product={product} />);
    expect(queryByText('$')).toBeNull();
  });

  it('renders as a link when product_url is provided', () => {
    const { container } = render(<ProductCard product={baseProduct} />);
    const link = container.querySelector('a.reva-product-card-link');
    expect(link).toBeTruthy();
    expect(link?.getAttribute('href')).toBe(
      'https://test-store.myshopify.com/products/stylish-summer-necklace',
    );
    expect(link?.getAttribute('target')).toBe('_blank');
    expect(link?.getAttribute('rel')).toBe('noopener noreferrer');
  });

  it('renders as a div when product_url is null', () => {
    const product = { ...baseProduct, product_url: null };
    const { container } = render(<ProductCard product={product} />);
    expect(container.querySelector('a')).toBeNull();
    expect(container.querySelector('div.reva-product-card')).toBeTruthy();
  });
});
