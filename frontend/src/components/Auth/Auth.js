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

        if (fieldErrors[e.target.name]) {
            setFieldErrors({
                ...fieldErrors,
                [e.target.name]: null
            });
        }
    };

    const parseErrorResponse = (errorResponse) => {

        setError('');
        setFieldErrors({});
        
        if (!errorResponse) {
            setError('An unexpected error occurred. Please try again.');
            return;
        }

        if (errorResponse.error_summary && Array.isArray(errorResponse.error_summary)) {

            setError(errorResponse.error_summary.join(' '));
        } else if (errorResponse.message) {

            setError(errorResponse.message);
        }

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

        if (isLogin) {
            localStorage.removeItem('token');
        }

        try {
            const endpoint = isLogin ? '/api/auth/login/' : '/api/auth/register/';
            const response = await apiPost(endpoint, formData);
            
            if (isLogin) {

                localStorage.setItem('token', response.token.access);
                setSuccess('Login successful! Redirecting...');
                
                setTimeout(() => navigate('/dashboard'), 1000);
            } else {
                setSuccess('Registration successful! Please login.');
                setIsLogin(true);

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
            const errorMessage = handleApiError(err);

            if (err.response?.data) {
                parseErrorResponse(err.response.data);
            } else {
                setError(errorMessage);
            }
        } finally {
            setLoading(false);
        }
    };

    const field = (name, label, type = 'text', required = false, placeholder = '') => (
        <div className="form-group" key={name}>
            <label htmlFor={name}>{label}</label>
            <input id={name} name={name} type={type} value={formData[name]}
                onChange={handleChange} required={required} placeholder={placeholder}
                className={fieldErrors[name] ? 'error' : ''} />
            {fieldErrors[name] && <span className="field-error">{fieldErrors[name]}</span>}
        </div>
    );

    return (
        <div className="auth-container">
            <div className="auth-background">
                <div className="oxford-pattern"></div>
                <div className="floating-elements">
                    <div className="floating-element"></div>
                    <div className="floating-element"></div>
                    <div className="floating-element"></div>
                </div>
            </div>
            <div className="auth-content">
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
                        Market simulation for MBA students
                    </p>
                </div>
                <div className="auth-card">
                    <div className="auth-header">
                        <h2>{isLogin ? 'Sign In to Your Account' : 'Create Your Account'}</h2>
                        <p>{isLogin ? 'Enter your credentials to access the trading platform' : 'Join the Oxford Mock Trading community'}</p>
                    </div>

                    {error && <div className="error-message">{error}</div>}
                    {success && <div className="success-message">{success}</div>}

                    <form onSubmit={handleSubmit} className="auth-form" aria-label={isLogin ? 'Sign in' : 'Register'}>
                        {field('username', 'Username', 'text', true, 'Enter your username')}
                        {!isLogin && <>
                            {field('email', 'Email Address', 'email', false, 'your.email@example.com')}
                            <div className="form-row">
                                {field('first_name', 'First Name', 'text', false, 'First name')}
                                {field('last_name', 'Last Name', 'text', false, 'Last name')}
                            </div>
                        </>}
                        {field('password', 'Password', 'password', true, 'Enter your password')}
                        {!isLogin && field('password2', 'Confirm Password', 'password', false, 'Confirm your password')}

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
                                    {isLogin ? 'Sign In to Platform' : 'Create Account'}
                                </span>
                            )}
                        </button>
                    </form>

                    <div className="auth-footer">
                        <p>
                            {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
                            <button type="button" className="link-secondary" onClick={() => setIsLogin(!isLogin)}>
                                {isLogin ? 'Create one here' : 'Sign in here'}
                            </button>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Auth; 