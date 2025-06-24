import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { formatDateTime, formatCurrency } from '../../utils/dateUtils';
import { getPositionClass, getTradeStatusText, getStatusBadgeClass, getStatusText, getProfitLossClass } from '../../utils/marketUtils';
import { apiGet, apiPost, apiDelete, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Trading.css';

const Trading = () => {
    const [markets, setMarkets] = useState([]);
    const [selectedMarket, setSelectedMarket] = useState(null);
    const [positions, setPositions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [balance, setBalance] = useState(0);
    const [tradeForm, setTradeForm] = useState({
        position: 'LONG',
        price: '',
        quantity: 1
    });
    const [showMarketMakerForm, setShowMarketMakerForm] = useState(false);
    const [marketMakerForm, setMarketMakerForm] = useState({
        spreadLow: '',
        spreadHigh: ''
    });
    const [showSpreadBidForm, setShowSpreadBidForm] = useState(false);
    const [spreadBidForm, setSpreadBidForm] = useState({
        spreadLow: '',
        spreadHigh: ''
    });
    const navigate = useNavigate();
    const location = useLocation();

    const fetchTradingData = async () => {
        try {
            setLoading(true);
            setError('');
            
            const [marketsResponse, positionsResponse] = await Promise.all([
                apiGet('/api/market/'),
                apiGet('/api/market/positions/')
            ]);
            
            setMarkets(marketsResponse);
            setPositions(positionsResponse.positions || []);
            
            // Auto-select market if market ID is provided in URL
            const urlParams = new URLSearchParams(location.search);
            const marketId = urlParams.get('market');
            if (marketId && marketsResponse.length > 0) {
                const market = marketsResponse.find(m => m.id === parseInt(marketId));
                if (market) {
                    setSelectedMarket(market);
                }
            }
        } catch (error) {
            console.error('Error fetching trading data:', error);
            if (shouldRedirectToLogin(error)) {
                navigate('/auth');
                return;
            }
            handleApiError(error);
            setError('Failed to load trading data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTradingData();
    }, [navigate, location.search]);

    const openTradeModal = (market) => {
        setSelectedMarket(market);
        
        // If user already has a trade on this market, populate the form
        if (market.user_trade) {
            setTradeForm({
                position: market.user_trade.position,
                price: market.user_trade.price.toString(),
                quantity: market.user_trade.quantity
            });
        } else {
            // Set default price based on position and market spread
            const defaultPrice = market.final_spread_high || market.unit_price;
            setTradeForm({
                position: 'LONG',
                price: defaultPrice.toString(),
                quantity: 1
            });
        }
    };

    const closeTradeModal = () => {
        setSelectedMarket(null);
        setTradeForm({
            position: 'LONG',
            price: '',
            quantity: 1
        });
        setError('');
    };

    const handleTradeSubmit = async (e) => {
        e.preventDefault();
        setError('');

        try {
            const response = await apiPost(
                `/api/market/${selectedMarket.id}/place_trade/`,
                {
                    position: tradeForm.position,
                    price: parseFloat(tradeForm.price),
                    quantity: parseInt(tradeForm.quantity)
                }
            );

            alert(response.message);
            closeTradeModal();
            await fetchTradingData(); // Refresh data
        } catch (error) {
            console.error('Error placing trade:', error);
            const errorMessage = handleApiError(error);
            setError(`Error placing trade: ${errorMessage}`);
        }
    };

    const handleCancelTrade = async (marketId) => {
        if (!window.confirm('Are you sure you want to cancel this trade?')) {
            return;
        }

        try {
            await apiDelete(`/api/market/${marketId}/cancel_trade/`);
            alert('Trade cancelled successfully');
            await fetchTradingData(); // Refresh data
        } catch (error) {
            console.error('Error cancelling trade:', error);
            const errorMessage = handleApiError(error);
            alert(`Error cancelling trade: ${errorMessage}`);
        }
    };

    const handleMarketMakerSubmit = async (e) => {
        e.preventDefault();
        
        if (!selectedMarket) {
            setError('Please select a market first');
            return;
        }

        const spreadLow = parseFloat(marketMakerForm.spreadLow);
        const spreadHigh = parseFloat(marketMakerForm.spreadHigh);

        if (spreadLow >= spreadHigh) {
            setError('Spread high must be greater than spread low');
            return;
        }

        if (spreadLow < 0) {
            setError('Spread values must be positive');
            return;
        }

        try {
            setError('');
            
            const response = await apiPost(`/api/market/${selectedMarket.id}/set-market-maker/`, {
                spread_low: spreadLow,
                spread_high: spreadHigh
            });

            alert(`Successfully set as market maker with spread: $${spreadLow} - $${spreadHigh}`);
            setShowMarketMakerForm(false);
            setMarketMakerForm({ spreadLow: '', spreadHigh: '' });
            fetchTradingData(); // Refresh data
            
        } catch (error) {
            console.error('Error setting market maker:', error);
            if (shouldRedirectToLogin(error)) {
                navigate('/auth');
                return;
            }
            handleApiError(error);
            setError('Failed to set market maker spread');
        }
    };

    const handleSpreadBidSubmit = async (e) => {
        e.preventDefault();
        
        if (!selectedMarket) {
            setError('Please select a market first');
            return;
        }

        const spreadLow = parseFloat(spreadBidForm.spreadLow);
        const spreadHigh = parseFloat(spreadBidForm.spreadHigh);

        if (spreadLow >= spreadHigh) {
            setError('Spread high must be greater than spread low');
            return;
        }

        if (spreadLow < 0) {
            setError('Spread values must be positive');
            return;
        }

        // Calculate spread width
        const spreadWidth = spreadHigh - spreadLow;
        
        // Check if this is a competitive bid (narrower than initial spread)
        if (spreadWidth >= selectedMarket.initial_spread) {
            setError(`Your spread width (${spreadWidth}) must be narrower than the initial spread (${selectedMarket.initial_spread}) to be competitive.`);
            return;
        }

        try {
            setError('');
            
            const response = await apiPost(`/api/market/${selectedMarket.id}/place_spread_bid/`, {
                spread_low: spreadLow,
                spread_high: spreadHigh
            });

            alert(`Spread bid placed successfully! Spread: $${spreadLow} - $${spreadHigh} (Width: ${spreadWidth})`);
            setShowSpreadBidForm(false);
            setSpreadBidForm({ spreadLow: '', spreadHigh: '' });
            fetchTradingData(); // Refresh data
            
        } catch (error) {
            console.error('Error placing spread bid:', error);
            if (shouldRedirectToLogin(error)) {
                navigate('/auth');
                return;
            }
            const errorMessage = handleApiError(error);
            setError(`Error placing spread bid: ${errorMessage}`);
        }
    };

    if (loading) {
        return <div className="loading">Loading trading data...</div>;
    }

    return (
        <div className="trading-container">
            <div className="trading-header">
                <div className="header-content">
                    <h1>Prediction Markets</h1>
                    <div className="header-actions">
                        <div className="balance-display">
                            Balance: {formatCurrency(balance)}
                        </div>
                        <button 
                            onClick={() => navigate('/trade-history')} 
                            className="btn btn-secondary"
                        >
                            Trade History
                        </button>
                        <button 
                            onClick={() => navigate('/dashboard')} 
                            className="btn btn-primary"
                        >
                            Dashboard
                        </button>
                    </div>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="trading-layout">
                {/* Markets List */}
                <div className="markets-section">
                    <h2>Available Markets</h2>
                    {loading ? (
                        <div className="loading-spinner">Loading markets...</div>
                    ) : (
                        <div className="markets-list">
                            {markets.map(market => (
                                <div 
                                    key={market.id} 
                                    className={`market-card ${selectedMarket?.id === market.id ? 'selected' : ''}`}
                                    onClick={() => setSelectedMarket(market)}
                                >
                                    <div className="market-header">
                                        <h3>{market.premise}</h3>
                                        <span className={`status-badge ${getStatusBadgeClass(market.status)}`}>
                                            {market.status}
                                        </span>
                                    </div>
                                    
                                    <div className="market-details">
                                        <div className="detail-row">
                                            <span>Trading closes:</span>
                                            <span>{formatDateTime(market.trading_close)}</span>
                                        </div>
                                        {market.market_maker && (
                                            <div className="detail-row">
                                                <span>Market Maker:</span>
                                                <span>{market.market_maker_username}</span>
                                            </div>
                                        )}
                                        {market.market_maker_spread_low && market.market_maker_spread_high && (
                                            <div className="detail-row">
                                                <span>Spread:</span>
                                                <span>{formatCurrency(market.market_maker_spread_low)} - {formatCurrency(market.market_maker_spread_high)}</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Trading Panel */}
                <div className="trading-panel">
                    {selectedMarket ? (
                        <>
                            <div className="selected-market">
                                <h2>{selectedMarket.premise}</h2>
                                <p className="market-description">{selectedMarket.description}</p>
                                
                                <div className="market-info-grid">
                                    <div className="info-item">
                                        <span className="label">Status:</span>
                                        <span className={`value status-${selectedMarket.status.toLowerCase()}`}>
                                            {getStatusText(selectedMarket.status)}
                                        </span>
                                    </div>
                                    <div className="info-item">
                                        <span className="label">Trading Closes:</span>
                                        <span className="value">{formatDateTime(selectedMarket.trading_close)}</span>
                                    </div>
                                    <div className="info-item">
                                        <span className="label">Resolution Date:</span>
                                        <span className="value">{formatDateTime(selectedMarket.resolution_date)}</span>
                                    </div>
                                </div>

                                {/* Spread Bidding Section */}
                                {selectedMarket.status === 'CREATED' && selectedMarket.is_spread_bidding_active && (
                                    <div className="spread-bidding-section">
                                        <h3>🎯 Compete to Become Market Maker</h3>
                                        <p>Place a spread bid to compete for the right to become the market maker. The bid with the narrowest spread wins!</p>
                                        
                                        {/* Current best bid display */}
                                        <div className="best-bid-display">
                                            {selectedMarket.best_spread_bid ? (
                                                <div className="current-best-bid">
                                                    <h4>Current Leading Bid:</h4>
                                                    <div className="bid-details">
                                                        <span className="bid-user">👤 {selectedMarket.best_spread_bid.user}</span>
                                                        <span className="bid-spread">📊 ${selectedMarket.best_spread_bid.spread_low} - ${selectedMarket.best_spread_bid.spread_high}</span>
                                                        <span className="bid-width">📏 Width: {selectedMarket.best_spread_bid.spread_width}</span>
                                                    </div>
                                                    <p className="beat-bid-text">Place a bid with a narrower spread to take the lead!</p>
                                                </div>
                                            ) : (
                                                <div className="no-bids">
                                                    <p>No bids yet! Be the first to place a spread bid.</p>
                                                    <p>Initial spread width: <strong>{selectedMarket.initial_spread}</strong> - beat this to win!</p>
                                                </div>
                                            )}
                                        </div>

                                        <div className="bidding-timing">
                                            <p>⏰ Bidding closes: <strong>{formatDateTime(selectedMarket.spread_bidding_close_trading_open)}</strong></p>
                                        </div>
                                        
                                        {!showSpreadBidForm ? (
                                            <button 
                                                onClick={() => setShowSpreadBidForm(true)}
                                                className="btn btn-primary"
                                            >
                                                Place Spread Bid
                                            </button>
                                        ) : (
                                            <form onSubmit={handleSpreadBidSubmit} className="spread-bid-form">
                                                <div className="form-explanation">
                                                    <p><strong>How it works:</strong> Enter your bid for the spread you're willing to make the market at. The bidder with the narrowest spread (smallest difference between high and low) wins and becomes the market maker.</p>
                                                </div>
                                                
                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Spread Low (Short/Sell Price):</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            // max="100"
                                                            step="0.01"
                                                            value={spreadBidForm.spreadLow}
                                                            onChange={(e) => setSpreadBidForm({
                                                                ...spreadBidForm,
                                                                spreadLow: e.target.value
                                                            })}
                                                            placeholder="e.g., 35.00"
                                                            required
                                                        />
                                                        <small>Price at which you'll buy SHORT positions</small>
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Spread High (Long/Buy Price):</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            // max="100"
                                                            step="0.01"
                                                            value={spreadBidForm.spreadHigh}
                                                            onChange={(e) => setSpreadBidForm({
                                                                ...spreadBidForm,
                                                                spreadHigh: e.target.value
                                                            })}
                                                            placeholder="e.g., 65.00"
                                                            required
                                                        />
                                                        <small>Price at which you'll sell LONG positions</small>
                                                    </div>
                                                </div>
                                                
                                                {/* Real-time spread width calculation */}
                                                {spreadBidForm.spreadLow && spreadBidForm.spreadHigh && (
                                                    <div className="spread-preview">
                                                        <div className="preview-item">
                                                            <strong>Your Spread Width: {(parseFloat(spreadBidForm.spreadHigh) - parseFloat(spreadBidForm.spreadLow)).toFixed(2)}</strong>
                                                        </div>
                                                        <div className="preview-item">
                                                            <span>Target to beat: {selectedMarket.best_spread_bid ? selectedMarket.best_spread_bid.spread_width : selectedMarket.initial_spread}</span>
                                                        </div>
                                                        {parseFloat(spreadBidForm.spreadHigh) - parseFloat(spreadBidForm.spreadLow) < (selectedMarket.best_spread_bid ? selectedMarket.best_spread_bid.spread_width : selectedMarket.initial_spread) ? (
                                                            <div className="preview-success">✅ Competitive bid! This would be the new leading bid.</div>
                                                        ) : (
                                                            <div className="preview-warning">⚠️ Not competitive. Make your spread narrower to win.</div>
                                                        )}
                                                    </div>
                                                )}
                                                
                                                <div className="form-actions">
                                                    <button type="submit" className="btn btn-primary">
                                                        Submit Spread Bid
                                                    </button>
                                                    <button 
                                                        type="button" 
                                                        onClick={() => {
                                                            setShowSpreadBidForm(false);
                                                            setSpreadBidForm({ spreadLow: '', spreadHigh: '' });
                                                            setError('');
                                                        }}
                                                        className="btn btn-secondary"
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        )}
                                    </div>
                                )}

                                {/* Market Maker Section */}
                                {selectedMarket.status === 'OPEN' && !selectedMarket.market_maker && (
                                    <div className="market-maker-section">
                                        <h3>Become Market Maker</h3>
                                        <p>Set the spread for this market and become the market maker. All other traders will trade against your spread.</p>
                                        
                                        {!showMarketMakerForm ? (
                                            <button 
                                                onClick={() => setShowMarketMakerForm(true)}
                                                className="btn btn-secondary"
                                            >
                                                Set Market Maker Spread
                                            </button>
                                        ) : (
                                            <form onSubmit={handleMarketMakerSubmit} className="market-maker-form">
                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Spread Low (Sell Price):</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            step="0.01"
                                                            value={marketMakerForm.spreadLow}
                                                            onChange={(e) => setMarketMakerForm({
                                                                ...marketMakerForm,
                                                                spreadLow: e.target.value
                                                            })}
                                                            required
                                                        />
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Spread High (Buy Price):</label>
                                                        <input
                                                            type="number"
                                                            min="0"
                                                            step="0.01"
                                                            value={marketMakerForm.spreadHigh}
                                                            onChange={(e) => setMarketMakerForm({
                                                                ...marketMakerForm,
                                                                spreadHigh: e.target.value
                                                            })}
                                                            required
                                                        />
                                                    </div>
                                                </div>
                                                <div className="form-actions">
                                                    <button type="submit" className="btn btn-primary">
                                                        Set Spread
                                                    </button>
                                                    <button 
                                                        type="button" 
                                                        onClick={() => {
                                                            setShowMarketMakerForm(false);
                                                            setMarketMakerForm({ spreadLow: '', spreadHigh: '' });
                                                        }}
                                                        className="btn btn-secondary"
                                                    >
                                                        Cancel
                                                    </button>
                                                </div>
                                            </form>
                                        )}
                                    </div>
                                )}

                                {/* Trading Form */}
                                {selectedMarket.status === 'OPEN' && selectedMarket.market_maker && (
                                    <div className="trading-form-section">
                                        <h3>Place Trade</h3>
                                        <form onSubmit={handleTradeSubmit} className="trade-form">
                                            <div className="form-group">
                                                <label>Position:</label>
                                                <select
                                                    value={tradeForm.position}
                                                    onChange={(e) => setTradeForm({
                                                        ...tradeForm,
                                                        position: e.target.value
                                                    })}
                                                >
                                                    <option value="LONG">LONG (Buy YES)</option>
                                                    <option value="SHORT">SHORT (Buy NO)</option>
                                                </select>
                                            </div>

                                            <div className="form-group">
                                                <label>Quantity:</label>
                                                <input
                                                    type="number"
                                                    min="1"
                                                    value={tradeForm.quantity}
                                                    onChange={(e) => setTradeForm({
                                                        ...tradeForm,
                                                        quantity: parseInt(e.target.value)
                                                    })}
                                                    required
                                                />
                                            </div>

                                            <div className="trade-pricing">
                                                <div className="pricing-info">
                                                    <div className="price-item">
                                                        <span className="label">Your Price (LONG):</span>
                                                        <span className="value">{formatCurrency(selectedMarket.market_maker_spread_high)}</span>
                                                    </div>
                                                    <div className="price-item">
                                                        <span className="label">Your Price (SHORT):</span>
                                                        <span className="value">{formatCurrency(selectedMarket.market_maker_spread_low)}</span>
                                                    </div>
                                                </div>
                                                
                                                <div className="total-cost">
                                                    <strong>
                                                        Total Cost: {formatCurrency(
                                                            (tradeForm.position === 'LONG' 
                                                                ? selectedMarket.market_maker_spread_high 
                                                                : selectedMarket.market_maker_spread_low) * tradeForm.quantity
                                                        )}
                                                    </strong>
                                                </div>
                                            </div>

                                            <button type="submit" className="btn btn-primary btn-large">
                                                Place {tradeForm.position} Trade
                                            </button>
                                        </form>
                                    </div>
                                )}

                                {selectedMarket.status === 'CLOSED' && (
                                    <div className="market-closed-message">
                                        <p>This market is closed for trading and awaiting settlement.</p>
                                    </div>
                                )}

                                {selectedMarket.status === 'SETTLED' && (
                                    <div className="market-settled-message">
                                        <h3>Market Settled</h3>
                                        <p>
                                            <strong>Outcome:</strong> {selectedMarket.final_outcome ? 'YES' : 'NO'}
                                        </p>
                                        <p>
                                            <strong>Settlement Price:</strong> {formatCurrency(selectedMarket.settlement_price)}
                                        </p>
                                        <p>
                                            <strong>Settled:</strong> {formatDateTime(selectedMarket.settled_at)}
                                        </p>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="no-market-selected">
                            <h2>Select a Market</h2>
                            <p>Choose a market from the list to view details and place trades.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Positions Section */}
            {positions.length > 0 && (
                <div className="positions-section">
                    <h2>Your Positions</h2>
                    <div className="positions-grid">
                        {positions.map(position => (
                            <div key={`${position.market_id}-${position.position}`} className="position-card">
                                <div className="position-header">
                                    <h3>{position.market_premise}</h3>
                                    <span className={`position-badge ${getPositionClass(position.position)}`}>
                                        {position.position}
                                    </span>
                                </div>
                                
                                <div className="position-details">
                                    <div className="detail-row">
                                        <span>Quantity:</span>
                                        <span>{position.total_quantity} units</span>
                                    </div>
                                    <div className="detail-row">
                                        <span>Avg Price:</span>
                                        <span>{formatCurrency(position.average_price)}</span>
                                    </div>
                                    <div className="detail-row">
                                        <span>Total Cost:</span>
                                        <span>{formatCurrency(position.total_cost)}</span>
                                    </div>
                                    {position.is_settled && (
                                        <>
                                            <div className="detail-row">
                                                <span>Settlement:</span>
                                                <span>{formatCurrency(position.settlement_amount)}</span>
                                            </div>
                                            <div className={`detail-row profit-loss ${getProfitLossClass(position.profit_loss)}`}>
                                                <span>P&L:</span>
                                                <span>{position.profit_loss >= 0 ? '+' : ''}{formatCurrency(position.profit_loss)}</span>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Trading; 