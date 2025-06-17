// Form validation utilities

/**
 * Validates market timing constraints
 * @param {string} activationTime - ISO datetime string
 * @param {string} closingTime - ISO datetime string
 * @returns {object} - { isValid: boolean, error: string }
 */
export const validateMarketTiming = (activationTime, closingTime) => {
  if (!activationTime || !closingTime) {
    return { isValid: false, error: 'Both activation and closing times are required' };
  }

  const activation = new Date(activationTime);
  const closing = new Date(closingTime);
  const now = new Date();

  // Check if activation time is in the future
  if (activation <= now) {
    return { isValid: false, error: 'Activation time must be in the future' };
  }

  // Check if closing time is after activation time
  if (closing <= activation) {
    return { isValid: false, error: 'Closing time must be after activation time' };
  }

  // Check minimum duration (e.g., at least 1 hour)
  const minDuration = 60 * 60 * 1000; // 1 hour in milliseconds
  if (closing.getTime() - activation.getTime() < minDuration) {
    return { isValid: false, error: 'Market must be active for at least 1 hour' };
  }

  return { isValid: true, error: '' };
};

/**
 * Gets the minimum datetime for input fields (current time + 1 hour)
 * @returns {string} - ISO datetime string for datetime-local input
 */
export const getMinDateTime = () => {
  const now = new Date();
  now.setHours(now.getHours() + 1);
  return now.toISOString().slice(0, 16);
}; 