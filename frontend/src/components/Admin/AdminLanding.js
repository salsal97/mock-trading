import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './AdminLanding.css';

const AdminLanding = () => {
    const [stats, setStats] = useState({
        totalUsers: 0,
        totalTrades: 0,
        totalMarkets: 0,
        activeMarkets: 0
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const fetchAdminData = async () => {
            try {
                setLoading(true);
                setError('');
                
                const [usersResponse, marketsResponse, tradesResponse] = await Promise.all([
                    apiGet('/api/auth/admin/users/'),
                    apiGet('/api/market/'),
                    apiGet('/api/market/trades/')
                ]);

                setStats({
                    totalUsers: usersResponse.length || 0,
                    totalMarkets: marketsResponse.length || 0,
                    activeMarkets: marketsResponse.filter(market => market.status === 'active').length || 0,
                    totalTrades: tradesResponse.length || 0
                });
            } catch (error) {
                console.error('Error fetching admin data:', error);
                if (shouldRedirectToLogin(error)) {
                    navigate('/auth');
                    return;
                }
                handleApiError(error);
                setError('Failed to load admin data');
            } finally {
                setLoading(false);
            }
        };

        fetchAdminData();
    }, [navigate]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/auth');
    };

    if (loading) {
        return (
            <div className="admin-landing">
                <div className="loading-spinner">Loading admin dashboard...</div>
            </div>
        );
    }

    return (
        <div className="admin-landing">
            <div className="admin-header">
                <h1>Admin Dashboard</h1>
                <div className="admin-actions">
                    <button onClick={() => navigate('/dashboard')} className="btn btn-secondary">
                        User Dashboard
                    </button>
                    <button onClick={handleLogout} className="btn btn-outline">
                        Logout
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="stats-grid">
                <div className="stat-card">
                    <h3>Total Users</h3>
                    <div className="stat-number">{stats.totalUsers}</div>
                </div>
                <div className="stat-card">
                    <h3>Total Markets</h3>
                    <div className="stat-number">{stats.totalMarkets}</div>
                </div>
                <div className="stat-card">
                    <h3>Active Markets</h3>
                    <div className="stat-number">{stats.activeMarkets}</div>
                </div>
                <div className="stat-card">
                    <h3>Total Trades</h3>
                    <div className="stat-number">{stats.totalTrades}</div>
                </div>
            </div>

            <div className="admin-nav-grid">
                <div className="nav-card" onClick={() => navigate('/admin/markets')}>
                    <h3>Market Management</h3>
                    <p>Create, edit, and manage prediction markets</p>
                </div>
                <div className="nav-card" onClick={() => navigate('/admin/users')}>
                    <h3>User Management</h3>
                    <p>View and manage user accounts</p>
                </div>
            </div>
        </div>
    );
};

export default AdminLanding; 