import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime } from '../../utils/dateUtils';
import { getStatusColor, getStatusText } from '../../utils/marketUtils';
import { apiGet, apiPost, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Dashboard.css';

const Dashboard = () => {
    const [markets, setMarkets] = useState([]);
    const [userData, setUserData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
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
                if (shouldRedirectToLogin(error)) {
                    navigate('/auth');
                    return;
                }
                handleApiError(error);
                setError('Failed to load data');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [navigate]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/auth');
    };

    const handleTrade = async (marketId, position) => {
        try {
            setError('');
            const response = await apiPost(`/api/market/${marketId}/place_trade/`, {
                position: position,
                quantity: 1
            });
            
            alert(`${position} trade placed successfully!`);
            // Refresh data after successful trade
            const marketResponse = await apiGet('/api/market/');
            setMarkets(marketResponse);
        } catch (error) {
            console.error('Error placing trade:', error);
            const errorMessage = handleApiError(error);
            setError(`Error placing trade: ${errorMessage}`);
        }
    };

    if (loading) {
        return (
            <div className="dashboard">
                <div className="loading-spinner">Loading dashboard...</div>
            </div>
        );
    }

    return (
        <div className="dashboard-container">
            <div className="dashboard-header">
                <div className="header-left">
                <h1>Market Dashboard</h1>
                    {userData && (
                        <div className="user-summary">
                            <span className="welcome-text">Welcome, <strong>{userData.username}</strong>!</span>
                            <span className="balance-info">Balance: <strong>${userData.balance || 0}</strong></span>
                        </div>
                    )}
                </div>
                <div className="header-actions">
                    <button onClick={() => navigate('/trading')} className="btn btn-primary">
                        Trading
                    </button>
                    <button onClick={handleLogout} className="btn btn-outline">
                        Logout
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            {/* Quick Stats */}
            <div className="dashboard-stats">
                <div className="stat-card">
                    <div className="stat-number">{markets.length}</div>
                    <div className="stat-label">Total Markets</div>
                </div>
                <div className="stat-card">
                    <div className="stat-number">{markets.filter(m => m.status === 'OPEN').length}</div>
                    <div className="stat-label">Active Markets</div>
                </div>
                <div className="stat-card">
                    <div className="stat-number">{markets.filter(m => m.user_trade).length}</div>
                    <div className="stat-label">Your Positions</div>
                </div>
                <div className="stat-card">
                    <div className="stat-number">{markets.filter(m => !m.can_user_trade?.can_trade && m.status === 'OPEN').length}</div>
                    <div className="stat-label">You're Market Maker</div>
                </div>
            </div>

            {/* Markets organized by status */}
            <div className="markets-sections">
                {/* Active Markets */}
                {markets.filter(m => m.status === 'OPEN').length > 0 && (
                    <div className="market-status-section">
                        <h2>🔥 Active Markets</h2>
            <div className="markets-grid">
                            {markets.filter(m => m.status === 'OPEN').map(market => (
                                <div key={market.id} className="market-card active">
                                    <div className="market-header">
                        <h3>{market.premise}</h3>
                                        <span className="status-badge status-active">ACTIVE</span>
                                    </div>
                                    
                                    <div className="market-info">
                                        <div className="spread-info">
                                            <span>Spread: ${market.final_spread_low} - ${market.final_spread_high}</span>
                                        </div>
                                        <div className="timing-info">
                                            <span>Closes: {formatDateTime(market.trading_close)}</span>
                                        </div>
                                        <div className="trade-stats">
                                            <span>{market.total_trades_count} trades ({market.long_trades_count} LONG, {market.short_trades_count} SHORT)</span>
                                        </div>
                                    </div>
                                    
                                    {market.can_user_trade?.can_trade ? (
                                        <>
                                            {market.user_trade ? (
                                                <div className="current-position">
                                                    <div className="position-badge position-badge-{market.user_trade.position.toLowerCase()}">
                                                        Your Position: {market.user_trade.position}
                                                    </div>
                                                    <p>{market.user_trade.quantity} units @ ${market.user_trade.price}</p>
                                                    <button 
                                                        onClick={() => navigate(`/trading?market=${market.id}`)}
                                                        className="btn btn-secondary btn-small"
                                                    >
                                                        Manage Position
                                                    </button>
                                                </div>
                                            ) : (
                                                <div className="trade-options">
                                                    <p className="trade-prompt">Choose your position:</p>
                                                    <div className="trade-buttons">
                                                        <button 
                                                            onClick={() => handleTrade(market.id, 'LONG')}
                                                            className="btn btn-success btn-small"
                                                        >
                                                            BUY ${market.market_maker_spread_high}
                                                        </button>
                                                        <button 
                                                            onClick={() => handleTrade(market.id, 'SHORT')}
                                                            className="btn btn-danger btn-small"
                                                        >
                                                            SELL ${market.market_maker_spread_low}
                                                        </button>
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    ) : (
                                        <div className="market-maker-info">
                                            <div className="market-maker-badge">
                                                🎯 Market Maker
                                            </div>
                                            <p>Your Spread: ${market.final_spread_low} - ${market.final_spread_high}</p>
                                            <button 
                                                onClick={() => navigate('/trading')}
                                                className="btn btn-info btn-small"
                                            >
                                                View Trade Activity
                                            </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Bidding Markets */}
                {markets.filter(m => m.status === 'CREATED').length > 0 && (
                    <div className="market-status-section">
                        <h2>⏳ Spread Bidding Active</h2>
                        <div className="markets-grid">
                            {markets.filter(m => m.status === 'CREATED').map(market => (
                                <div key={market.id} className="market-card bidding">
                                    <div className="market-header">
                                        <h3>{market.premise}</h3>
                                        <span className="status-badge status-bidding">BIDDING</span>
                                    </div>
                                    
                                    <div className="market-info">
                                        <div className="timing-info">
                                            <span>Bidding closes: {formatDateTime(market.spread_bidding_close_trading_open)}</span>
                                            <span>Trading opens: {formatDateTime(market.spread_bidding_close_trading_open)}</span>
                                        </div>
                                        {market.best_spread_bid && (
                                            <div className="best-bid">
                                                <span>Best bid: {market.best_spread_bid.spread_width} width by {market.best_spread_bid.user}</span>
                                            </div>
                                        )}
                        </div>
                        
                                    {market.is_spread_bidding_active && (
                                        <div className="spread-bidding-section">
                                            <p className="bid-prompt">Compete to become market maker!</p>
                                <button 
                                                onClick={() => navigate('/trading')}
                                                className="btn btn-primary btn-small"
                                >
                                                Place Spread Bid
                                </button>
                            </div>
                        )}
                    </div>
                ))}
                        </div>
                    </div>
                )}

                {/* Closed/Settled Markets */}
                {markets.filter(m => ['CLOSED', 'SETTLED'].includes(m.status)).length > 0 && (
                    <div className="market-status-section">
                        <h2>📊 Completed Markets</h2>
                        <div className="markets-grid">
                            {markets.filter(m => ['CLOSED', 'SETTLED'].includes(m.status)).map(market => (
                                <div key={market.id} className="market-card completed">
                                    <div className="market-header">
                                        <h3>{market.premise}</h3>
                                        <span className={`status-badge status-${market.status.toLowerCase()}`}>
                                            {market.status}
                                        </span>
                                    </div>
                                    
                                    <div className="market-info">
                                        {market.outcome !== null && (
                                            <div className="outcome-info">
                                                <span>Outcome: {market.outcome}</span>
                                            </div>
                                        )}
                                        <div className="trade-stats">
                                            <span>{market.total_trades_count} total trades</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {markets.length === 0 && !loading && (
                <div className="no-markets">
                    <div className="no-markets-icon">📈</div>
                    <h3>No markets available</h3>
                    <p>Check back later for new prediction markets!</p>
                </div>
            )}
        </div>
    );
};

export default Dashboard; 