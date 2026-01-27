/**
 * Reva Widget Entry Point
 * Initializes the chat widget and mounts it to the DOM.
 */

import { render } from 'preact';

import { Widget } from './components/Widget';
import { getConfig } from './lib/config';
import './styles.css';

// Types are now defined in src/types.ts and imported via lib/config.ts

/**
 * Initialize and mount the widget.
 */
function init() {
  const container = document.getElementById('reva-widget');
  if (!container) {
    console.error('Reva Widget: Container element #reva-widget not found');
    return;
  }

  const config = getConfig();

  // Warn if storeId is missing (widget won't work properly)
  if (!config.storeId) {
    console.error(
      'Reva Widget: storeId is required. Set window.RevaConfig = { storeId: "your-store-id" } before loading the widget.'
    );
  }

  render(<Widget config={config} />, container);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
