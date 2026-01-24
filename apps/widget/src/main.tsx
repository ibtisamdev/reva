import { render } from 'preact';
import { Widget } from './components/Widget';
import './styles.css';

// Configuration from embed script
declare global {
  interface Window {
    RevaWidgetConfig?: {
      organizationId: string;
      primaryColor?: string;
      position?: 'left' | 'right';
    };
  }
}

function init() {
  const container = document.getElementById('reva-widget');
  if (!container) {
    console.error('Reva Widget: Container element #reva-widget not found');
    return;
  }

  const config = window.RevaWidgetConfig || {
    organizationId: 'demo',
  };

  render(<Widget config={config} />, container);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
