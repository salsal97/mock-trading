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
                
                // Fetch data with error handling for individual endpoints
                const [usersResponse, marketsResponse] = await Promise.all([
                    apiGet('/api/auth/admin/users/'),
                    apiGet('/api/market/')
                ]);

                // Calculate trades count from market data (since global trades endpoint is not available)
                const tradesCount = marketsResponse.reduce((total, market) => 
                    total + (market.total_trades_count || 0), 0);

                setStats({
                    totalUsers: usersResponse.length || 0,
                    totalMarkets: marketsResponse.length || 0,
                    activeMarkets: marketsResponse.filter(market => 
                        market.status === 'CREATED' || market.status === 'ACTIVE' || 
                        market.is_spread_bidding_active || market.is_trading_active).length || 0,
                    totalTrades: tradesCount
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

            <div className="admin-cards">
                <div className="admin-card">
                    <div className="card-icon">👥</div>
                    <h2>User Management</h2>
                    <p>Manage user accounts and verification status</p>
                    <div className="stats-grid">
                        <div className="stat-item">
                            <span className="stat-number">{stats.totalUsers}</span>
                            <span className="stat-label">Total Users</span>
                        </div>
                    </div>
                    <button 
                        onClick={() => navigate('/admin/users')}
                        className="btn btn-primary"
                    >
                        Manage Users
                    </button>
                </div>

                <div className="admin-card">
                    <div className="card-icon">📊</div>
                    <h2>Market Management</h2>
                    <p>Create and manage prediction markets</p>
                    <div className="stats-grid">
                        <div className="stat-item">
                            <span className="stat-number">{stats.totalMarkets}</span>
                            <span className="stat-label">Total Markets</span>
                        </div>
                        <div className="stat-item">
                            <span className="stat-number">{stats.activeMarkets}</span>
                            <span className="stat-label">Active Markets</span>
                        </div>
                    </div>
                    <button 
                        onClick={() => navigate('/admin/markets')}
                        className="btn btn-primary"
                    >
                        Manage Markets
                    </button>
                </div>

                <div className="admin-card">
                    <div className="card-icon">⚖️</div>
                    <h2>Market Settlement</h2>
                    <p>Settle closed markets and distribute profits/losses</p>
                    <button 
                        onClick={() => navigate('/admin/settlement')}
                        className="btn btn-primary"
                    >
                        Settle Markets
                    </button>
                </div>

                <div className="admin-card">
                    <div className="card-icon">📈</div>
                    <h2>Trading Statistics</h2>
                    <p>Overview of trading activity and market performance</p>
                    <div className="stats-grid">
                        <div className="stat-item">
                            <span className="stat-number">{stats.totalTrades}</span>
                            <span className="stat-label">Total Trades</span>
                        </div>
                    </div>
                    <button 
                        onClick={() => navigate('/admin/analytics')}
                        className="btn btn-secondary"
                    >
                        View Analytics
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AdminLanding; 