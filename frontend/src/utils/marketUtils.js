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
  const isCreatedOrPending = status === 'created' || status === 'pending';
  
  // Check if there's at least one bid from a non-admin user
  const hasBid = market.best_spread_bid && market.best_spread_bid.user !== market.created_by_username;
  
  return isCreatedOrPending && hasBid;
};

/**
 * Get display text for trade status
 * @param {string} status - Trade status
 * @returns {string} - Display text
 */
export const getTradeStatusText = (market) => {
  if (!market.is_trading_active) return 'Trading Closed';
  if (market.user_trade) {
    return `${market.user_trade.position} Position (${market.user_trade.quantity} units @ $${market.user_trade.price})`;
  }
  return 'No Position';
};

export const getProfitLossClass = (profitLoss) => {
  if (profitLoss > 0) return 'profit';
  if (profitLoss < 0) return 'loss';
  return 'neutral';
}; 