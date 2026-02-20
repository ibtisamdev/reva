/**
 * Root Widget component.
 * Manages open/close state, applies theme customization,
 * and handles cart recovery popup polling.
 */

import type { JSX } from 'preact';
import { useCallback, useEffect, useState } from 'preact/hooks';

import type { RecoveryCheckResponse, WidgetConfig } from '../types';
import { checkRecovery, isApiError } from '../lib/api';
import { getThemeVariables } from '../lib/config';
import { getSessionId } from '../lib/session';
import { ChatWindow } from './ChatWindow';
import { RecoveryPopup } from './RecoveryPopup';
import { ToggleButton } from './ToggleButton';

const RECOVERY_POLL_INTERVAL = 60_000; // 60 seconds
const RECOVERY_DISMISS_KEY = 'reva_recovery_dismissed';
const DISMISS_DURATION_MS = 24 * 60 * 60 * 1000; // 24 hours

interface WidgetProps {
  config: WidgetConfig;
}

export function Widget({ config }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [recoveryData, setRecoveryData] = useState<RecoveryCheckResponse | null>(null);
  const [showRecoveryPopup, setShowRecoveryPopup] = useState(false);

  const apiUrl = config.apiUrl || 'http://localhost:8000';

  // Check if recovery popup was recently dismissed
  const isDismissed = useCallback((): boolean => {
    try {
      const dismissedAt = localStorage.getItem(`${RECOVERY_DISMISS_KEY}_${config.storeId}`);
      if (!dismissedAt) return false;
      return Date.now() - parseInt(dismissedAt, 10) < DISMISS_DURATION_MS;
    } catch {
      return false;
    }
  }, [config.storeId]);

  // Poll for recovery data
  useEffect(() => {
    if (!config.storeId) return;

    const pollRecovery = async () => {
      if (isDismissed()) return;

      const sessionId = getSessionId();
      const result = await checkRecovery(apiUrl, config.storeId, sessionId);

      if (!isApiError(result) && result.has_recovery && result.checkout_url) {
        setRecoveryData(result);
        setShowRecoveryPopup(true);
      } else {
        setRecoveryData(null);
        setShowRecoveryPopup(false);
      }
    };

    // Initial check after a short delay
    const initialTimeout = setTimeout(pollRecovery, 5000);

    // Periodic polling
    const interval = setInterval(pollRecovery, RECOVERY_POLL_INTERVAL);

    return () => {
      clearTimeout(initialTimeout);
      clearInterval(interval);
    };
  }, [config.storeId, apiUrl, isDismissed]);

  const handleDismissRecovery = () => {
    setShowRecoveryPopup(false);
    try {
      localStorage.setItem(
        `${RECOVERY_DISMISS_KEY}_${config.storeId}`,
        String(Date.now())
      );
    } catch {
      // Ignore localStorage errors
    }
  };

  // Compute theme CSS variables from config
  // This allows store owners to customize the primary color
  const themeStyle: JSX.CSSProperties = getThemeVariables(config.theme?.primaryColor);

  return (
    <div className="reva-widget" style={themeStyle}>
      {isOpen && (
        <ChatWindow
          storeId={config.storeId}
          apiUrl={config.apiUrl}
          onClose={() => setIsOpen(false)}
        />
      )}
      {showRecoveryPopup && recoveryData && !isOpen && (
        <RecoveryPopup
          items={recoveryData.items}
          checkoutUrl={recoveryData.checkout_url!}
          totalPrice={recoveryData.total_price || '0.00'}
          onDismiss={handleDismissRecovery}
          onRecover={handleDismissRecovery}
        />
      )}
      <ToggleButton isOpen={isOpen} onClick={() => setIsOpen(!isOpen)} />
    </div>
  );
}
