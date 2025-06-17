import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import API_BASE_URL from '../../config/api';
import './MarketManagement.css';

const MarketManagement = () => {
    const [markets, setMarkets] = useState([]);
    const [stats, setStats] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [validationErrors, setValidationErrors] = useState({});
    const [activating, setActivating] = useState({});
    const [newMarket, setNewMarket] = useState({
        premise: '',
        unit_price: 1.0,
        initial_spread: '',
        spread_bidding_open: '',
        spread_bidding_close: '',
        trading_open: '',
        trading_close: ''
    });
    const navigate = useNavigate();

    useEffect(() => {
        verifyAdminAndFetchData();
    }, []);

    // Real-time validation as user types
    useEffect(() => {
        validateMarketTiming();
    }, [newMarket.spread_bidding_open, newMarket.spread_bidding_close, newMarket.trading_open, newMarket.trading_close]);

    const validateMarketTiming = () => {
        const errors = {};
        const { spread_bidding_open, spread_bidding_close, trading_open, trading_close } = newMarket;

        if (spread_bidding_open && spread_bidding_close) {
            if (new Date(spread_bidding_open) >= new Date(spread_bidding_close)) {
                errors.spread_bidding_close = 'Spread bidding close must be after spread bidding open';
            }
        }

        if (trading_open && trading_close) {
            if (new Date(trading_open) >= new Date(trading_close)) {
                errors.trading_close = 'Trading close must be after trading open';
            }
        }

        if (spread_bidding_close && trading_open) {
            if (new Date(spread_bidding_close) > new Date(trading_open)) {
                errors.trading_open = 'Trading open must be after spread bidding close';
            }
        }

        setValidationErrors(errors);
    };

    const getCurrentDateTime = () => {
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        return now.toISOString().slice(0, 16);
    };

    const getMinDateTime = (fieldName) => {
        const now = getCurrentDateTime();
        
        switch (fieldName) {
            case 'spread_bidding_open':
                return now;
            case 'spread_bidding_close':
                return newMarket.spread_bidding_open || now;
            case 'trading_open':
                return newMarket.spread_bidding_close || now;
            case 'trading_close':
                return newMarket.trading_open || now;
            default:
                return now;
        }
    };

    const verifyAdminAndFetchData = async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/login');
            return;
        }

        try {
            // Verify admin status and fetch data
            const [marketsResponse, statsResponse] = await Promise.all([
                axios.get(`${API_BASE_URL}/api/market/`, {
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get(`${API_BASE_URL}/api/market/stats/`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);

            setMarkets(marketsResponse.data);
            setStats(statsResponse.data);
            setError('');
        } catch (error) {
            console.error('Error fetching data:', error);
            if (error.response?.status === 403) {
                setError('Access denied. Admin privileges required.');
                setTimeout(() => navigate('/dashboard'), 2000);
            } else if (error.response?.status === 401) {
                navigate('/login');
            } else {
                setError('Error loading market data. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    const handleCreateMarket = async (e) => {
        e.preventDefault();
        
        // Check for validation errors
        if (Object.keys(validationErrors).length > 0) {
            setError('Please fix validation errors before submitting.');
            return;
        }

        const token = localStorage.getItem('token');
        try {
            await axios.post(`${API_BASE_URL}/api/market/`, newMarket, {
                headers: { Authorization: `Bearer ${token}` }
            });

            // Reset form and refresh data
            setNewMarket({
                premise: '',
                unit_price: 1.0,
                initial_spread: '',
                spread_bidding_open: '',
                spread_bidding_close: '',
                trading_open: '',
                trading_close: ''
            });
            setShowCreateForm(false);
            setError('');
            await verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error creating market:', error);
            if (error.response?.data) {
                const errorMessage = typeof error.response.data === 'object' 
                    ? Object.values(error.response.data).flat().join('. ')
                    : error.response.data;
                setError(`Error creating market: ${errorMessage}`);
            } else {
                setError('Error creating market. Please try again.');
            }
        }
    };

    const handleUpdateMarketStatus = async (marketId, newStatus) => {
        const token = localStorage.getItem('token');
        try {
            await axios.patch(`${API_BASE_URL}/api/market/${marketId}/`, 
                { status: newStatus },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            await verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error updating market status:', error);
            setError('Error updating market status. Please try again.');
        }
    };

    const handleManualActivate = async (marketId) => {
        const token = localStorage.getItem('token');
        setActivating(prev => ({ ...prev, [marketId]: true }));
        
        try {
            const response = await axios.post(
                `${API_BASE_URL}/api/market/${marketId}/manual_activate/`,
                {},
                { headers: { Authorization: `Bearer ${token}` } }
            );
            
            // Show success message with details
            const details = response.data.details;
            let message = 'Market activated successfully!';
            
            if (details.winning_bid) {
                message += `\nWinner: ${details.winning_bid.user} (spread: ${details.winning_bid.spread_low}-${details.winning_bid.spread_high})`;
            } else {
                message += '\nNo bids received - activated with initial spread';
            }
            
            alert(message);
            await verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error activating market:', error);
            if (error.response?.data) {
                const errorMessage = error.response.data.error || 'Unknown error';
                setError(`Error activating market: ${errorMessage}`);
            } else {
                setError('Error activating market. Please try again.');
            }
        } finally {
            setActivating(prev => ({ ...prev, [marketId]: false }));
        }
    };

    const handleSetFinalSpread = async (marketId) => {
        const spreadLow = prompt('Enter final spread low:');
        const spreadHigh = prompt('Enter final spread high:');
        
        if (spreadLow && spreadHigh) {
            const token = localStorage.getItem('token');
            try {
                await axios.patch(`${API_BASE_URL}/api/market/${marketId}/`, 
                    { 
                        final_spread_low: parseInt(spreadLow),
                        final_spread_high: parseInt(spreadHigh)
                    },
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                await verifyAdminAndFetchData();
            } catch (error) {
                console.error('Error setting final spread:', error);
                setError('Error setting final spread. Please try again.');
            }
        }
    };

    const handleDeleteMarket = async (marketId) => {
        if (window.confirm('Are you sure you want to delete this market?')) {
            const token = localStorage.getItem('token');
            try {
                            await axios.delete(`${API_BASE_URL}/api/market/${marketId}/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
                await verifyAdminAndFetchData();
            } catch (error) {
                console.error('Error deleting market:', error);
                setError('Error deleting market. Please try again.');
            }
        }
    };

    const formatDateTime = (dateString) => {
        return new Date(dateString).toLocaleString();
    };

    const getStatusBadgeClass = (status) => {
        switch (status) {
            case 'CREATED': return 'status-created';
            case 'OPEN': return 'status-open';
            case 'CLOSED': return 'status-closed';
            case 'SETTLED': return 'status-settled';
            default: return 'status-default';
        }
    };

    const shouldShowAutoActivateButton = (market) => {
        const now = new Date();
        const biddingClose = new Date(market.spread_bidding_close);
        return (
            market.status === 'CREATED' && 
            now > biddingClose && 
            market.final_spread_low === null && 
            market.final_spread_high === null
        );
    };

    if (loading) {
        return <div className="loading">Loading market management...</div>;
    }

    return (
        <div className="market-management">
            <div className="management-header">
                <h1>Market Management</h1>
                <button 
                    className="create-button"
                    onClick={() => setShowCreateForm(!showCreateForm)}
                >
                    {showCreateForm ? 'Cancel' : 'Create New Market'}
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            {/* Market Statistics */}
            {stats && (
                <div className="stats-section">
                    <h2>Market Statistics</h2>
                    <div className="stats-grid">
                        <div className="stat-card">
                            <h3>Total Markets</h3>
                            <p className="stat-number">{stats.total_markets}</p>
                        </div>
                        <div className="stat-card">
                            <h3>Active Trading</h3>
                            <p className="stat-number">{stats.active_trading}</p>
                        </div>
                        <div className="stat-card">
                            <h3>By Status</h3>
                            <div className="status-breakdown">
                                {Object.entries(stats.markets_by_status).map(([status, count]) => (
                                    <div key={status} className="status-item">
                                        <span className={`status-badge ${getStatusBadgeClass(status)}`}>
                                            {status}
                                        </span>
                                        <span className="status-count">{count}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Create Market Form */}
            {showCreateForm && (
                <div className="create-form-section">
                    <h2>Create New Market</h2>
                    <form onSubmit={handleCreateMarket} className="create-form">
                        <div className="form-group">
                            <label>Market Premise:</label>
                            <textarea
                                value={newMarket.premise}
                                onChange={(e) => setNewMarket({...newMarket, premise: e.target.value})}
                                placeholder="Enter the market question or premise..."
                                required
                                rows="3"
                            />
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Unit Price:</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={newMarket.unit_price}
                                    onChange={(e) => setNewMarket({...newMarket, unit_price: parseFloat(e.target.value)})}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Initial Spread:</label>
                                <input
                                    type="number"
                                    value={newMarket.initial_spread}
                                    onChange={(e) => setNewMarket({...newMarket, initial_spread: e.target.value})}
                                    placeholder="e.g., 10"
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Spread Bidding Open:</label>
                                <input
                                    type="datetime-local"
                                    value={newMarket.spread_bidding_open}
                                    min={getMinDateTime('spread_bidding_open')}
                                    onChange={(e) => setNewMarket({...newMarket, spread_bidding_open: e.target.value})}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Spread Bidding Close:</label>
                                <input
                                    type="datetime-local"
                                    value={newMarket.spread_bidding_close}
                                    min={getMinDateTime('spread_bidding_close')}
                                    onChange={(e) => setNewMarket({...newMarket, spread_bidding_close: e.target.value})}
                                    required
                                    className={validationErrors.spread_bidding_close ? 'error' : ''}
                                />
                                {validationErrors.spread_bidding_close && (
                                    <span className="validation-error">{validationErrors.spread_bidding_close}</span>
                                )}
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Trading Open:</label>
                                <input
                                    type="datetime-local"
                                    value={newMarket.trading_open}
                                    min={getMinDateTime('trading_open')}
                                    onChange={(e) => setNewMarket({...newMarket, trading_open: e.target.value})}
                                    required
                                    className={validationErrors.trading_open ? 'error' : ''}
                                />
                                {validationErrors.trading_open && (
                                    <span className="validation-error">{validationErrors.trading_open}</span>
                                )}
                            </div>
                            <div className="form-group">
                                <label>Trading Close:</label>
                                <input
                                    type="datetime-local"
                                    value={newMarket.trading_close}
                                    min={getMinDateTime('trading_close')}
                                    onChange={(e) => setNewMarket({...newMarket, trading_close: e.target.value})}
                                    required
                                    className={validationErrors.trading_close ? 'error' : ''}
                                />
                                {validationErrors.trading_close && (
                                    <span className="validation-error">{validationErrors.trading_close}</span>
                                )}
                            </div>
                        </div>

                        <div className="form-actions">
                            <button 
                                type="submit" 
                                className="submit-button"
                                disabled={Object.keys(validationErrors).length > 0}
                            >
                                Create Market
                            </button>
                            <button 
                                type="button" 
                                className="cancel-button"
                                onClick={() => setShowCreateForm(false)}
                            >
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Markets List */}
            <div className="markets-section">
                <h2>All Markets ({markets.length})</h2>
                <div className="markets-list">
                    {markets.map(market => (
                        <div key={market.id} className="market-card">
                            <div className="market-header">
                                <h3>{market.premise}</h3>
                                <span className={`status-badge ${getStatusBadgeClass(market.status)}`}>
                                    {market.status}
                                </span>
                            </div>
                            
                            <div className="market-details">
                                <div className="market-info">
                                    <span>Unit Price: ${market.unit_price}</span>
                                    <span>Current Spread: {market.current_spread_display}</span>
                                    <span>Created by: {market.created_by_username}</span>
                                </div>
                                
                                {/* Best Spread Bid Info */}
                                {market.best_spread_bid && (
                                    <div className="best-bid-info">
                                        <strong>Leading Bid:</strong> Width of {market.best_spread_bid.spread_width} by {market.best_spread_bid.user} 
                                        <span className="bid-time">
                                            ({formatDateTime(market.best_spread_bid.bid_time)})
                                        </span>
                                    </div>
                                )}
                                
                                {/* Auto-activation status */}
                                {shouldShowAutoActivateButton(market) && (
                                    <div className="auto-activate-notice">
                                        <strong>⚠️ Ready for Auto-Activation:</strong> Bidding window closed, market can be activated
                                    </div>
                                )}
                                
                                {/* Timing Information */}
                                <div className="market-timing">
                                    <span>Spread Bidding: {formatDateTime(market.spread_bidding_open)} - {formatDateTime(market.spread_bidding_close)}</span>
                                    <span>Trading: {formatDateTime(market.trading_open)} - {formatDateTime(market.trading_close)}</span>
                                </div>
                                
                                {/* Final Spread Display */}
                                {market.final_spread_low !== null && market.final_spread_high !== null && (
                                    <div className="final-spread-info">
                                        <strong>Final Spread:</strong> {market.final_spread_low} - {market.final_spread_high}
                                    </div>
                                )}
                            </div>
                            
                            <div className="market-actions">
                                {market.status === 'CREATED' && (
                                    <>
                                        {shouldShowAutoActivateButton(market) && (
                                            <button 
                                                onClick={() => handleManualActivate(market.id)}
                                                className="action-button activate-button"
                                                disabled={activating[market.id]}
                                            >
                                                {activating[market.id] ? 'Activating...' : 'Auto-Activate Market'}
                                            </button>
                                        )}
                                        <button 
                                            onClick={() => handleSetFinalSpread(market.id)}
                                            className="action-button spread-button"
                                        >
                                            Set Final Spread
                                        </button>
                                        <button 
                                            onClick={() => handleUpdateMarketStatus(market.id, 'OPEN')}
                                            className="action-button open-button"
                                        >
                                            Open Market
                                        </button>
                                        <button 
                                            onClick={() => handleDeleteMarket(market.id)}
                                            className="action-button delete-button"
                                        >
                                            Delete
                                        </button>
                                    </>
                                )}
                                
                                {market.status === 'OPEN' && (
                                    <button 
                                        onClick={() => handleUpdateMarketStatus(market.id, 'CLOSED')}
                                        className="action-button close-button"
                                    >
                                        Close Market
                                    </button>
                                )}
                                
                                {market.status === 'CLOSED' && (
                                    <button 
                                        onClick={() => handleUpdateMarketStatus(market.id, 'SETTLED')}
                                        className="action-button settle-button"
                                    >
                                        Settle Market
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default MarketManagement; 