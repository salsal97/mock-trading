import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime } from '../../utils/dateUtils';
import { getPositionClass, getTradeStatusText } from '../../utils/marketUtils';
import { apiGet, apiPost, apiDelete, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Trading.css';

const Trading = () => {
    const [markets, setMarkets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [tradingMarket, setTradingMarket] = useState(null);
    const [tradeForm, setTradeForm] = useState({
        position: 'LONG',
        price: '',
        quantity: 1
    });
    const [submitting, setSubmitting] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        fetchTradingData();
    }, []);

    const fetchTradingData = async () => {
        try {
            setLoading(true);
            setError('');
            
            const marketsData = await apiGet('/api/market/?status=OPEN');
            setMarkets(marketsData);
        } catch (error) {
            console.error('Error fetching trading data:', error);
            const errorMessage = handleApiError(error);
            setError(errorMessage);
            
            if (shouldRedirectToLogin(error)) {
                navigate('/login');
            }
        } finally {
            setLoading(false);
        }
    };

    const openTradeModal = (market) => {
        setTradingMarket(market);
        
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
        setTradingMarket(null);
        setTradeForm({
            position: 'LONG',
            price: '',
            quantity: 1
        });
        setError('');
    };

    const handleTradeSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);
        setError('');

        try {
            const response = await apiPost(
                `/api/market/${tradingMarket.id}/place_trade/`,
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
        } finally {
            setSubmitting(false);
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

    if (loading) {
        return <div className="loading">Loading trading data...</div>;
    }

    return (
        <div className="trading-container">
            <div className="trading-header">
                <h1>Trading Dashboard</h1>
                <button 
                    className="back-button"
                    onClick={() => navigate('/dashboard')}
                >
                    Back to Dashboard
                </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            {/* Open Markets Section */}
            <div className="markets-section">
                <h2>Open Markets</h2>
                {markets.length === 0 ? (
                    <div className="no-markets">No markets are currently open for trading.</div>
                ) : (
                    <div className="markets-grid">
                        {markets.map(market => (
                            <div key={market.id} className="market-card">
                                <div className="market-header">
                                    <h3>{market.premise}</h3>
                                    <div className="market-spread">
                                        Spread: {market.current_spread_display}
                                    </div>
                                </div>
                                
                                <div className="market-details">
                                    <div className="market-info">
                                        <span>Unit Price: ${market.unit_price}</span>
                                        <span>Trading closes: {formatDateTime(market.trading_close)}</span>
                                    </div>
                                    
                                    <div className="trade-stats">
                                        <span className="long-count">Long: {market.long_trades_count}</span>
                                        <span className="short-count">Short: {market.short_trades_count}</span>
                                    </div>
                                    
                                    <div className={`trade-status ${market.user_trade ? getPositionClass(market.user_trade.position) : ''}`}>
                                        {getTradeStatusText(market)}
                                    </div>
                                </div>
                                
                                <div className="market-actions">
                                    {market.is_trading_active && market.can_user_trade.can_trade && (
                                        <button 
                                            className="trade-button"
                                            onClick={() => openTradeModal(market)}
                                        >
                                            {market.user_trade ? 'Edit Trade' : 'Place Trade'}
                                        </button>
                                    )}
                                    
                                    {market.user_trade && market.is_trading_active && (
                                        <button 
                                            className="cancel-button"
                                            onClick={() => handleCancelTrade(market.id)}
                                        >
                                            Cancel Trade
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Trade Modal */}
            {tradingMarket && (
                <div className="modal-overlay">
                    <div className="trade-modal">
                        <div className="modal-header">
                            <h2>{tradingMarket.user_trade ? 'Edit Trade' : 'Place Trade'}</h2>
                            <button className="close-button" onClick={closeTradeModal}>×</button>
                        </div>
                        
                        <div className="modal-content">
                            <div className="market-info">
                                <h3>{tradingMarket.premise}</h3>
                                <p>Current Spread: {tradingMarket.current_spread_display}</p>
                                <p>Trading closes: {formatDateTime(tradingMarket.trading_close)}</p>
                            </div>
                            
                            {error && <div className="error-message">{error}</div>}
                            
                            <form onSubmit={handleTradeSubmit} className="trade-form">
                                <div className="form-group">
                                    <label>Position:</label>
                                    <div className="position-buttons">
                                        <button
                                            type="button"
                                            className={`position-btn ${tradeForm.position === 'LONG' ? 'active long' : ''}`}
                                            onClick={() => setTradeForm({...tradeForm, position: 'LONG'})}
                                        >
                                            Long
                                        </button>
                                        <button
                                            type="button"
                                            className={`position-btn ${tradeForm.position === 'SHORT' ? 'active short' : ''}`}
                                            onClick={() => setTradeForm({...tradeForm, position: 'SHORT'})}
                                        >
                                            Short
                                        </button>
                                    </div>
                                </div>
                                
                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Price:</label>
                                        <input
                                            type="number"
                                            step="0.01"
                                            value={tradeForm.price}
                                            onChange={(e) => setTradeForm({...tradeForm, price: e.target.value})}
                                            required
                                            min="0.01"
                                        />
                                        <small>
                                            {tradeForm.position === 'LONG' 
                                                ? `Minimum: ${tradingMarket.final_spread_high || 'N/A'}`
                                                : `Maximum: ${tradingMarket.final_spread_low || 'N/A'}`
                                            }
                                        </small>
                                    </div>
                                    
                                    <div className="form-group">
                                        <label>Quantity:</label>
                                        <input
                                            type="number"
                                            value={tradeForm.quantity}
                                            onChange={(e) => setTradeForm({...tradeForm, quantity: parseInt(e.target.value)})}
                                            required
                                            min="1"
                                        />
                                    </div>
                                </div>
                                
                                <div className="total-value">
                                    <strong>Total Value: ${(parseFloat(tradeForm.price || 0) * parseInt(tradeForm.quantity || 1)).toFixed(2)}</strong>
                                </div>
                                
                                <div className="form-actions">
                                    <button 
                                        type="submit" 
                                        className="submit-button"
                                        disabled={submitting}
                                    >
                                        {submitting ? 'Processing...' : (tradingMarket.user_trade ? 'Update Trade' : 'Place Trade')}
                                    </button>
                                    <button 
                                        type="button" 
                                        className="cancel-button"
                                        onClick={closeTradeModal}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Trading; 