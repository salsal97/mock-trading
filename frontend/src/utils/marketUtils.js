// Market-related utility functions and constants

// Market status constants
export const MARKET_STATUS = {
  CREATED: 'CREATED',
  OPEN: 'OPEN', 
  CLOSED: 'CLOSED',
  SETTLED: 'SETTLED'
};

/**
 * Get color for market status
 * @param {string} status - Market status
 * @returns {string} - Color code
 */
export const getStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case 'created':
    case 'pending':
      return '#f59e0b'; // amber
    case 'open':
    case 'active':
      return '#10b981'; // emerald
    case 'closed':
      return '#ef4444'; // red
    case 'settled':
      return '#6b7280'; // gray
    default:
      return '#6b7280'; // gray
  }
};

/**
 * Get display text for market status
 * @param {string} status - Market status
 * @returns {string} - Display text
 */
export const getStatusText = (status) => {
  switch (status?.toLowerCase()) {
    case 'created':
      return 'Created';
    case 'open':
    case 'active':
      return 'Active';
    case 'closed':
      return 'Closed';
    case 'settled':
      return 'Settled';
    default:
      return 'Unknown';
  }
};

/**
 * Get CSS class for status badge
 * @param {string} status - Market status
 * @returns {string} - CSS class name
 */
export const getStatusBadgeClass = (status) => {
  switch (status?.toLowerCase()) {
    case 'created':
    case 'pending':
      return 'status-badge status-pending';
    case 'open':
    case 'active':
      return 'status-badge status-active';
    case 'closed':
      return 'status-badge status-closed';
    case 'settled':
      return 'status-badge status-settled';
    default:
      return 'status-badge status-unknown';
  }
};

/**
 * Get CSS class for position display
 * @param {string} position - Trading position (LONG/SHORT)
 * @returns {string} - CSS class name
 */
export const getPositionClass = (position) => {
  switch (position?.toLowerCase()) {
    case 'long':
      return 'position-long';
    case 'short':
      return 'position-short';
    default:
      return 'position-neutral';
  }
};

/**
 * Determine if auto-activate button should be shown
 * @param {object} market - Market object
 * @returns {boolean} - Whether to show auto-activate button
 */
export const shouldShowAutoActivateButton = (market) => {
  if (!market) return false;
  
  const status = market.status?.toLowerCase();
  return status === 'created' || status === 'pending';
};

/**
 * Get display text for trade status
 * @param {string} status - Trade status
 * @returns {string} - Display text
 */
export const getTradeStatusText = (status) => {
  switch (status?.toLowerCase()) {
    case 'pending':
      return 'Pending';
    case 'filled':
      return 'Filled';
    case 'cancelled':
      return 'Cancelled';
    case 'expired':
      return 'Expired';
    default:
      return 'Unknown';
  }
}; 