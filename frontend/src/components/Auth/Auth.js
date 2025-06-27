import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost, handleApiError } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Auth.css';

const Auth = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        password2: '',
        email: '',
        first_name: '',
        last_name: ''
    });
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
        
        // Clear field-specific error when user starts typing
        if (fieldErrors[e.target.name]) {
            setFieldErrors({
                ...fieldErrors,
                [e.target.name]: null
            });
        }
    };

    const parseErrorResponse = (errorResponse) => {
        console.log('Error response:', errorResponse); // For debugging
        
        // Clear previous errors
        setError('');
        setFieldErrors({});
        
        if (!errorResponse) {
            setError('An unexpected error occurred. Please try again.');
            return;
        }

        // Handle different error response formats
        if (errorResponse.error_summary && Array.isArray(errorResponse.error_summary)) {
            // Use the user-friendly error summary
            setError(errorResponse.error_summary.join(' '));
        } else if (errorResponse.message) {
            // Use the main error message
            setError(errorResponse.message);
        }

        // Set field-specific errors if available
        if (errorResponse.errors && typeof errorResponse.errors === 'object') {
            const newFieldErrors = {};
            Object.keys(errorResponse.errors).forEach(field => {
                if (Array.isArray(errorResponse.errors[field])) {
                    newFieldErrors[field] = errorResponse.errors[field].join(', ');
                } else {
                    newFieldErrors[field] = errorResponse.errors[field];
                }
            });
            setFieldErrors(newFieldErrors);
        }

        // Fallback: if no specific message, create a generic one
        if (!errorResponse.message && !errorResponse.error_summary) {
            setError('Please check your input and try again.');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setFieldErrors({});
        setSuccess('');
        setLoading(true);

        // Clear any existing token before login attempt
        if (isLogin) {
            localStorage.removeItem('token');
        }

        try {
            const endpoint = isLogin ? '/api/auth/login/' : '/api/auth/register/';
            const response = await apiPost(endpoint, formData);
            
            if (isLogin) {
                // Store the token in localStorage
                localStorage.setItem('token', response.token.access);
                setSuccess('Login successful! Redirecting...');
                
                // Check if user is admin and redirect accordingly
                if (response.is_admin) {
                    setTimeout(() => navigate('/admin'), 1000);
                } else {
                    setTimeout(() => navigate('/dashboard'), 1000);
                }
            } else {
                setSuccess('Registration successful! Please login.');
                setIsLogin(true);
                // Clear form data after successful registration
                setFormData({
                    username: '',
                    password: '',
                    password2: '',
                    email: '',
                    first_name: '',
                    last_name: ''
                });
            }
        } catch (err) {
            console.error('Auth error:', err); // For debugging
            const errorMessage = handleApiError(err);
            
            // Try to parse the detailed error response
            if (err.response?.data) {
                parseErrorResponse(err.response.data);
            } else {
                setError(errorMessage);
            }
        } finally {
            setLoading(false);
        }
    };

    const getFieldError = (fieldName) => {
        return fieldErrors[fieldName];
    };

    const hasFieldError = (fieldName) => {
        return !!fieldErrors[fieldName];
    };

    return (
        <div className="auth-container">
            {/* Background Elements */}
            <div className="auth-background">
                <div className="oxford-pattern"></div>
                <div className="floating-elements">
                    <div className="floating-element"></div>
                    <div className="floating-element"></div>
                    <div className="floating-element"></div>
                </div>
            </div>

            {/* Main Content */}
            <div className="auth-content">
                {/* Brand Header */}
                <div className="brand-header">
                    <div className="oxford-logo">
                        <div className="logo-shield">
                            <div className="shield-inner">
                                <span className="logo-text">Oxford</span>
                            </div>
                        </div>
                    </div>
                    <h1 className="brand-title">Welcome to Oxford Mock Trading</h1>
                    <p className="brand-subtitle">
                        Advanced Market Simulation Platform for MBA Students
                    </p>
                </div>

                {/* Auth Card */}
                <div className="auth-card">
                    <div className="auth-header">
                        <h2>{isLogin ? 'Sign In to Your Account' : 'Create Your Account'}</h2>
                        <p>{isLogin ? 'Enter your credentials to access the trading platform' : 'Join the Oxford Mock Trading community'}</p>
                    </div>

                    {error && <div className="error-message">{error}</div>}
                    {success && <div className="success-message">{success}</div>}

                    <form onSubmit={handleSubmit} className="auth-form">
                        <div className="form-group">
                            <label htmlFor="username">
                                <span className="label-icon">👤</span>
                                Username
                            </label>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                required
                                className={hasFieldError('username') ? 'error' : ''}
                                placeholder="Enter your username"
                            />
                            {hasFieldError('username') && (
                                <span className="field-error">{getFieldError('username')}</span>
                            )}
                        </div>

                        {!isLogin && (
                            <>
                                <div className="form-group">
                                    <label htmlFor="email">
                                        <span className="label-icon">📧</span>
                                        Email Address
                                    </label>
                                    <input
                                        type="email"
                                        id="email"
                                        name="email"
                                        value={formData.email}
                                        onChange={handleChange}
                                        className={hasFieldError('email') ? 'error' : ''}
                                        placeholder="your.email@example.com"
                                    />
                                    {hasFieldError('email') && (
                                        <span className="field-error">{getFieldError('email')}</span>
                                    )}
                                </div>
                                
                                <div className="form-row">
                                    <div className="form-group">
                                        <label htmlFor="first_name">
                                            <span className="label-icon">✏️</span>
                                            First Name
                                        </label>
                                        <input
                                            type="text"
                                            id="first_name"
                                            name="first_name"
                                            value={formData.first_name}
                                            onChange={handleChange}
                                            className={hasFieldError('first_name') ? 'error' : ''}
                                            placeholder="First name"
                                        />
                                        {hasFieldError('first_name') && (
                                            <span className="field-error">{getFieldError('first_name')}</span>
                                        )}
                                    </div>
                                    <div className="form-group">
                                        <label htmlFor="last_name">
                                            <span className="label-icon">✏️</span>
                                            Last Name
                                        </label>
                                        <input
                                            type="text"
                                            id="last_name"
                                            name="last_name"
                                            value={formData.last_name}
                                            onChange={handleChange}
                                            className={hasFieldError('last_name') ? 'error' : ''}
                                            placeholder="Last name"
                                        />
                                        {hasFieldError('last_name') && (
                                            <span className="field-error">{getFieldError('last_name')}</span>
                                        )}
                                    </div>
                                </div>
                            </>
                        )}

                        <div className="form-group">
                            <label htmlFor="password">
                                <span className="label-icon">🔒</span>
                                Password
                            </label>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                required
                                className={hasFieldError('password') ? 'error' : ''}
                                placeholder="Enter your password"
                            />
                            {hasFieldError('password') && (
                                <span className="field-error">{getFieldError('password')}</span>
                            )}
                        </div>

                        {!isLogin && (
                            <div className="form-group">
                                <label htmlFor="password2">
                                    <span className="label-icon">🔒</span>
                                    Confirm Password
                                </label>
                                <input
                                    type="password"
                                    id="password2"
                                    name="password2"
                                    value={formData.password2}
                                    onChange={handleChange}
                                    className={hasFieldError('password2') ? 'error' : ''}
                                    placeholder="Confirm your password"
                                />
                                {hasFieldError('password2') && (
                                    <span className="field-error">{getFieldError('password2')}</span>
                                )}
                            </div>
                        )}

                        <button 
                            type="submit" 
                            className="auth-button"
                            disabled={loading}
                        >
                            {loading ? (
                                <span className="button-loading">
                                    <span className="spinner"></span>
                                    {isLogin ? 'Signing In...' : 'Creating Account...'}
                                </span>
                            ) : (
                                <span>
                                    {isLogin ? '🚀 Sign In to Platform' : '🎓 Create Account'}
                                </span>
                            )}
                        </button>
                    </form>

                    <div className="auth-footer">
                        <p>
                            {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
                            <a onClick={() => setIsLogin(!isLogin)}>
                                {isLogin ? 'Create one here' : 'Sign in here'}
                            </a>
                        </p>
                        
                        {isLogin && (
                            <div className="additional-links">
                                <a href="#" className="link-secondary">Forgot your password?</a>
                                <span className="divider">|</span>
                                <a href="#" className="link-secondary">Need help?</a>
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer */}
                <div className="platform-footer">
                    <p>© 2024 Oxford Mock Trading Platform. Built for MBA Excellence.</p>
                    <div className="footer-links">
                        <a href="#">Privacy Policy</a>
                        <a href="#">Terms of Service</a>
                        <a href="#">Support</a>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Auth; 