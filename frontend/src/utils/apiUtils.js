/**
 * API utility functions for consistent API handling across the application
 */
import axios from 'axios';
import API_BASE_URL from '../config/api';

/**
 * Get authentication headers with current token
 * @returns {object} Headers object with Authorization
 */
export const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * Handle API errors consistently
 * @param {Error} error - The error object from axios
 * @returns {string} User-friendly error message
 */
export const handleApiError = (error) => {
    console.error('API Error:', error);

    if (error.response?.data?.errors) {
        const errorData = error.response.data.errors;
        if (typeof errorData === 'object') {
            return Object.values(errorData).flat().join('. ');
        }
        return errorData;
    }

    if (error.response?.data?.error) {
        return error.response.data.error;
    }

    if (error.response?.data?.message) {
        return error.response.data.message;
    }

    // Django REST Framework returns validation errors directly by field name.
    if (error.response?.status === 400 && error.response.data && typeof error.response.data === 'object') {
        const messages = Object.values(error.response.data).flat().filter(value => typeof value === 'string');
        if (messages.length) return messages.join('. ');
    }

    if (error.response?.status === 401) {
        return 'Unauthorized. Please log in again.';
    }

    if (error.response?.status === 403) {
        return 'Access denied. Insufficient permissions.';
    }

    if (error.response?.status === 404) {
        return 'Resource not found.';
    }

    if (error.response?.status === 500) {
        return 'Server error. Please try again later.';
    }

    if (error.code === 'NETWORK_ERROR' || !error.response) {
        return 'Network error. Please check your connection and try again.';
    }

    return 'An unexpected error occurred. Please try again.';
};

/**
 * Check if user should be redirected to login based on error
 * @param {Error} error - The error object from axios
 * @returns {boolean} True if should redirect to login
 */
export const shouldRedirectToLogin = (error) => {
    return error.response?.status === 401;
};

/**
 * Generic API request wrapper with error handling
 * @param {string} method - HTTP method
 * @param {string} url - API endpoint
 * @param {object} data - Request data
 * @param {object} options - Additional options
 * @returns {Promise} API response
 */
export const apiRequest = async (method, url, data = null, options = {}) => {
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/register');
    const config = {
        method,
        url: `${API_BASE_URL}${url}`,
        headers: { ...(isAuthEndpoint ? {} : getAuthHeaders()), ...options.headers },
        ...options
    };
    if (data && ['post', 'put', 'patch'].includes(method.toLowerCase())) config.data = data;
    const response = await axios(config);
    return response.data;
};

/**
 * GET request wrapper
 * @param {string} url - API endpoint
 * @param {object} options - Additional options
 * @returns {Promise} API response
 */
export const apiGet = (url, options = {}) => {
    return apiRequest('GET', url, null, options);
};

/**
 * POST request wrapper
 * @param {string} url - API endpoint
 * @param {object} data - Request data
 * @param {object} options - Additional options
 * @returns {Promise} API response
 */
export const apiPost = (url, data, options = {}) => {
    return apiRequest('POST', url, data, options);
};
