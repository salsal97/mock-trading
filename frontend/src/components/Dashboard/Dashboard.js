import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime } from '../../utils/dateUtils';
import { getStatusColor, getStatusText } from '../../utils/marketUtils';
import { apiGet, apiPost, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Dashboard.css';

const Dashboard = () => {
    const [userData, setUserData] = useState(null);
    const [markets, setMarkets] = useState([]);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [bidding, setBidding] = useState({});
    const [bidForms, setBidForms] = useState({});
    const navigate = useNavigate();

    useEffect(() => {
        fetchData();
    }, [navigate]);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError('');
            
            const [userResponse, marketsResponse] = await Promise.all([
                apiGet('/api/auth/user-profile/'),
                apiGet('/api/market/')
            ]);
            
            setUserData(userResponse);
            setMarkets(marketsResponse);
        } catch (error) {
            console.error('Error fetching data:', error);
            const errorMessage = handleApiError(error);
            setError(errorMessage);
            
            if (shouldRedirectToLogin(error)) {
                localStorage.removeItem('token');
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

    const handleSpreadBid = async (marketId) => {
        const bidData = bidForms[marketId];
        if (!bidData || !bidData.spread_low || !bidData.spread_high) {
            setError('Please enter both spread low and high values');
            return;
        }

        setBidding(prev => ({ ...prev, [marketId]: true }));
        
        try {
            await apiPost(
                `/api/market/${marketId}/place_spread_bid/`,
                {
                    spread_low: parseInt(bidData.spread_low),
                    spread_high: parseInt(bidData.spread_high)
                }
            );

            // Refresh markets data
            const marketsResponse = await apiGet('/api/market/');
            setMarkets(marketsResponse);
            
            // Clear the form
            setBidForms(prev => ({ ...prev, [marketId]: { spread_low: '', spread_high: '' } }));
            setError('');
        } catch (error) {
            console.error('Error placing spread bid:', error);
            const errorMessage = handleApiError(error);
            setError(`Error placing bid: ${errorMessage}`);
        } finally {
            setBidding(prev => ({ ...prev, [marketId]: false }));
        }
    };

    const updateBidForm = (marketId, field, value) => {
        setBidForms(prev => ({
            ...prev,
            [marketId]: {
                ...prev[marketId],
                [field]: value
            }
        }));
    };

    if (loading) {
        return <div className="dashboard-container">Loading...</div>;
    }

    if (error) {
        return <div className="dashboard-container error">{error}</div>;
    }

    if (!userData) {
        return <div className="dashboard-container">Loading...</div>;
    }

    return (
        <div className="dashboard-container">
            <div className="dashboard-header">
                <h1>Welcome, {userData.username}!</h1>
                <div className="header-actions">
                    <button 
                        onClick={() => navigate('/trading')} 
                        className="trading-button"
                    >
                        Trading Dashboard
                    </button>
                    <button onClick={handleLogout} className="logout-button">
                        Logout
                    </button>
                </div>
            </div>
            <div className="dashboard-content">
                <div className="dashboard-card">
                    <h2>Account Overview</h2>
                    <p>Email: {userData.email}</p>
                    <p>Account Status: {userData.is_verified ? 'Verified' : 'Pending Verification'}</p>
                    <p>Member Since: {new Date(userData.date_joined).toLocaleDateString()}</p>
                    {!userData.is_verified && (
                        <div className="verification-notice">
                            <strong>Note:</strong> Your account needs verification to participate in spread bidding.
                        </div>
                    )}
                </div>
                
                <div className="dashboard-card markets-card">
                    <h2>Available Markets ({markets.length})</h2>
                    {markets.length === 0 ? (
                        <p className="no-markets">No markets available at the moment.</p>
                    ) : (
                        <div className="markets-list">
                            {markets.map(market => (
                                <div key={market.id} className="market-item">
                                    <div className="market-header">
                                        <h3>{market.premise}</h3>
                                        <span 
                                            className="status-badge"
                                            style={{ backgroundColor: getStatusColor(market.status) }}
                                        >
                                            {getStatusText(market.status)}
                                        </span>
                                    </div>
                                    <div className="market-details">
                                        <div className="market-info">
                                            <span>Unit Price: ${market.unit_price}</span>
                                            <span>Current Spread: {market.current_spread_display}</span>
                                        </div>
                                        
                                        {/* Trade Statistics */}
                                        {(market.long_trades_count > 0 || market.short_trades_count > 0) && (
                                            <div className="trade-stats">
                                                <span className="long-trades">Long: {market.long_trades_count}</span>
                                                <span className="short-trades">Short: {market.short_trades_count}</span>
                                                <span className="total-trades">Total: {market.total_trades_count}</span>
                                            </div>
                                        )}
                                        
                                        {/* User's Trade Status */}
                                        {market.user_trade && (
                                            <div className={`user-trade-status ${market.user_trade.position.toLowerCase()}`}>
                                                Your Position: {market.user_trade.position} at ${market.user_trade.price}
                                                {market.is_trading_active && (
                                                    <button 
                                                        className="edit-trade-btn"
                                                        onClick={() => navigate('/trading')}
                                                    >
                                                        Edit
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                        
                                        {/* Best Spread Bid Info */}
                                        {market.best_spread_bid && (
                                            <div className="best-bid-info">
                                                <strong>Leading Bid:</strong> Width of {market.best_spread_bid.spread_width} by {market.best_spread_bid.user} 
                                                <span className="bid-time">
                                                    ({formatDateTime(market.best_spread_bid.bid_time)})
                                                </span>
                                            </div>
                                        )}
                                        
                                        {/* Timing Information */}
                                        {market.status === 'CREATED' && (
                                            <div className="market-timing">
                                                <span>Spread Bidding: {formatDateTime(market.spread_bidding_open)} - {formatDateTime(market.spread_bidding_close)}</span>
                                                <span>Trading starts: {formatDateTime(market.trading_open)}</span>
                                            </div>
                                        )}
                                        {market.status === 'OPEN' && (
                                            <div className="market-timing">
                                                <span>Trading until: {formatDateTime(market.trading_close)}</span>
                                            </div>
                                        )}
                                        {market.status === 'SETTLED' && market.outcome !== null && (
                                            <div className="market-outcome">
                                                <strong>Final Outcome: {market.outcome}</strong>
                                            </div>
                                        )}
                                        
                                        {/* Spread Bidding Interface */}
                                        {market.status === 'CREATED' && market.is_spread_bidding_active && userData.is_verified && (
                                            <div className="spread-bidding-section">
                                                <h4>Place Spread Bid</h4>
                                                <p className="bid-requirement">
                                                    Your spread width must be smaller than the current best of {market.current_best_spread_width}
                                                </p>
                                                <div className="bid-form">
                                                    <div className="bid-inputs">
                                                        <input
                                                            type="number"
                                                            placeholder="Spread Low"
                                                            value={bidForms[market.id]?.spread_low || ''}
                                                            onChange={(e) => updateBidForm(market.id, 'spread_low', e.target.value)}
                                                            disabled={bidding[market.id]}
                                                        />
                                                        <input
                                                            type="number"
                                                            placeholder="Spread High"
                                                            value={bidForms[market.id]?.spread_high || ''}
                                                            onChange={(e) => updateBidForm(market.id, 'spread_high', e.target.value)}
                                                            disabled={bidding[market.id]}
                                                        />
                                                    </div>
                                                    <button
                                                        className="bid-button"
                                                        onClick={() => handleSpreadBid(market.id)}
                                                        disabled={bidding[market.id]}
                                                    >
                                                        {bidding[market.id] ? 'Placing Bid...' : 'Place Bid'}
                                                    </button>
                                                </div>
                                            </div>
                                        )}
                                        
                                        {/* Spread Bidding Closed Message */}
                                        {market.status === 'CREATED' && !market.is_spread_bidding_active && (
                                            <div className="bidding-closed">
                                                Spread bidding is not currently active for this market.
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Dashboard; 