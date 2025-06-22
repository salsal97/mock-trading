// Form validation utilities

/**
 * Validates market timing constraints
 * @param {object|string} marketOrActivationTime - Market object or activation time string
 * @param {string} closingTime - Closing time string (only used if first param is string)
 * @returns {object} - { isValid: boolean, error: string, errors: object }
 */
export const validateMarketTiming = (marketOrActivationTime, closingTime) => {
  // Handle both market object and individual parameters
  let market;
  if (typeof marketOrActivationTime === 'object') {
    market = marketOrActivationTime;
  } else {
    // Legacy support for individual parameters
    market = {
      spread_bidding_open: marketOrActivationTime,
      trading_close: closingTime
    };
  }

  const errors = {};
  const now = new Date();

  // Validate individual fields
  if (!market.spread_bidding_open) {
    errors.spread_bidding_open = 'Spread bidding open time is required';
  }
  if (!market.spread_bidding_close_trading_open) {
    errors.spread_bidding_close_trading_open = 'Spread bidding close & trading open time is required';
  }
  if (!market.trading_close) {
    errors.trading_close = 'Trading close time is required';
  }

  // If any required fields are missing, return early
  if (Object.keys(errors).length > 0) {
    return { isValid: false, error: 'All timing fields are required', errors };
  }

  const spreadBiddingOpen = new Date(market.spread_bidding_open);
  const spreadBiddingCloseTrading = new Date(market.spread_bidding_close_trading_open);
  const tradingClose = new Date(market.trading_close);

  // Check if spread bidding close & trading open is after spread bidding open
  if (spreadBiddingCloseTrading <= spreadBiddingOpen) {
    errors.spread_bidding_close_trading_open = 'Spread bidding close & trading open must be after spread bidding open';
  }

  // Check if trading close is after spread bidding close & trading open
  if (tradingClose <= spreadBiddingCloseTrading) {
    errors.trading_close = 'Trading close must be after spread bidding close & trading open';
  }

  // Check minimum durations
  const minSpreadBiddingDuration = 60 * 60 * 1000; // 1 hour
  if (spreadBiddingCloseTrading.getTime() - spreadBiddingOpen.getTime() < minSpreadBiddingDuration) {
    errors.spread_bidding_close_trading_open = 'Spread bidding must be open for at least 1 hour';
  }

  const minTradingDuration = 60 * 60 * 1000; // 1 hour
  if (tradingClose.getTime() - spreadBiddingCloseTrading.getTime() < minTradingDuration) {
    errors.trading_close = 'Trading must be open for at least 1 hour';
  }

  const isValid = Object.keys(errors).length === 0;
  const errorMessage = isValid ? '' : 'Please fix the timing validation errors';

  return { isValid, error: errorMessage, errors };
};

/**
 * Gets the minimum datetime for input fields based on field type and other field values
 * @param {string} fieldType - The type of field (spread_bidding_open, spread_bidding_close_trading_open, trading_close)
 * @param {object} market - The current market object with other field values
 * @returns {string} - ISO datetime string for datetime-local input
 */
export const getMinDateTime = (fieldType, market = {}) => {
  const now = new Date();
  
  switch (fieldType) {
    case 'spread_bidding_open':
      // Allow current time (server will validate)
      return now.toISOString().slice(0, 16);
    
    case 'spread_bidding_close_trading_open':
      if (market.spread_bidding_open) {
        const spreadOpen = new Date(market.spread_bidding_open);
        spreadOpen.setHours(spreadOpen.getHours() + 1); // Minimum 1 hour after open
        return spreadOpen.toISOString().slice(0, 16);
      }
      return now.toISOString().slice(0, 16);
    
    case 'trading_close':
      if (market.spread_bidding_close_trading_open) {
        const tradingOpen = new Date(market.spread_bidding_close_trading_open);
        tradingOpen.setHours(tradingOpen.getHours() + 1); // Minimum 1 hour after open
        return tradingOpen.toISOString().slice(0, 16);
      }
      return now.toISOString().slice(0, 16);
    
    default:
      return now.toISOString().slice(0, 16);
  }
}; 