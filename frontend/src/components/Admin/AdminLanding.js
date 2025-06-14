import React from 'react';
import { useNavigate } from 'react-router-dom';
import './AdminLanding.css';

const AdminLanding = () => {
    const navigate = useNavigate();

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/');
    };

    return (
        <div className="admin-landing-container">
            <div className="admin-header">
                <h1>Admin Dashboard</h1>
                <button className="logout-button" onClick={handleLogout}>
                    Logout
                </button>
            </div>
            <div className="admin-options">
                <button 
                    className="admin-option-button"
                    onClick={() => navigate('/admin/users')}
                >
                    <h2>User Management</h2>
                    <p>Manage user accounts, verify new users, and handle user-related tasks</p>
                </button>
                <button 
                    className="admin-option-button"
                    onClick={() => navigate('/admin/market')}
                >
                    <h2>Market Management</h2>
                    <p>Configure market settings, manage trading hours, and monitor market status</p>
                </button>
            </div>
        </div>
    );
};

export default AdminLanding; 