import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Admin.css';

const Admin = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/');
            return;
        }

        // Verify admin status
        verifyAdminStatus();
    }, [navigate]);

    const verifyAdminStatus = async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get('http://localhost:8000/api/auth/admin/users/', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            setIsAdmin(true);
            setUsers(response.data);
            setLoading(false);
        } catch (err) {
            console.error('Admin verification error:', err);
            if (err.response?.status === 403) {
                setError('Access denied. Admin privileges required.');
                // Clear token and redirect after a short delay
                setTimeout(() => {
                    localStorage.removeItem('token');
                    navigate('/');
                }, 2000);
            } else if (err.response?.status === 500) {
                setError('Server error. Please try again later.');
            } else {
                setError(err.response?.data?.error || 'Failed to verify admin status. Please try again.');
            }
            setLoading(false);
        }
    };

    const handleVerification = async (userId, action) => {
        try {
            const token = localStorage.getItem('token');
            await axios.post(
                `http://localhost:8000/api/auth/admin/users/${userId}/verify/`,
                { action },
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            );
            // Refresh the user list
            verifyAdminStatus();
        } catch (err) {
            console.error('Verification error:', err);
            if (err.response?.status === 403) {
                setError('Access denied. Admin privileges required.');
                setTimeout(() => {
                    localStorage.removeItem('token');
                    navigate('/');
                }, 2000);
            } else {
                setError(err.response?.data?.error || `Failed to ${action} user. Please try again.`);
            }
        }
    };

    if (loading) {
        return <div className="admin-container">Loading...</div>;
    }

    if (error) {
        return <div className="admin-container error">{error}</div>;
    }

    if (!isAdmin) {
        return <div className="admin-container error">Verifying admin status...</div>;
    }

    return (
        <div className="admin-container">
            <h1>User Management</h1>
            <div className="users-table">
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Verified</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(user => (
                            <tr key={user.id}>
                                <td>{user.username}</td>
                                <td>{user.email}</td>
                                <td>{`${user.first_name} ${user.last_name}`}</td>
                                <td>{user.is_active ? 'Active' : 'Inactive'}</td>
                                <td>{user.is_verified ? 'Yes' : 'No'}</td>
                                <td>
                                    {!user.is_verified && (
                                        <button
                                            onClick={() => handleVerification(user.id, 'verify')}
                                            className="verify-btn"
                                        >
                                            Verify
                                        </button>
                                    )}
                                    {user.is_verified && (
                                        <button
                                            onClick={() => handleVerification(user.id, 'reject')}
                                            className="reject-btn"
                                        >
                                            Reject
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Admin; 