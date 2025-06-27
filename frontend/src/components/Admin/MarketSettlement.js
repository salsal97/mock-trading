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
  const [settlementStep, setSettlementStep] = useState(1); // 1: set price, 2: preview, 3: execute
  const [settlementPrice, setSettlementPrice] = useState('');
  const [settlementPreview, setSettlementPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [reopenForm, setReopenForm] = useState({ showForm: false, newTradingClose: '' });
  const navigate = useNavigate();

  useEffect(() => {
    fetchMarkets();
  }, []);

  const fetchMarkets = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await apiGet('/api/market/');
      // Filter markets that can be settled (CLOSED or SETTLED status)
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

  const handleCloseTrading = async (marketId) => {
    try {
      setSubmitting(true);
      const response = await apiPost(`/api/market/${marketId}/close-trading/`);
      alert(response.message);
      fetchMarkets();
    } catch (error) {
      console.error('Error closing trading:', error);
      handleApiError(error);
      setError('Failed to close trading');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSetSettlementPrice = async (e) => {
    e.preventDefault();
    
    if (!selectedMarket) {
      setError('Please select a market first');
      return;
    }

    if (!settlementPrice) {
      setError('Settlement price is required');
      return;
    }

    const price = parseFloat(settlementPrice);
    if (price < 0.01 || price > 999999.99) {
      setError('Settlement price must be between 0.01 and 999999.99');
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      
      const response = await apiPost(`/api/market/${selectedMarket.id}/set-settlement-price/`, {
        price: price
      });

      alert(response.message);
      setSettlementStep(2);
      
      // Now get the preview
      await loadSettlementPreview();
      
    } catch (error) {
      console.error('Error setting settlement price:', error);
      handleApiError(error);
      setError('Failed to set settlement price');
    } finally {
      setSubmitting(false);
    }
  };

  const loadSettlementPreview = async () => {
    try {
      setSubmitting(true);
      const response = await apiGet(`/api/market/${selectedMarket.id}/settlement-preview/`);
      setSettlementPreview(response);
    } catch (error) {
      console.error('Error loading settlement preview:', error);
      handleApiError(error);
      setError('Failed to load settlement preview');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExecuteSettlement = async () => {
    if (!window.confirm('Are you sure you want to execute this settlement? This action cannot be undone and will update all user balances.')) {
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      
      const response = await apiPost(`/api/market/${selectedMarket.id}/execute-settlement/`);
      
      alert(`Settlement executed successfully! ${response.settlement_data.total_trades} trades settled.`);
      
      // Reset form and refresh markets
      resetSettlementForm();
      fetchMarkets();
      
    } catch (error) {
      console.error('Error executing settlement:', error);
      handleApiError(error);
      setError('Failed to execute settlement');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReopenTrading = async (e) => {
    e.preventDefault();
    
    if (!reopenForm.newTradingClose) {
      setError('New trading close time is required');
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      
      const response = await apiPost(`/api/market/${selectedMarket.id}/reopen-trading/`, {
        new_trading_close: reopenForm.newTradingClose
      });

      alert(response.message);
      setReopenForm({ showForm: false, newTradingClose: '' });
      fetchMarkets();
      
    } catch (error) {
      console.error('Error reopening trading:', error);
      handleApiError(error);
      setError('Failed to reopen trading');
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
      handleApiError(error);
      setError('Failed to run auto-settlement');
    }
  };

  const resetSettlementForm = () => {
    setSelectedMarket(null);
    setSettlementStep(1);
    setSettlementPrice('');
    setSettlementPreview(null);
    setError('');
  };

  const selectMarket = (market) => {
    setSelectedMarket(market);
    setSettlementStep(market.settlement_price ? 2 : 1);
    setSettlementPrice(market.settlement_price || '');
    setSettlementPreview(null);
    setError('');
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
              Auto-Close Markets
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
                  onClick={() => selectMarket(market)}
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
                      <span>Total trades:</span>
                      <span>{market.total_trades_count || 0}</span>
                    </div>
                    {market.market_maker && (
                      <div className="detail-row">
                        <span>Market Maker:</span>
                        <span>{market.market_maker_username}</span>
                      </div>
                    )}
                    {market.settlement_price && (
                      <div className="detail-row">
                        <span>Settlement Price:</span>
                        <span>{formatCurrency(market.settlement_price)}</span>
                      </div>
                    )}
                    {market.status === 'SETTLED' && (
                      <div className="detail-row">
                        <span>Settled:</span>
                        <span>{formatDateTime(market.settled_at)}</span>
                      </div>
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
                <h2>Settlement Workflow</h2>
                <div className="market-info">
                  <h3>{selectedMarket.premise}</h3>
                  
                  <div className="market-stats">
                    <div className="stat-item">
                      <span className="label">Status:</span>
                      <span className={`value status-${selectedMarket.status.toLowerCase()}`}>
                        {getStatusText(selectedMarket.status)}
                      </span>
                    </div>
                    <div className="stat-item">
                      <span className="label">Total Trades:</span>
                      <span className="value">{selectedMarket.total_trades_count || 0}</span>
                    </div>
                    <div className="stat-item">
                      <span className="label">Market Maker:</span>
                      <span className="value">{selectedMarket.market_maker_username || 'None'}</span>
                    </div>
                  </div>
                </div>

                {/* Settlement Steps */}
                <div className="settlement-steps">
                  <div className={`step ${settlementStep >= 1 ? 'active' : ''} ${selectedMarket.settlement_price ? 'completed' : ''}`}>
                    <span className="step-number">1</span>
                    <span>Set Settlement Price</span>
                  </div>
                  <div className={`step ${settlementStep >= 2 ? 'active' : ''} ${selectedMarket.settlement_preview_calculated ? 'completed' : ''}`}>
                    <span className="step-number">2</span>
                    <span>Preview Settlement</span>
                  </div>
                  <div className={`step ${settlementStep >= 3 ? 'active' : ''} ${selectedMarket.status === 'SETTLED' ? 'completed' : ''}`}>
                    <span className="step-number">3</span>
                    <span>Execute Settlement</span>
                  </div>
                </div>

                {selectedMarket.status === 'SETTLED' ? (
                  <div className="already-settled">
                    <h3>✅ Market Already Settled</h3>
                    <div className="settled-details">
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
                ) : selectedMarket.status === 'CLOSED' ? (
                  <>
                    {/* Step 1: Set Settlement Price */}
                    {settlementStep === 1 && (
                      <div className="settlement-step-content">
                        <h3>Step 1: Set Settlement Price</h3>
                        <form onSubmit={handleSetSettlementPrice} className="settlement-form">
                          <div className="form-group">
                            <label>Settlement Price:</label>
                            <input
                              type="number"
                              min="0.01"
                              max="999999.99"
                              step="0.01"
                              value={settlementPrice}
                              onChange={(e) => setSettlementPrice(e.target.value)}
                              placeholder="Enter final settlement value (0.01 - 999999.99)"
                              required
                            />
                            <small className="form-help">
                              This is the final market value used to calculate all profit/loss settlements.
                            </small>
                          </div>

                          <button 
                            type="submit" 
                            className="btn btn-primary"
                            disabled={submitting}
                          >
                            {submitting ? 'Setting Price...' : 'Set Settlement Price'}
                          </button>
                        </form>
                      </div>
                    )}

                    {/* Step 2: Preview Settlement */}
                    {settlementStep === 2 && (
                      <div className="settlement-step-content">
                        <h3>Step 2: Settlement Preview</h3>
                        
                        {!settlementPreview ? (
                          <div className="loading-preview">
                            <button 
                              onClick={loadSettlementPreview}
                              className="btn btn-primary"
                              disabled={submitting}
                            >
                              {submitting ? 'Loading Preview...' : 'Calculate Settlement Preview'}
                            </button>
                          </div>
                        ) : (
                          <div className="settlement-preview">
                            <div className="preview-summary">
                              <h4>Settlement Summary</h4>
                              <div className="summary-item">
                                <span>Settlement Price:</span>
                                <span>{formatCurrency(settlementPreview.settlement_price)}</span>
                              </div>
                              <div className="summary-item">
                                <span>Total Trades:</span>
                                <span>{settlementPreview.total_trades}</span>
                              </div>
                              <div className="summary-item">
                                <span>Market Maker Impact:</span>
                                <span className={settlementPreview.market_maker_impact >= 0 ? 'positive' : 'negative'}>
                                  {formatCurrency(settlementPreview.market_maker_impact)}
                                </span>
                              </div>
                            </div>

                            <div className="trades-preview">
                              <h4>Individual Trade Settlements</h4>
                              <div className="trades-table">
                                <div className="table-header">
                                  <span>User</span>
                                  <span>Position</span>
                                  <span>Trade Price</span>
                                  <span>Settlement Price</span>
                                  <span>Profit/Loss</span>
                                </div>
                                {settlementPreview.trades.map(trade => (
                                  <div key={trade.trade_id} className="table-row">
                                    <span>{trade.username}</span>
                                    <span className={`position ${trade.position.toLowerCase()}`}>
                                      {trade.position}
                                    </span>
                                    <span>{formatCurrency(trade.trade_price)}</span>
                                    <span>{formatCurrency(trade.settlement_price)}</span>
                                    <span className={trade.profit_loss >= 0 ? 'profit' : 'loss'}>
                                      {formatCurrency(trade.profit_loss)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </div>

                            <div className="preview-actions">
                              <button 
                                onClick={() => setSettlementStep(1)}
                                className="btn btn-secondary"
                              >
                                ← Back to Price Setting
                              </button>
                              <button 
                                onClick={handleExecuteSettlement}
                                className="btn btn-danger"
                                disabled={submitting}
                              >
                                {submitting ? 'Executing...' : 'Confirm & Execute Settlement'}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Reopen Trading Option */}
                    <div className="reopen-section">
                      <h4>Alternative Actions</h4>
                      {!reopenForm.showForm ? (
                        <button 
                          onClick={() => setReopenForm({ showForm: true, newTradingClose: '' })}
                          className="btn btn-warning"
                          disabled={selectedMarket.settlement_price !== null}
                        >
                          Reopen Trading
                        </button>
                      ) : (
                        <form onSubmit={handleReopenTrading} className="reopen-form">
                          <div className="form-group">
                            <label>New Trading Close Time:</label>
                            <input
                              type="datetime-local"
                              value={reopenForm.newTradingClose}
                              onChange={(e) => setReopenForm({
                                ...reopenForm,
                                newTradingClose: e.target.value
                              })}
                              required
                            />
                          </div>
                          <div className="form-actions">
                            <button type="submit" className="btn btn-warning" disabled={submitting}>
                              {submitting ? 'Reopening...' : 'Reopen Trading'}
                            </button>
                            <button 
                              type="button" 
                              onClick={() => setReopenForm({ showForm: false, newTradingClose: '' })}
                              className="btn btn-secondary"
                            >
                              Cancel
                            </button>
                          </div>
                        </form>
                      )}
                      {selectedMarket.settlement_price !== null && (
                        <small className="warning">Cannot reopen trading after settlement price has been set</small>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="market-not-ready">
                    <h3>Market Not Ready for Settlement</h3>
                    <p>This market must be in CLOSED status before it can be settled.</p>
                    {selectedMarket.status === 'OPEN' && (
                      <button 
                        onClick={() => handleCloseTrading(selectedMarket.id)}
                        className="btn btn-danger"
                        disabled={submitting}
                      >
                        {submitting ? 'Closing...' : 'Close Trading Manually'}
                      </button>
                    )}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="no-market-selected">
              <h2>Select a Market</h2>
              <p>Choose a market from the list to view settlement options.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MarketSettlement; 