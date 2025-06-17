/**
 * Form utility functions for validation and form handling
 */

/**
 * Validate market timing configuration
 * @param {Object} marketData - Market form data
 * @returns {Object} Validation errors object
 */
export const validateMarketTiming = (marketData) => {
    const errors = {};
    const now = new Date();

    const spreadBiddingOpen = new Date(marketData.spread_bidding_open);
    const spreadBiddingClose = new Date(marketData.spread_bidding_close);
    const tradingOpen = new Date(marketData.trading_open);
    const tradingClose = new Date(marketData.trading_close);

    if (spreadBiddingOpen <= now) {
        errors.spread_bidding_open = 'Spread bidding open must be in the future';
    }

    if (spreadBiddingClose <= spreadBiddingOpen) {
        errors.spread_bidding_close = 'Spread bidding close must be after spread bidding open';
    }

    if (tradingOpen <= spreadBiddingClose) {
        errors.trading_open = 'Trading open must be after spread bidding close';
    }

    if (tradingClose <= tradingOpen) {
        errors.trading_close = 'Trading close must be after trading open';
    }

    return errors;
};

/**
 * Get minimum datetime for form inputs (current time + 1 minute)
 * @returns {string} Minimum datetime string for input
 */
export const getMinDateTime = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 1);
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
};

/**
 * Reset form to initial state
 * @param {object} initialState - Initial form state
 * @param {function} setFormData - State setter function
 * @param {function} setErrors - Error setter function
 */
export const resetForm = (initialState, setFormData, setErrors = null) => {
    setFormData(initialState);
    if (setErrors) {
        setErrors({});
    }
};

/**
 * Handle form field changes with error clearing
 * @param {Event} event - Change event
 * @param {object} formData - Current form data
 * @param {function} setFormData - Form data setter
 * @param {object} fieldErrors - Current field errors
 * @param {function} setFieldErrors - Field errors setter
 */
export const handleFieldChange = (event, formData, setFormData, fieldErrors, setFieldErrors) => {
    const { name, value } = event.target;
    
    setFormData({
        ...formData,
        [name]: value
    });
    
    // Clear field-specific error when user starts typing
    if (fieldErrors[name]) {
        setFieldErrors({
            ...fieldErrors,
            [name]: null
        });
    }
};

/**
 * Validate required fields
 * @param {object} formData - Form data to validate
 * @param {array} requiredFields - Array of required field names
 * @returns {object} Validation errors object
 */
export const validateRequiredFields = (formData, requiredFields) => {
    const errors = {};
    
    requiredFields.forEach(field => {
        if (!formData[field] || formData[field].toString().trim() === '') {
            errors[field] = `${field.replace('_', ' ')} is required`;
        }
    });
    
    return errors;
};

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean} True if email is valid
 */
export const validateEmail = (email) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
};

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @returns {object} Validation result with isValid and message
 */
export const validatePassword = (password) => {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    if (password.length < minLength) {
        return { isValid: false, message: `Password must be at least ${minLength} characters long` };
    }
    
    if (!hasUpperCase) {
        return { isValid: false, message: 'Password must contain at least one uppercase letter' };
    }
    
    if (!hasLowerCase) {
        return { isValid: false, message: 'Password must contain at least one lowercase letter' };
    }
    
    if (!hasNumbers) {
        return { isValid: false, message: 'Password must contain at least one number' };
    }
    
    return { isValid: true, message: 'Password is strong' };
};

/**
 * Compare passwords for confirmation
 * @param {string} password - Original password
 * @param {string} confirmPassword - Confirmation password
 * @returns {boolean} True if passwords match
 */
export const validatePasswordConfirmation = (password, confirmPassword) => {
    return password === confirmPassword;
}; 