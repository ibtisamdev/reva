import type { JSX } from 'preact';
import { useState } from 'preact/hooks';

import { ChatWindow } from './ChatWindow';
import { ToggleButton } from './ToggleButton';

interface WidgetConfig {
  organizationId: string;
  primaryColor?: string;
  position?: 'left' | 'right';
}

interface WidgetProps {
  config: WidgetConfig;
}

export function Widget({ config }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);

  const style: JSX.CSSProperties | undefined = config.primaryColor
    ? { '--reva-primary': config.primaryColor }
    : undefined;

  return (
    <div className="reva-widget" style={style}>
      {isOpen && (
        <ChatWindow
          organizationId={config.organizationId}
          onClose={() => setIsOpen(false)}
        />
      )}
      <ToggleButton isOpen={isOpen} onClick={() => setIsOpen(!isOpen)} />
    </div>
  );
}
