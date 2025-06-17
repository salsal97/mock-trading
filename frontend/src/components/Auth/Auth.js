import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../../config/api';
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

        try {
            const endpoint = isLogin ? '/api/auth/login/' : '/api/auth/register/';
            const response = await axios.post(`${API_BASE_URL}${endpoint}`, formData);
            
            if (isLogin) {
                // Store the token in localStorage
                localStorage.setItem('token', response.data.token.access);
                setSuccess('Login successful! Redirecting...');
                
                // Check if user is admin and redirect accordingly
                if (response.data.is_admin) {
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
            
            if (err.response?.data) {
                parseErrorResponse(err.response.data);
            } else if (err.response?.status === 500) {
                setError('Server error. Please try again later.');
            } else if (err.code === 'NETWORK_ERROR' || !err.response) {
                setError('Network error. Please check your connection and try again.');
            } else {
                setError('An unexpected error occurred. Please try again.');
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
            <div className="auth-card">
                <div className="auth-header">
                    <h1>{isLogin ? 'Welcome Back' : 'Create Account'}</h1>
                    <p>{isLogin ? 'Please login to your account' : 'Sign up to get started'}</p>
                </div>

                {error && <div className="error-message">{error}</div>}
                {success && <div className="success-message">{success}</div>}

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            required
                            className={hasFieldError('username') ? 'error' : ''}
                        />
                        {hasFieldError('username') && (
                            <span className="field-error">{getFieldError('username')}</span>
                        )}
                    </div>

                    {!isLogin && (
                        <>
                            <div className="form-group">
                                <label htmlFor="email">Email</label>
                                <input
                                    type="email"
                                    id="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    className={hasFieldError('email') ? 'error' : ''}
                                />
                                {hasFieldError('email') && (
                                    <span className="field-error">{getFieldError('email')}</span>
                                )}
                            </div>
                            <div className="form-group">
                                <label htmlFor="first_name">First Name</label>
                                <input
                                    type="text"
                                    id="first_name"
                                    name="first_name"
                                    value={formData.first_name}
                                    onChange={handleChange}
                                    className={hasFieldError('first_name') ? 'error' : ''}
                                />
                                {hasFieldError('first_name') && (
                                    <span className="field-error">{getFieldError('first_name')}</span>
                                )}
                            </div>
                            <div className="form-group">
                                <label htmlFor="last_name">Last Name</label>
                                <input
                                    type="text"
                                    id="last_name"
                                    name="last_name"
                                    value={formData.last_name}
                                    onChange={handleChange}
                                    className={hasFieldError('last_name') ? 'error' : ''}
                                />
                                {hasFieldError('last_name') && (
                                    <span className="field-error">{getFieldError('last_name')}</span>
                                )}
                            </div>
                        </>
                    )}

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            className={hasFieldError('password') ? 'error' : ''}
                        />
                        {hasFieldError('password') && (
                            <span className="field-error">{getFieldError('password')}</span>
                        )}
                    </div>

                    {!isLogin && (
                        <div className="form-group">
                            <label htmlFor="password2">Confirm Password</label>
                            <input
                                type="password"
                                id="password2"
                                name="password2"
                                value={formData.password2}
                                onChange={handleChange}
                                required
                                className={hasFieldError('password2') ? 'error' : ''}
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
                        {loading ? 'Processing...' : isLogin ? 'Login' : 'Register'}
                    </button>
                </form>

                <div className="auth-footer">
                    {isLogin ? (
                        <p>
                            Don't have an account?{' '}
                            <a href="#" onClick={(e) => {
                                e.preventDefault();
                                setIsLogin(false);
                                setError('');
                                setFieldErrors({});
                                setSuccess('');
                            }}>
                                Register here
                            </a>
                        </p>
                    ) : (
                        <p>
                            Already have an account?{' '}
                            <a href="#" onClick={(e) => {
                                e.preventDefault();
                                setIsLogin(true);
                                setError('');
                                setFieldErrors({});
                                setSuccess('');
                            }}>
                                Login here
                            </a>
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Auth; 