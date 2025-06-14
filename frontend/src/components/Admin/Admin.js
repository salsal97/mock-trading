import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Admin.css';

const Admin = () => {
    const [users, setUsers] = useState([]);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        verifyAdminStatus();
        fetchUsers();
    }, []);

    const verifyAdminStatus = async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/');
            return;
        }

        try {
            // Since we don't have a specific verify-admin endpoint,
            // we'll use the get-all-users endpoint to verify admin status
            const response = await axios.get('http://localhost:8000/api/auth/admin/users/', {
                headers: { Authorization: `Bearer ${token}` }
            });
            // If we get here, the user is an admin
        } catch (error) {
            console.error('Error verifying admin status:', error);
            setError('Error verifying admin status. Please try again.');
            if (error.response?.status === 403) {
                setTimeout(() => {
                    localStorage.removeItem('token');
                    navigate('/');
                }, 2000);
            }
        }
    };

    const fetchUsers = async () => {
        const token = localStorage.getItem('token');
        try {
            const response = await axios.get('http://localhost:8000/api/auth/admin/users/', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setUsers(response.data);
        } catch (error) {
            console.error('Error fetching users:', error);
            setError('Error fetching users. Please try again.');
        }
    };

    const handleVerification = async (userId, action) => {
        const token = localStorage.getItem('token');
        try {
            await axios.post(`http://localhost:8000/api/auth/admin/users/${userId}/verify/`, 
                { action: action === 'approve' ? 'verify' : 'reject' },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            fetchUsers();
        } catch (error) {
            console.error(`Error ${action}ing user:`, error);
            setError(`Error ${action}ing user. Please try again.`);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/');
    };

    return (
        <div className="admin-container">
            <div className="admin-header">
                <div className="left-section">
                    <button className="back-button" onClick={() => navigate('/admin')}>
                        ← Back to Admin Dashboard
                    </button>
                    <h1>User Management</h1>
                </div>
                <button className="logout-button" onClick={handleLogout}>
                    Logout
                </button>
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="users-list">
                {users.map(user => (
                    <div key={user.id} className="user-card">
                        <div className="user-info">
                            <h3>{user.username}</h3>
                            <p>Email: {user.email}</p>
                            <p>Status: {user.is_verified ? 'Verified' : 'Pending'}</p>
                            <p>Joined: {new Date(user.date_joined).toLocaleDateString()}</p>
                        </div>
                        {!user.is_verified && (
                            <div className="verification-actions">
                                <button 
                                    onClick={() => handleVerification(user.id, 'approve')}
                                    className="approve-button"
                                >
                                    Approve
                                </button>
                                <button 
                                    onClick={() => handleVerification(user.id, 'reject')}
                                    className="reject-button"
                                >
                                    Reject
                                </button>
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Admin; 