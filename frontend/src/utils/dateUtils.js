/**
 * Date utility functions for consistent date formatting across the application
 */

/**
 * Format date string to localized date and time
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
};

/**
 * Get current datetime in format suitable for datetime-local input
 * @returns {string} Current datetime in YYYY-MM-DDTHH:MM format
 */
export const getCurrentDateTimeLocal = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
};

/**
 * Convert UTC date string to local datetime-local format for form inputs
 * @param {string} dateString - UTC date string
 * @returns {string} Local datetime string for input
 */
export const formatForDateTimeInput = (dateString) => {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day}T${hours}:${minutes}`;
};

/**
 * Convert datetime-local input value to ISO string for API submission
 * @param {string} dateTimeLocalValue - Value from datetime-local input (YYYY-MM-DDTHH:MM)
 * @returns {string} ISO datetime string
 */
export const convertLocalDateTimeToISO = (dateTimeLocalValue) => {
    if (!dateTimeLocalValue) return '';
    
    // Create a Date object from the local datetime value
    // The browser treats datetime-local values as local time
    const date = new Date(dateTimeLocalValue);
    
    if (isNaN(date.getTime())) return '';
    
    // Return as ISO string (this will be in UTC)
    return date.toISOString();
};

/**
 * Convert market object with datetime-local values to API format
 * @param {object} market - Market object with datetime-local values
 * @returns {object} Market object with ISO datetime values
 */
export const convertMarketDatesToISO = (market) => {
    return {
        ...market,
        spread_bidding_open: convertLocalDateTimeToISO(market.spread_bidding_open),
        spread_bidding_close_trading_open: convertLocalDateTimeToISO(market.spread_bidding_close_trading_open),
        trading_close: convertLocalDateTimeToISO(market.trading_close)
    };
};

export const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}; 