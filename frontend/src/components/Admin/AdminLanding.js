import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../../config/api';
import './AdminLanding.css';

const AdminLanding = () => {
    const [stats, setStats] = useState({
        totalUsers: 0,
        verifiedUsers: 0,
        totalMarkets: 0,
        activeMarkets: 0,
        totalTrades: 0
    });
    const [markets, setMarkets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        fetchAdminData();
    }, []);

    const fetchAdminData = async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/');
            return;
        }

        try {
            const [usersResponse, marketsResponse] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/auth/admin/users/`, {
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get(`${API_BASE_URL}/api/market/`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);

            const users = usersResponse.data;
            const marketsData = marketsResponse.data;

            setStats({
                totalUsers: users.length,
                verifiedUsers: users.filter(u => u.is_verified).length,
                totalMarkets: marketsData.length,
                activeMarkets: marketsData.filter(m => m.status === 'OPEN').length,
                totalTrades: marketsData.reduce((sum, m) => sum + (m.total_trades_count || 0), 0)
            });

            setMarkets(marketsData);
            setError('');
        } catch (error) {
            console.error('Error fetching admin data:', error);
            setError('Error loading admin data. Please try again.');
            if (error.response?.status === 401 || error.response?.status === 403) {
                navigate('/');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/');
    };

    const handleViewTrades = (marketId, position = null) => {
        // In a real app, this would navigate to a detailed trades view
        // For now, we'll show an alert with the information
        const market = markets.find(m => m.id === marketId);
        if (market) {
            const message = position 
                ? `${position} trades for "${market.premise}": ${position === 'LONG' ? market.long_trades_count : market.short_trades_count} positions`
                : `All trades for "${market.premise}": ${market.total_trades_count} total positions`;
            alert(message);
        }
    };

    if (loading) {
        return <div className="admin-landing-container">Loading admin dashboard...</div>;
    }

    return (
        <div className="admin-landing-container">
            <div className="admin-header">
                <h1>Admin Dashboard</h1>
                <button className="logout-button" onClick={handleLogout}>
                    Logout
                </button>
            </div>
            
            {error && <div className="error-message">{error}</div>}
            
            {/* Statistics Overview */}
            <div className="stats-overview">
                <div className="stat-card">
                    <h3>Users</h3>
                    <div className="stat-number">{stats.totalUsers}</div>
                    <div className="stat-detail">({stats.verifiedUsers} verified)</div>
                </div>
                <div className="stat-card">
                    <h3>Markets</h3>
                    <div className="stat-number">{stats.totalMarkets}</div>
                    <div className="stat-detail">({stats.activeMarkets} active)</div>
                </div>
                <div className="stat-card">
                    <h3>Total Trades</h3>
                    <div className="stat-number">{stats.totalTrades}</div>
                    <div className="stat-detail">All positions</div>
                </div>
            </div>
            
            {/* Market Trade Statistics */}
            {markets.length > 0 && (
                <div className="market-trades-section">
                    <h2>Market Trading Activity</h2>
                    <div className="markets-trade-list">
                        {markets.map(market => (
                            <div key={market.id} className="market-trade-card">
                                <div className="market-trade-header">
                                    <h3>{market.premise}</h3>
                                    <span className={`status-badge ${market.status.toLowerCase()}`}>
                                        {market.status}
                                    </span>
                                </div>
                                <div className="trade-statistics">
                                    <div className="trade-stat-item">
                                        <span className="trade-label">Long Positions:</span>
                                        <button 
                                            className="trade-count-btn long"
                                            onClick={() => handleViewTrades(market.id, 'LONG')}
                                            disabled={market.long_trades_count === 0}
                                        >
                                            {market.long_trades_count || 0}
                                        </button>
                                    </div>
                                    <div className="trade-stat-item">
                                        <span className="trade-label">Short Positions:</span>
                                        <button 
                                            className="trade-count-btn short"
                                            onClick={() => handleViewTrades(market.id, 'SHORT')}
                                            disabled={market.short_trades_count === 0}
                                        >
                                            {market.short_trades_count || 0}
                                        </button>
                                    </div>
                                    <div className="trade-stat-item">
                                        <span className="trade-label">Total:</span>
                                        <button 
                                            className="trade-count-btn total"
                                            onClick={() => handleViewTrades(market.id)}
                                            disabled={market.total_trades_count === 0}
                                        >
                                            {market.total_trades_count || 0}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
            
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