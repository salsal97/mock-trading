import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime, formatForDateTimeInput } from '../../utils/dateUtils';
import { getStatusBadgeClass, shouldShowAutoActivateButton } from '../../utils/marketUtils';
import { validateMarketTiming, getMinDateTime } from '../../utils/formUtils';
import { apiGet, apiPost, apiPatch, apiDelete, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './MarketManagement.css';

const MarketManagement = () => {
    const [markets, setMarkets] = useState([]);
    const [stats, setStats] = useState(null);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [showEditForm, setShowEditForm] = useState(false);
    const [editingMarket, setEditingMarket] = useState(null);
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
    const [editMarket, setEditMarket] = useState({
        premise: '',
        unit_price: 1.0,
        initial_spread: '',
        spread_bidding_open: '',
        spread_bidding_close: '',
        trading_open: '',
        trading_close: '',
        status: '',
        outcome: ''
    });
    const navigate = useNavigate();

    useEffect(() => {
        verifyAdminAndFetchData();
    }, []);

    // Real-time validation as user types
    useEffect(() => {
        const errors = validateMarketTiming(newMarket);
        setValidationErrors(errors);
    }, [newMarket.spread_bidding_open, newMarket.spread_bidding_close, newMarket.trading_open, newMarket.trading_close]);

    const verifyAdminAndFetchData = async () => {
        try {
            setLoading(true);
            setError('');
            
            // Verify admin status and fetch data
            const [marketsResponse, statsResponse] = await Promise.all([
                apiGet('/api/market/'),
                apiGet('/api/market/stats/').catch(() => ({ data: null })) // Stats endpoint might not exist
            ]);

            setMarkets(marketsResponse);
            setStats(statsResponse.data);
        } catch (error) {
            console.error('Error fetching data:', error);
            const errorMessage = handleApiError(error);
            setError(errorMessage);
            
            if (error.response?.status === 403) {
                setTimeout(() => navigate('/dashboard'), 2000);
            } else if (shouldRedirectToLogin(error)) {
                navigate('/login');
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

        try {
            await apiPost('/api/market/', newMarket);

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
            const errorMessage = handleApiError(error);
            setError(`Error creating market: ${errorMessage}`);
        }
    };

    const handleEditMarket = async (e) => {
        e.preventDefault();
        
        if (!editingMarket) return;

        try {
            await apiPatch(`/api/market/${editingMarket.id}/edit/`, editMarket);

            // Reset form and refresh data
            setEditingMarket(null);
            setShowEditForm(false);
            setError('');
            await verifyAdminAndFetchData();
            
            alert('Market updated successfully!');
        } catch (error) {
            console.error('Error updating market:', error);
            const errorMessage = handleApiError(error);
            setError(`Error updating market: ${errorMessage}`);
        }
    };

    const startEditMarket = (market) => {
        setEditingMarket(market);
        
        setEditMarket({
            premise: market.premise,
            unit_price: market.unit_price,
            initial_spread: market.initial_spread,
            spread_bidding_open: formatForDateTimeInput(market.spread_bidding_open),
            spread_bidding_close: formatForDateTimeInput(market.spread_bidding_close),
            trading_open: formatForDateTimeInput(market.trading_open),
            trading_close: formatForDateTimeInput(market.trading_close),
            status: market.status,
            outcome: market.outcome || ''
        });
        
        setShowEditForm(true);
        setError('');
        
        // Log timezone debugging info
        if (market.timezone_info) {
            console.log('Timezone Debug Info:', market.timezone_info);
            console.log('Server Time:', market.server_time);
            console.log('Local Time:', new Date().toISOString());
        }
    };

    const cancelEdit = () => {
        setEditingMarket(null);
        setShowEditForm(false);
        setError('');
    };

    const handleUpdateMarketStatus = async (marketId, newStatus) => {
        try {
            await apiPatch(`/api/market/${marketId}/`, { status: newStatus });
            await verifyAdminAndFetchData();
        } catch (error) {
            console.error('Error updating market status:', error);
            const errorMessage = handleApiError(error);
            setError(`Error updating market status: ${errorMessage}`);
        }
    };

    const handleManualActivate = async (marketId) => {
        setActivating(prev => ({ ...prev, [marketId]: true }));
        
        try {
            const response = await apiPost(`/api/market/${marketId}/manual_activate/`, {});
            
            // Show success message with details
            const details = response.details;
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
            const errorMessage = handleApiError(error);
            setError(`Error activating market: ${errorMessage}`);
        } finally {
            setActivating(prev => ({ ...prev, [marketId]: false }));
        }
    };

    const handleSetFinalSpread = async (marketId) => {
        const spreadLow = prompt('Enter final spread low:');
        const spreadHigh = prompt('Enter final spread high:');
        
        if (spreadLow && spreadHigh) {
            try {
                await apiPatch(`/api/market/${marketId}/`, { 
                    final_spread_low: parseInt(spreadLow),
                    final_spread_high: parseInt(spreadHigh)
                });
                await verifyAdminAndFetchData();
            } catch (error) {
                console.error('Error setting final spread:', error);
                const errorMessage = handleApiError(error);
                setError(`Error setting final spread: ${errorMessage}`);
            }
        }
    };

    const handleDeleteMarket = async (marketId) => {
        if (window.confirm('Are you sure you want to delete this market?')) {
            try {
                await apiDelete(`/api/market/${marketId}/`);
                await verifyAdminAndFetchData();
            } catch (error) {
                console.error('Error deleting market:', error);
                const errorMessage = handleApiError(error);
                setError(`Error deleting market: ${errorMessage}`);
            }
        }
    };

    if (loading) {
        return <div className="loading">Loading market management...</div>;
    }

    return (
        <div className="market-management-container">
            <div className="market-header">
                <div className="header-left">
                    <button className="back-button" onClick={() => navigate('/admin')}>
                        ← Back to Admin
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
                    <button className="logout-button" onClick={() => {
                        localStorage.removeItem('token');
                        navigate('/');
                    }}>
                        Logout
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            {/* Statistics */}
            {stats && (
                <div className="stats-overview">
                    <div className="stat-card">
                        <h3>Total Markets</h3>
                        <div className="stat-number">{stats.total_markets}</div>
                    </div>
                    <div className="stat-card">
                        <h3>Active Markets</h3>
                        <div className="stat-number">{stats.active_markets}</div>
                    </div>
                    <div className="stat-card">
                        <h3>Total Spread Bids</h3>
                        <div className="stat-number">{stats.total_spread_bids}</div>
                    </div>
                </div>
            )}

            {/* Create Form */}
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
                                <label>Unit Price ($):</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={newMarket.unit_price}
                                    onChange={(e) => setNewMarket({...newMarket, unit_price: parseFloat(e.target.value)})}
                                    required
                                    min="0.01"
                                />
                            </div>
                            <div className="form-group">
                                <label>Initial Spread:</label>
                                <input
                                    type="number"
                                    value={newMarket.initial_spread}
                                    onChange={(e) => setNewMarket({...newMarket, initial_spread: e.target.value})}
                                    required
                                    min="1"
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Spread Bidding Open:</label>
                                <input
                                    type="datetime-local"
                                    value={newMarket.spread_bidding_open}
                                    min={getMinDateTime('spread_bidding_open', newMarket)}
                                    onChange={(e) => setNewMarket({...newMarket, spread_bidding_open: e.target.value})}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Spread Bidding Close:</label>
                                <input
                                    type="datetime-local"
                                    value={newMarket.spread_bidding_close}
                                    min={getMinDateTime('spread_bidding_close', newMarket)}
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
                                    min={getMinDateTime('trading_open', newMarket)}
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
                                    min={getMinDateTime('trading_close', newMarket)}
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
                            <button type="submit" className="submit-button">Create Market</button>
                            <button type="button" className="cancel-button" onClick={() => setShowCreateForm(false)}>Cancel</button>
                        </div>
                    </form>
                </div>
            )}

            {/* Edit Form */}
            {showEditForm && editingMarket && (
                <div className="create-form-section">
                    <h2>Edit Market: {editingMarket.premise.substring(0, 50)}...</h2>
                    <div className="timezone-debug">
                        <small>
                            <strong>Timezone Info:</strong> Times are displayed in your local timezone for editing. 
                            Server stores in UTC. Current server time: {editingMarket.server_time ? new Date(editingMarket.server_time).toLocaleString() : 'N/A'}
                        </small>
                    </div>
                    <form onSubmit={handleEditMarket} className="create-form">
                        <div className="form-group">
                            <label>Market Premise:</label>
                            <textarea
                                value={editMarket.premise}
                                onChange={(e) => setEditMarket({...editMarket, premise: e.target.value})}
                                placeholder="Enter the market question or premise..."
                                required
                                rows="3"
                            />
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Unit Price ($):</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    value={editMarket.unit_price}
                                    onChange={(e) => setEditMarket({...editMarket, unit_price: parseFloat(e.target.value)})}
                                    required
                                    min="0.01"
                                />
                            </div>
                            <div className="form-group">
                                <label>Initial Spread:</label>
                                <input
                                    type="number"
                                    value={editMarket.initial_spread}
                                    onChange={(e) => setEditMarket({...editMarket, initial_spread: e.target.value})}
                                    required
                                    min="1"
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Spread Bidding Open:</label>
                                <input
                                    type="datetime-local"
                                    value={editMarket.spread_bidding_open}
                                    onChange={(e) => setEditMarket({...editMarket, spread_bidding_open: e.target.value})}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Spread Bidding Close:</label>
                                <input
                                    type="datetime-local"
                                    value={editMarket.spread_bidding_close}
                                    onChange={(e) => setEditMarket({...editMarket, spread_bidding_close: e.target.value})}
                                    required
                                />
                            </div>
                        </div>

                        <div className="form-row">
                            <div className="form-group">
                                <label>Trading Open:</label>
                                <input
                                    type="datetime-local"
                                    value={editMarket.trading_open}
                                    onChange={(e) => setEditMarket({...editMarket, trading_open: e.target.value})}
                                    required
                                />
                            </div>
                            <div className="form-group">
                                <label>Trading Close:</label>
                                <input
                                    type="datetime-local"
                                    value={editMarket.trading_close}
                                    onChange={(e) => setEditMarket({...editMarket, trading_close: e.target.value})}
                                    required
                                />
                            </div>
                        </div>

                        {/* Status and Outcome for existing markets */}
                        <div className="form-row">
                            <div className="form-group">
                                <label>Status:</label>
                                <select
                                    value={editMarket.status}
                                    onChange={(e) => setEditMarket({...editMarket, status: e.target.value})}
                                >
                                    <option value="CREATED">Created</option>
                                    <option value="OPEN">Open</option>
                                    <option value="CLOSED">Closed</option>
                                    <option value="SETTLED">Settled</option>
                                </select>
                            </div>
                            <div className="form-group">
                                <label>Outcome (if settled):</label>
                                <input
                                    type="number"
                                    value={editMarket.outcome}
                                    onChange={(e) => setEditMarket({...editMarket, outcome: e.target.value})}
                                    placeholder="Final outcome value"
                                />
                            </div>
                        </div>

                        <div className="form-actions">
                            <button type="submit" className="submit-button">Update Market</button>
                            <button type="button" className="cancel-button" onClick={cancelEdit}>Cancel</button>
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
                                <button 
                                    className="edit-button action-button"
                                    onClick={() => startEditMarket(market)}
                                >
                                    Edit
                                </button>
                                
                                {shouldShowAutoActivateButton(market) && (
                                    <button 
                                        className="activate-button action-button"
                                        onClick={() => handleManualActivate(market.id)}
                                        disabled={activating[market.id]}
                                    >
                                        {activating[market.id] ? 'Activating...' : 'Activate Market'}
                                    </button>
                                )}
                                
                                {market.status === 'CREATED' && market.final_spread_low === null && (
                                    <button 
                                        className="set-spread-button action-button"
                                        onClick={() => handleSetFinalSpread(market.id)}
                                    >
                                        Set Final Spread
                                    </button>
                                )}
                                
                                {market.status === 'OPEN' && (
                                    <button 
                                        className="close-button action-button"
                                        onClick={() => handleUpdateMarketStatus(market.id, 'CLOSED')}
                                    >
                                        Close Trading
                                    </button>
                                )}
                                
                                {market.status === 'CLOSED' && (
                                    <button 
                                        className="settle-button action-button"
                                        onClick={() => handleUpdateMarketStatus(market.id, 'SETTLED')}
                                    >
                                        Settle
                                    </button>
                                )}
                                
                                <button 
                                    className="delete-button action-button"
                                    onClick={() => handleDeleteMarket(market.id)}
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default MarketManagement; 