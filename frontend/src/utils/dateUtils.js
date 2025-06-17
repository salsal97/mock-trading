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
    const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return localDate.toISOString().slice(0, 16);
}; 