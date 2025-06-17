/**
 * Market utility functions for status handling and market operations
 */

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
 * @returns {string} Color hex code
 */
export const getStatusColor = (status) => {
    const colors = {
        [MARKET_STATUS.CREATED]: '#6c757d',
        [MARKET_STATUS.OPEN]: '#28a745',
        [MARKET_STATUS.CLOSED]: '#ffc107',
        [MARKET_STATUS.SETTLED]: '#17a2b8'
    };
    return colors[status] || '#6c757d';
};

/**
 * Get text for market status
 * @param {string} status - Market status
 * @returns {string} Human readable status text
 */
export const getStatusText = (status) => {
    const texts = {
        [MARKET_STATUS.CREATED]: 'Created',
        [MARKET_STATUS.OPEN]: 'Open for Trading',
        [MARKET_STATUS.CLOSED]: 'Trading Closed',
        [MARKET_STATUS.SETTLED]: 'Settled'
    };
    return texts[status] || 'Unknown';
};

/**
 * Get CSS class for status badge
 * @param {string} status - Market status
 * @returns {string} CSS class name
 */
export const getStatusBadgeClass = (status) => {
    const classes = {
        [MARKET_STATUS.CREATED]: 'status-badge status-created',
        [MARKET_STATUS.OPEN]: 'status-badge status-open',
        [MARKET_STATUS.CLOSED]: 'status-badge status-closed',
        [MARKET_STATUS.SETTLED]: 'status-badge status-settled'
    };
    return classes[status] || 'status-badge';
};

/**
 * Get CSS class for trade position
 * @param {string} position - Trade position ('LONG' or 'SHORT')
 * @returns {string} CSS class name
 */
export const getPositionClass = (position) => {
    return position === 'LONG' ? 'position-long' : 'position-short';
};

/**
 * Check if auto-activate button should be shown for a market
 * @param {Object} market - Market object
 * @returns {boolean} Whether to show auto-activate button
 */
export const shouldShowAutoActivateButton = (market) => {
    if (!market) return false;
    return market.status === MARKET_STATUS.CREATED && 
           market.spread_bidding_close && 
           new Date(market.spread_bidding_close) <= new Date();
};

/**
 * Get trade status text based on market and user's trade
 * @param {Object} market - Market object
 * @returns {string} Trade status text
 */
export const getTradeStatusText = (market) => {
    if (!market) return 'No trade';
    
    if (market.user_trade) {
        const position = market.user_trade.position === 'LONG' ? 'Long' : 'Short';
        const price = market.user_trade.price;
        const quantity = market.user_trade.quantity;
        return `${position} ${quantity} at ${price}`;
    }
    
    if (market.status === MARKET_STATUS.OPEN) {
        return 'No position';
    }
    
    return 'Trading closed';
};

/**
 * Check if market is in a specific phase
 * @param {object} market - Market object
 * @param {string} phase - Phase to check ('bidding', 'trading', 'closed', 'settled')
 * @returns {boolean} True if in specified phase
 */
export const isMarketInPhase = (market, phase) => {
    const now = new Date();
    
    switch (phase) {
        case 'bidding':
            return market.status === MARKET_STATUS.CREATED && market.is_spread_bidding_active;
        case 'trading':
            return market.status === MARKET_STATUS.OPEN && market.is_trading_active;
        case 'closed':
            return market.status === MARKET_STATUS.CLOSED;
        case 'settled':
            return market.status === MARKET_STATUS.SETTLED;
        default:
            return false;
    }
};

/**
 * Get market phase display text
 * @param {object} market - Market object
 * @returns {string} Current phase description
 */
export const getMarketPhase = (market) => {
    if (isMarketInPhase(market, 'bidding')) return 'Spread Bidding Active';
    if (isMarketInPhase(market, 'trading')) return 'Trading Active';
    if (isMarketInPhase(market, 'closed')) return 'Trading Closed';
    if (isMarketInPhase(market, 'settled')) return 'Market Settled';
    return 'Market Created';
};

/**
 * Format market premise for display (truncate if too long)
 * @param {string} premise - Market premise
 * @param {number} maxLength - Maximum length (default 50)
 * @returns {string} Formatted premise
 */
export const formatMarketPremise = (premise, maxLength = 50) => {
    if (!premise) return '';
    if (premise.length <= maxLength) return premise;
    return premise.substring(0, maxLength) + '...';
};

/**
 * Calculate total trading volume for a market
 * @param {object} market - Market object
 * @returns {number} Total trading volume
 */
export const getTotalTradingVolume = (market) => {
    return (market.long_trades_count || 0) + (market.short_trades_count || 0);
};

/**
 * Get trading sentiment (more longs vs shorts)
 * @param {object} market - Market object
 * @returns {object} Sentiment analysis
 */
export const getTradingSentiment = (market) => {
    const longCount = market.long_trades_count || 0;
    const shortCount = market.short_trades_count || 0;
    const total = longCount + shortCount;
    
    if (total === 0) {
        return { sentiment: 'neutral', percentage: 0, description: 'No trades yet' };
    }
    
    const longPercentage = (longCount / total) * 100;
    
    if (longPercentage > 60) {
        return { sentiment: 'bullish', percentage: longPercentage, description: 'Mostly long positions' };
    } else if (longPercentage < 40) {
        return { sentiment: 'bearish', percentage: 100 - longPercentage, description: 'Mostly short positions' };
    } else {
        return { sentiment: 'neutral', percentage: 50, description: 'Balanced trading' };
    }
}; 