import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Product } from '@/lib/api/types';

import { ProductList } from '../product-list';

const mockProducts: Product[] = [
  {
    id: 'prod-1',
    platform_product_id: '1001',
    title: 'Test Widget',
    description: 'A test product',
    handle: 'test-widget',
    vendor: 'Acme',
    product_type: 'gadget',
    status: 'active',
    tags: ['test'],
    variants: [{ title: 'Default', price: '29.99', sku: 'TW-001', inventory_quantity: 10 }],
    images: [{ src: 'https://cdn.example.com/widget.jpg', alt: 'Widget photo', position: 1 }],
    synced_at: '2024-01-15T00:00:00Z',
    created_at: '2024-01-10T00:00:00Z',
  },
  {
    id: 'prod-2',
    platform_product_id: '1002',
    title: 'Plain Product',
    description: null,
    handle: 'plain-product',
    vendor: null,
    product_type: null,
    status: 'draft',
    tags: [],
    variants: [{ title: 'Default', price: '9.99', sku: null, inventory_quantity: null }],
    images: [],
    synced_at: null,
    created_at: '2024-01-11T00:00:00Z',
  },
];

describe('ProductList', () => {
  it('shows empty state when no products', () => {
    render(<ProductList products={[]} />);
    expect(screen.getByText('No products synced')).toBeInTheDocument();
    expect(screen.getByText(/connect your shopify store/i)).toBeInTheDocument();
  });

  it('renders product titles, prices, vendors, and status badges', () => {
    render(<ProductList products={mockProducts} />);
    expect(screen.getByText('Test Widget')).toBeInTheDocument();
    expect(screen.getByText('$29.99')).toBeInTheDocument();
    expect(screen.getByText('Acme')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
    expect(screen.getByText('Plain Product')).toBeInTheDocument();
    expect(screen.getByText('$9.99')).toBeInTheDocument();
    expect(screen.getByText('draft')).toBeInTheDocument();
  });

  it('shows "Edit in Shopify" links when shopDomain is provided', () => {
    render(<ProductList products={mockProducts} shopDomain="test.myshopify.com" />);
    const links = screen.getAllByText('Edit in Shopify');
    expect(links).toHaveLength(2);
    expect(links[0].closest('a')).toHaveAttribute(
      'href',
      'https://test.myshopify.com/admin/products/1001'
    );
  });

  it('does not show "Edit in Shopify" links when shopDomain is not provided', () => {
    render(<ProductList products={mockProducts} />);
    expect(screen.queryByText('Edit in Shopify')).not.toBeInTheDocument();
  });
});
