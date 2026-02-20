/**
 * Recovery popup component for abandoned cart recovery.
 * Slides up from the toggle button to show abandoned cart items.
 */

import type { RecoveryItem } from '../types';

interface RecoveryPopupProps {
  items: RecoveryItem[];
  checkoutUrl: string;
  totalPrice: string;
  onDismiss: () => void;
  onRecover: () => void;
}

export function RecoveryPopup({
  items,
  checkoutUrl,
  totalPrice,
  onDismiss,
  onRecover,
}: RecoveryPopupProps) {
  const displayItems = items.slice(0, 3);

  const handleRecover = () => {
    onRecover();
    // Add UTM params
    const separator = checkoutUrl.includes('?') ? '&' : '?';
    const url = `${checkoutUrl}${separator}utm_source=reva&utm_medium=widget&utm_campaign=cart_recovery&utm_content=popup`;
    window.open(url, '_blank');
  };

  return (
    <div className="reva-recovery-popup">
      <div className="reva-recovery-header">
        <span className="reva-recovery-title">You left items in your cart</span>
        <button
          className="reva-recovery-close"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          &times;
        </button>
      </div>

      <div className="reva-recovery-items">
        {displayItems.map((item, i) => (
          <div key={i} className="reva-recovery-item">
            {item.image_url && (
              <img
                className="reva-recovery-item-image"
                src={item.image_url}
                alt={item.title}
                loading="lazy"
              />
            )}
            <div className="reva-recovery-item-details">
              <span className="reva-recovery-item-title">{item.title}</span>
              <span className="reva-recovery-item-meta">
                Qty: {item.quantity} &middot; ${item.price}
              </span>
            </div>
          </div>
        ))}
        {items.length > 3 && (
          <div className="reva-recovery-more">
            +{items.length - 3} more item{items.length - 3 > 1 ? 's' : ''}
          </div>
        )}
      </div>

      <div className="reva-recovery-total">
        <span>Total</span>
        <span className="reva-recovery-total-price">${totalPrice}</span>
      </div>

      <button className="reva-recovery-cta" onClick={handleRecover}>
        Complete Your Purchase
      </button>

      <button className="reva-recovery-dismiss" onClick={onDismiss}>
        Maybe Later
      </button>
    </div>
  );
}
