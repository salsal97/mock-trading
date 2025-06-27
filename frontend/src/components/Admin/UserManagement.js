import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatCurrency } from '../../utils/dateUtils';
import { apiGet, apiPost, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Admin.css';
import './UserManagement.css';

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [balanceData, setBalanceData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [activeTab, setActiveTab] = useState('users'); // 'users' or 'balances'
    const [adjustBalanceForm, setAdjustBalanceForm] = useState({
        showForm: false,
        userId: null,
        username: '',
        action: 'adjust',
        amount: '',
        reason: ''
    });
    const navigate = useNavigate();

    useEffect(() => {
        fetchUsers();
        fetchBalanceData();
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

    const fetchBalanceData = async () => {
        try {
            const response = await apiGet('/api/auth/admin/user-balances/');
            setBalanceData(response);
        } catch (error) {
            console.error('Error fetching balance data:', error);
            if (shouldRedirectToLogin(error)) {
                navigate('/auth');
                return;
            }
            setError('Failed to load balance data');
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
            
            // Refresh users list and balance data
            fetchUsers();
            fetchBalanceData();
        } catch (error) {
            console.error('Error updating user:', error);
            setError(handleApiError(error));
        }
    };

    const handleBalanceAdjustment = async (e) => {
        e.preventDefault();
        
        try {
            setError('');
            setSuccess('');
            
            const response = await apiPost(`/api/auth/admin/users/${adjustBalanceForm.userId}/adjust-balance/`, {
                action: adjustBalanceForm.action,
                amount: parseFloat(adjustBalanceForm.amount),
                reason: adjustBalanceForm.reason
            });

            setSuccess(`Balance adjusted successfully for ${adjustBalanceForm.username}: ${formatCurrency(response.old_balance)} → ${formatCurrency(response.new_balance)}`);
            
            // Reset form
            setAdjustBalanceForm({
                showForm: false,
                userId: null,
                username: '',
                action: 'adjust',
                amount: '',
                reason: ''
            });
            
            // Refresh data
            fetchUsers();
            fetchBalanceData();
            
        } catch (error) {
            console.error('Error adjusting balance:', error);
            setError(handleApiError(error));
        }
    };

    const openBalanceAdjustment = (user) => {
        setAdjustBalanceForm({
            showForm: true,
            userId: user.id,
            username: user.username,
            action: 'adjust',
            amount: '',
            reason: ''
        });
    };

    const cancelBalanceAdjustment = () => {
        setAdjustBalanceForm({
            showForm: false,
            userId: null,
            username: '',
            action: 'adjust',
            amount: '',
            reason: ''
        });
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

            {/* Tab Navigation */}
            <div className="tab-navigation">
                <button 
                    className={`tab-button ${activeTab === 'users' ? 'active' : ''}`}
                    onClick={() => setActiveTab('users')}
                >
                    User Management
                </button>
                <button 
                    className={`tab-button ${activeTab === 'balances' ? 'active' : ''}`}
                    onClick={() => setActiveTab('balances')}
                >
                    Balance Management
                </button>
            </div>

            {/* User Management Tab */}
            {activeTab === 'users' && (
                <div className="users-table-container">
                    <table className="users-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Name</th>
                                <th>Balance</th>
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
                                    <td className={`balance ${user.balance < 0 ? 'negative' : 'positive'}`}>
                                        {formatCurrency(user.balance)}
                                    </td>
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
                                        <div className="action-buttons">
                                            {!user.is_verified && !user.is_superuser && (
                                                <>
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
                                                </>
                                            )}
                                            <button
                                                onClick={() => openBalanceAdjustment(user)}
                                                className="btn btn-sm btn-warning"
                                                title="Adjust Balance"
                                            >
                                                💰
                                            </button>
                                        </div>
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

                    {users.length === 0 && (
                        <div className="empty-state">
                            <p>No users found.</p>
                        </div>
                    )}
                </div>
            )}

            {/* Balance Management Tab */}
            {activeTab === 'balances' && balanceData && (
                <div className="balance-management">
                    {/* Summary Statistics */}
                    <div className="balance-summary">
                        <div className="summary-card">
                            <h3>Total Users</h3>
                            <div className="stat-value">{balanceData.total_users}</div>
                        </div>
                        <div className="summary-card">
                            <h3>Total Balance</h3>
                            <div className="stat-value">{formatCurrency(balanceData.total_balance)}</div>
                        </div>
                        <div className="summary-card">
                            <h3>Verified Users</h3>
                            <div className="stat-value">{balanceData.verified_users}</div>
                        </div>
                        <div className="summary-card">
                            <h3>Active Traders</h3>
                            <div className="stat-value">{balanceData.active_traders}</div>
                        </div>
                    </div>

                    {/* Detailed Balance Table */}
                    <div className="balance-table-container">
                        <table className="balance-table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Email</th>
                                    <th>Balance</th>
                                    <th>Total Trades</th>
                                    <th>Settled Trades</th>
                                    <th>Total P&L</th>
                                    <th>MM Markets</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {balanceData.users.map(user => (
                                    <tr key={user.user_id}>
                                        <td>{user.username}</td>
                                        <td>{user.email}</td>
                                        <td className={`balance ${user.balance < 0 ? 'negative' : 'positive'}`}>
                                            {formatCurrency(user.balance)}
                                        </td>
                                        <td>{user.total_trades}</td>
                                        <td>{user.settled_trades}</td>
                                        <td className={`pnl ${user.total_pnl >= 0 ? 'profit' : 'loss'}`}>
                                            {formatCurrency(user.total_pnl)}
                                        </td>
                                        <td>{user.market_maker_markets}</td>
                                        <td>
                                            <span className={`status-badge ${user.is_verified ? 'verified' : 'unverified'}`}>
                                                {user.is_verified ? 'Verified' : 'Unverified'}
                                            </span>
                                            {user.is_staff && <span className="status-badge staff">Staff</span>}
                                        </td>
                                        <td>
                                            <button
                                                onClick={() => openBalanceAdjustment({
                                                    id: user.user_id,
                                                    username: user.username
                                                })}
                                                className="btn btn-sm btn-warning"
                                            >
                                                Adjust Balance
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Balance Adjustment Modal */}
            {adjustBalanceForm.showForm && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <h3>Adjust Balance for {adjustBalanceForm.username}</h3>
                        <form onSubmit={handleBalanceAdjustment}>
                            <div className="form-group">
                                <label>Action:</label>
                                <select
                                    value={adjustBalanceForm.action}
                                    onChange={(e) => setAdjustBalanceForm({
                                        ...adjustBalanceForm,
                                        action: e.target.value
                                    })}
                                    required
                                >
                                    <option value="adjust">Adjust (Add/Subtract)</option>
                                    <option value="set">Set Absolute Value</option>
                                </select>
                            </div>

                            <div className="form-group">
                                <label>Amount:</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={adjustBalanceForm.amount}
                                    onChange={(e) => setAdjustBalanceForm({
                                        ...adjustBalanceForm,
                                        amount: e.target.value
                                    })}
                                    placeholder={adjustBalanceForm.action === 'adjust' ? 'Enter amount to add/subtract' : 'Enter new balance'}
                                    required
                                />
                                <small>
                                    {adjustBalanceForm.action === 'adjust' 
                                        ? 'Use negative values to subtract from balance'
                                        : 'Set the absolute balance value'
                                    }
                                </small>
                            </div>

                            <div className="form-group">
                                <label>Reason:</label>
                                <input
                                    type="text"
                                    value={adjustBalanceForm.reason}
                                    onChange={(e) => setAdjustBalanceForm({
                                        ...adjustBalanceForm,
                                        reason: e.target.value
                                    })}
                                    placeholder="Reason for adjustment"
                                    required
                                />
                            </div>

                            <div className="form-actions">
                                <button type="submit" className="btn btn-primary">
                                    Adjust Balance
                                </button>
                                <button 
                                    type="button" 
                                    onClick={cancelBalanceAdjustment}
                                    className="btn btn-secondary"
                                >
                                    Cancel
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UserManagement; 