import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './MarketManagement.css';

const MarketManagement = () => {
    const [markets, setMarkets] = useState([]);
    const [stats, setStats] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [validationErrors, setValidationErrors] = useState({});
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
            navigate('/');
            return;
        }

        try {
            // Fetch markets and stats in parallel
            const [marketsResponse, statsResponse] = await Promise.all([
                axios.get('http://localhost:8000/api/market/', {
                    headers: { Authorization: `Bearer ${token}` }
                }),
                axios.get('http://localhost:8000/api/market/stats/', {
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);

            setMarkets(marketsResponse.data);
            setStats(statsResponse.data);
            setLoading(false);
        } catch (error) {
            console.error('Error fetching data:', error);
            if (error.response?.status === 403) {
                setError('Access denied. Admin privileges required.');
                setTimeout(() => {
                    localStorage.removeItem('token');
                    navigate('/');
                }, 2000);
            } else {
                setError('Error loading market data. Please try again.');
            }
            setLoading(false);
        }
    };

    const handleCreateMarket = async (e) => {
        e.preventDefault();
        
        // Final validation before submission
        if (Object.keys(validationErrors).length > 0) {
            setError('Please fix the validation errors before submitting.');
            return;
        }

        const token = localStorage.getItem('token');

        try {
            await axios.post('http://localhost:8000/api/market/', newMarket, {
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
            setValidationErrors({});
            setShowCreateForm(false);
            setError(''); // Clear any previous errors
            verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error creating market:', error);
            if (error.response?.data) {
                // Display backend validation errors
                const backendErrors = error.response.data;
                if (typeof backendErrors === 'object') {
                    const errorMessages = Object.values(backendErrors).flat().join('. ');
                    setError(`Validation error: ${errorMessages}`);
                } else {
                    setError('Error creating market. Please check your input and try again.');
                }
            } else {
                setError('Error creating market. Please check your input and try again.');
            }
        }
    };

    const handleUpdateMarketStatus = async (marketId, newStatus) => {
        const token = localStorage.getItem('token');

        try {
            await axios.patch(`http://localhost:8000/api/market/${marketId}/`, 
                { status: newStatus },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error updating market status:', error);
            setError('Error updating market status. Please try again.');
        }
    };

    const handleSettleMarket = async (marketId, outcome) => {
        const token = localStorage.getItem('token');

        try {
            await axios.post(`http://localhost:8000/api/market/${marketId}/settle/`, 
                { outcome: parseInt(outcome) },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error settling market:', error);
            setError('Error settling market. Please try again.');
        }
    };

    const handleSetFinalSpread = async (marketId) => {
        const spreadLow = prompt('Enter final spread low value:');
        const spreadHigh = prompt('Enter final spread high value:');
        
        if (spreadLow === null || spreadHigh === null) return;
        
        const token = localStorage.getItem('token');

        try {
            await axios.patch(`http://localhost:8000/api/market/${marketId}/`, 
                { 
                    final_spread_low: parseInt(spreadLow),
                    final_spread_high: parseInt(spreadHigh)
                },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error setting final spread:', error);
            setError('Error setting final spread. Please try again.');
        }
    };

    const handleDeleteMarket = async (marketId) => {
        if (!window.confirm('Are you sure you want to delete this market?')) {
            return;
        }

        const token = localStorage.getItem('token');

        try {
            await axios.delete(`http://localhost:8000/api/market/${marketId}/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error deleting market:', error);
            setError('Error deleting market. Please try again.');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/');
    };

    const formatDateTime = (dateString) => {
        return new Date(dateString).toLocaleString();
    };

    const getStatusColor = (status) => {
        const colors = {
            'CREATED': '#6c757d',
            'OPEN': '#28a745',
            'CLOSED': '#ffc107',
            'SETTLED': '#17a2b8'
        };
        return colors[status] || '#6c757d';
    };

    if (loading) {
        return <div className="market-management-container">Loading...</div>;
    }

    return (
        <div className="market-management-container">
            <div className="market-header">
                <div className="header-left">
                    <button className="back-button" onClick={() => navigate('/admin')}>
                        ← Back to Admin Dashboard
                    </button>
                    <h1>Market Management</h1>
                </div>
                <div className="header-right">
                    <button 
                        className="create-button"
                        onClick={() => setShowCreateForm(!showCreateForm)}
                    >
                        {showCreateForm ? 'Cancel' : 'Create New Market'}
                    </button>
                    <button className="logout-button" onClick={handleLogout}>
                        Logout
                    </button>
                </div>
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
                        {Object.entries(stats.markets_by_status).map(([status, count]) => (
                            <div key={status} className="stat-card">
                                <h3>{status}</h3>
                                <p className="stat-number">{count}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Create Market Form */}
            {showCreateForm && (
                <div className="create-form-section">
                    <h2>Create New Market</h2>
                    <form onSubmit={handleCreateMarket} className="create-form">
                        <div className="form-row">
                            <div className="form-group">
                                <label>Market Premise:</label>
                                <textarea
                                    value={newMarket.premise}
                                    onChange={(e) => setNewMarket({...newMarket, premise: e.target.value})}
                                    required
                                    placeholder="e.g., Will Bitcoin reach $100k by end of year?"
                                />
                            </div>
                        </div>
                        
                        <div className="form-row">
                            <div className="form-group">
                                <label>Unit Price:</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    value={newMarket.unit_price}
                                    onChange={(e) => setNewMarket({...newMarket, unit_price: parseFloat(e.target.value)})}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Initial Spread:</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={newMarket.initial_spread}
                                    onChange={(e) => setNewMarket({...newMarket, initial_spread: parseInt(e.target.value)})}
                                    required
                                    placeholder="Starting spread value"
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

                        <button 
                            type="submit" 
                            className="submit-button"
                            disabled={Object.keys(validationErrors).length > 0}
                        >
                            Create Market
                        </button>
                    </form>
                </div>
            )}

            {/* Markets List */}
            <div className="markets-section">
                <h2>All Markets ({markets.length})</h2>
                <div className="markets-list">
                    {markets.map(market => (
                        <div key={market.id} className="market-card">
                            <div className="market-header-info">
                                <h3>{market.premise}</h3>
                                <span 
                                    className="status-badge"
                                    style={{ backgroundColor: getStatusColor(market.status) }}
                                >
                                    {market.status}
                                </span>
                            </div>
                            
                            <div className="market-details">
                                <div className="detail-row">
                                    <span>Unit Price: ${market.unit_price}</span>
                                    <span>Spread: {market.current_spread_display}</span>
                                </div>
                                <div className="detail-row">
                                    <span>Created by: {market.created_by_username}</span>
                                    <span>Created: {formatDateTime(market.created_at)}</span>
                                </div>
                                <div className="detail-row">
                                    <span>Spread Bidding: {formatDateTime(market.spread_bidding_open)} - {formatDateTime(market.spread_bidding_close)}</span>
                                </div>
                                <div className="detail-row">
                                    <span>Trading: {formatDateTime(market.trading_open)} - {formatDateTime(market.trading_close)}</span>
                                </div>
                                {market.outcome !== null && (
                                    <div className="detail-row">
                                        <span><strong>Outcome: {market.outcome}</strong></span>
                                    </div>
                                )}
                            </div>

                            <div className="market-actions">
                                {market.status === 'CREATED' && (
                                    <>
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
                                
                                {market.status === 'CLOSED' && market.can_be_settled && (
                                    <button 
                                        onClick={() => {
                                            const outcome = prompt('Enter the final outcome (number):');
                                            if (outcome !== null) {
                                                handleSettleMarket(market.id, outcome);
                                            }
                                        }}
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