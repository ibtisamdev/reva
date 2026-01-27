/**
 * Root Widget component.
 * Manages open/close state and applies theme customization.
 */

import type { JSX } from 'preact';
import { useState } from 'preact/hooks';

import type { WidgetConfig } from '../types';
import { getThemeVariables } from '../lib/config';
import { ChatWindow } from './ChatWindow';
import { ToggleButton } from './ToggleButton';

interface WidgetProps {
  config: WidgetConfig;
}

export function Widget({ config }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);

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
      <ToggleButton isOpen={isOpen} onClick={() => setIsOpen(!isOpen)} />
    </div>
  );
}
