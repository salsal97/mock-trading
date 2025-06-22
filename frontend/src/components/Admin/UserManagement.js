import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Admin.css';
import './UserManagement.css';

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            setLoading(true);
            setError('');
            const response = await apiGet('/api/auth/admin/users/');
            setUsers(response);
        } catch (error) {
            console.error('Error fetching users:', error);
            if (shouldRedirectToLogin(error)) {
                navigate('/auth');
                return;
            }
            setError('Failed to load users');
        } finally {
            setLoading(false);
        }
    };

    const handleUserAction = async (userId, action) => {
        try {
            setError('');
            setSuccess('');
            await apiPost(`/api/auth/admin/users/${userId}/verify/`, { action });
            
            if (action === 'verify') {
                setSuccess('User verified successfully');
            } else if (action === 'reject') {
                setSuccess('User rejected successfully');
            }
            
            // Refresh users list
            fetchUsers();
        } catch (error) {
            console.error('Error updating user:', error);
            setError(handleApiError(error));
        }
    };

    const formatDate = (dateString) => {
        if (!dateString || dateString === 'Never') return 'Never';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="admin-page">
                <div className="loading-spinner">Loading users...</div>
            </div>
        );
    }

    return (
        <div className="admin-page">
            <div className="admin-header">
                <h1>User Management</h1>
                <div className="admin-actions">
                    <button onClick={() => navigate('/admin')} className="btn btn-secondary">
                        Back to Dashboard
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}
            {success && <div className="success-message">{success}</div>}

            <div className="users-table-container">
                <table className="users-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Verified</th>
                            <th>Date Joined</th>
                            <th>Last Login</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(user => (
                            <tr key={user.id}>
                                <td>{user.id}</td>
                                <td>{user.username}</td>
                                <td>{user.email}</td>
                                <td>{user.first_name} {user.last_name}</td>
                                <td>
                                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                                        {user.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                    {user.is_staff && <span className="status-badge staff">Staff</span>}
                                    {user.is_superuser && <span className="status-badge admin">Admin</span>}
                                </td>
                                <td>
                                    <span className={`status-badge ${user.is_verified ? 'verified' : 'unverified'}`}>
                                        {user.is_verified ? 'Verified' : 'Unverified'}
                                    </span>
                                    {user.is_verified && user.verified_by && (
                                        <div className="verification-info">
                                            by {user.verified_by} on {formatDate(user.verification_date)}
                                        </div>
                                    )}
                                </td>
                                <td>{formatDate(user.date_joined)}</td>
                                <td>{formatDate(user.last_login)}</td>
                                <td>
                                    {!user.is_verified && !user.is_superuser && (
                                        <div className="action-buttons">
                                            <button
                                                onClick={() => handleUserAction(user.id, 'verify')}
                                                className="btn btn-sm btn-success"
                                            >
                                                Verify
                                            </button>
                                            <button
                                                onClick={() => handleUserAction(user.id, 'reject')}
                                                className="btn btn-sm btn-danger"
                                            >
                                                Reject
                                            </button>
                                        </div>
                                    )}
                                    {user.is_verified && (
                                        <span className="text-muted">Verified</span>
                                    )}
                                    {user.is_superuser && (
                                        <span className="text-muted">Admin</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {users.length === 0 && (
                <div className="empty-state">
                    <p>No users found.</p>
                </div>
            )}
        </div>
    );
};

export default UserManagement; 