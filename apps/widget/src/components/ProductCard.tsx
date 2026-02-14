/**
 * ProductCard component for the Reva Widget.
 * Displays a product with image, title, price, and stock status.
 * Links to the product page on the store when product_url is available.
 */

import type { Product } from '../types';

interface ProductCardProps {
  product: Product;
}

export function ProductCard({ product }: ProductCardProps) {
  const { title, price, image_url, in_stock, product_url } = product;

  const cardContent = (
    <>
      {image_url ? (
        <div className="reva-product-card-image">
          <img src={image_url} alt={title} loading="lazy" />
        </div>
      ) : (
        <div className="reva-product-card-image reva-product-card-placeholder">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
            <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
          </svg>
        </div>
      )}
      <div className="reva-product-card-info">
        <span className="reva-product-card-title">{title}</span>
        <div className="reva-product-card-meta">
          {price && <span className="reva-product-card-price">${price}</span>}
          {!in_stock && <span className="reva-product-card-badge">Out of stock</span>}
        </div>
      </div>
    </>
  );

  if (product_url) {
    return (
      <a
        className="reva-product-card reva-product-card-link"
        href={product_url}
        target="_blank"
        rel="noopener noreferrer"
      >
        {cardContent}
      </a>
    );
  }

  return <div className="reva-product-card">{cardContent}</div>;
}
