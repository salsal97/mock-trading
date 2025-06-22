import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime, formatCurrency } from '../../utils/dateUtils';
import { getStatusBadgeClass, getStatusText } from '../../utils/marketUtils';
import { apiGet, apiPost, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './MarketSettlement.css';

const MarketSettlement = () => {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [settlementForm, setSettlementForm] = useState({
    outcome: true, // true for YES, false for NO
    settlementPrice: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchMarkets();
  }, []);

  const fetchMarkets = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await apiGet('/api/market/');
      // Filter markets that can be settled (CLOSED status)
      const settleableMarkets = response.filter(market => 
        market.status === 'CLOSED' || market.status === 'SETTLED'
      );
      setMarkets(settleableMarkets);
    } catch (error) {
      console.error('Error fetching markets:', error);
      if (shouldRedirectToLogin(error)) {
        navigate('/auth');
        return;
      }
      handleApiError(error);
      setError('Failed to load markets');
    } finally {
      setLoading(false);
    }
  };

  const handleSettleMarket = async (e) => {
    e.preventDefault();
    
    if (!selectedMarket) {
      setError('Please select a market first');
      return;
    }

    if (selectedMarket.status === 'SETTLED') {
      setError('Market is already settled');
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      
      const response = await apiPost(`/api/market/${selectedMarket.id}/settle/`, {
        outcome: settlementForm.outcome,
        settlement_price: settlementForm.settlementPrice ? parseFloat(settlementForm.settlementPrice) : null
      });

      alert(`Market settled successfully! ${response.total_trades_settled} trades were processed.`);
      
      // Reset form and refresh markets
      setSelectedMarket(null);
      setSettlementForm({ outcome: true, settlementPrice: '' });
      fetchMarkets();
      
    } catch (error) {
      console.error('Error settling market:', error);
      if (shouldRedirectToLogin(error)) {
        navigate('/auth');
        return;
      }
      handleApiError(error);
      setError('Failed to settle market');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAutoSettle = async () => {
    try {
      setError('');
      
      const response = await apiPost('/api/market/auto-settle/');
      alert(`Auto-settlement completed. ${response.markets_closed} markets were closed.`);
      fetchMarkets();
      
    } catch (error) {
      console.error('Error in auto-settlement:', error);
      if (shouldRedirectToLogin(error)) {
        navigate('/auth');
        return;
      }
      handleApiError(error);
      setError('Failed to run auto-settlement');
    }
  };

  if (loading) {
    return (
      <div className="market-settlement">
        <div className="loading-spinner">Loading markets...</div>
      </div>
    );
  }

  return (
    <div className="market-settlement">
      <div className="settlement-header">
        <div className="header-content">
          <h1>Market Settlement</h1>
          <div className="header-actions">
            <button 
              onClick={handleAutoSettle}
              className="btn btn-secondary"
            >
              Run Auto-Settlement
            </button>
            <button 
              onClick={() => navigate('/admin')}
              className="btn btn-primary"
            >
              Back to Admin
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="settlement-layout">
        {/* Markets List */}
        <div className="markets-section">
          <h2>Markets Ready for Settlement</h2>
          {markets.length === 0 ? (
            <div className="no-markets">
              <p>No markets are ready for settlement.</p>
              <p>Markets must be in CLOSED status to be settled.</p>
            </div>
          ) : (
            <div className="markets-list">
              {markets.map(market => (
                <div 
                  key={market.id} 
                  className={`market-card ${selectedMarket?.id === market.id ? 'selected' : ''} ${market.status === 'SETTLED' ? 'settled' : ''}`}
                  onClick={() => setSelectedMarket(market)}
                >
                  <div className="market-header">
                    <h3>{market.premise}</h3>
                    <span className={getStatusBadgeClass(market.status)}>
                      {getStatusText(market.status)}
                    </span>
                  </div>
                  
                  <div className="market-details">
                    <div className="detail-row">
                      <span>Trading closed:</span>
                      <span>{formatDateTime(market.trading_close)}</span>
                    </div>
                    <div className="detail-row">
                      <span>Resolution date:</span>
                      <span>{formatDateTime(market.resolution_date)}</span>
                    </div>
                    {market.market_maker && (
                      <div className="detail-row">
                        <span>Market Maker:</span>
                        <span>{market.market_maker_username}</span>
                      </div>
                    )}
                    {market.status === 'SETTLED' && (
                      <>
                        <div className="detail-row">
                          <span>Final Outcome:</span>
                          <span className={`outcome ${market.final_outcome ? 'yes' : 'no'}`}>
                            {market.final_outcome ? 'YES' : 'NO'}
                          </span>
                        </div>
                        <div className="detail-row">
                          <span>Settlement Price:</span>
                          <span>{formatCurrency(market.settlement_price)}</span>
                        </div>
                        <div className="detail-row">
                          <span>Settled:</span>
                          <span>{formatDateTime(market.settled_at)}</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Settlement Panel */}
        <div className="settlement-panel">
          {selectedMarket ? (
            <>
              <div className="selected-market">
                <h2>Settle Market</h2>
                <div className="market-info">
                  <h3>{selectedMarket.premise}</h3>
                  <p className="market-description">{selectedMarket.description}</p>
                  
                  <div className="market-stats">
                    <div className="stat-item">
                      <span className="label">Status:</span>
                      <span className={`value status-${selectedMarket.status.toLowerCase()}`}>
                        {getStatusText(selectedMarket.status)}
                      </span>
                    </div>
                    <div className="stat-item">
                      <span className="label">Trading Closed:</span>
                      <span className="value">{formatDateTime(selectedMarket.trading_close)}</span>
                    </div>
                    <div className="stat-item">
                      <span className="label">Resolution Date:</span>
                      <span className="value">{formatDateTime(selectedMarket.resolution_date)}</span>
                    </div>
                  </div>
                </div>

                {selectedMarket.status === 'CLOSED' ? (
                  <div className="settlement-form-section">
                    <h3>Settlement Details</h3>
                    <form onSubmit={handleSettleMarket} className="settlement-form">
                      <div className="form-group">
                        <label>Market Outcome:</label>
                        <div className="outcome-options">
                          <label className="radio-option">
                            <input
                              type="radio"
                              name="outcome"
                              checked={settlementForm.outcome === true}
                              onChange={() => setSettlementForm({
                                ...settlementForm,
                                outcome: true
                              })}
                            />
                            <span className="radio-label yes">YES - Market resolves true</span>
                          </label>
                          <label className="radio-option">
                            <input
                              type="radio"
                              name="outcome"
                              checked={settlementForm.outcome === false}
                              onChange={() => setSettlementForm({
                                ...settlementForm,
                                outcome: false
                              })}
                            />
                            <span className="radio-label no">NO - Market resolves false</span>
                          </label>
                        </div>
                      </div>

                      <div className="form-group">
                        <label>Settlement Price (optional):</label>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.01"
                          value={settlementForm.settlementPrice}
                          onChange={(e) => setSettlementForm({
                            ...settlementForm,
                            settlementPrice: e.target.value
                          })}
                          placeholder="Leave empty to use market maker spread price"
                        />
                        <small className="form-help">
                          If not specified, will use {settlementForm.outcome ? 'high' : 'low'} spread price from market maker
                        </small>
                      </div>

                      <div className="settlement-preview">
                        <h4>Settlement Preview</h4>
                        <div className="preview-details">
                          <div className="preview-item">
                            <span>Outcome:</span>
                            <span className={`outcome ${settlementForm.outcome ? 'yes' : 'no'}`}>
                              {settlementForm.outcome ? 'YES' : 'NO'}
                            </span>
                          </div>
                          <div className="preview-item">
                            <span>Winning Position:</span>
                            <span>{settlementForm.outcome ? 'LONG' : 'SHORT'}</span>
                          </div>
                          <div className="preview-item">
                            <span>Settlement Price:</span>
                            <span>
                              {settlementForm.settlementPrice 
                                ? formatCurrency(parseFloat(settlementForm.settlementPrice))
                                : `Market Maker ${settlementForm.outcome ? 'High' : 'Low'} Price`
                              }
                            </span>
                          </div>
                        </div>
                      </div>

                      <button 
                        type="submit" 
                        className="btn btn-danger btn-large"
                        disabled={submitting}
                      >
                        {submitting ? 'Settling Market...' : 'Settle Market'}
                      </button>
                    </form>
                  </div>
                ) : (
                  <div className="already-settled">
                    <h3>Market Already Settled</h3>
                    <div className="settled-details">
                      <div className="settled-item">
                        <span>Final Outcome:</span>
                        <span className={`outcome ${selectedMarket.final_outcome ? 'yes' : 'no'}`}>
                          {selectedMarket.final_outcome ? 'YES' : 'NO'}
                        </span>
                      </div>
                      <div className="settled-item">
                        <span>Settlement Price:</span>
                        <span>{formatCurrency(selectedMarket.settlement_price)}</span>
                      </div>
                      <div className="settled-item">
                        <span>Settled At:</span>
                        <span>{formatDateTime(selectedMarket.settled_at)}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="no-market-selected">
              <h2>Select a Market</h2>
              <p>Choose a market from the list to view settlement details.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MarketSettlement; 