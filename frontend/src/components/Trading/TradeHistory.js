import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime } from '../../utils/dateUtils';
import { getPositionClass } from '../../utils/marketUtils';
import { apiGet, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './TradeHistory.css';

const TradeHistory = () => {
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all'); // all, settled, active
  const navigate = useNavigate();

  useEffect(() => {
    fetchTradeHistory();
  }, []);

  const fetchTradeHistory = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await apiGet('/api/market/trade-history/');
      setTrades(response.trades);
      setSummary({
        totalTrades: response.total_trades,
        settledTrades: response.settled_trades,
        totalProfitLoss: response.total_profit_loss
      });
    } catch (error) {
      console.error('Error fetching trade history:', error);
      if (shouldRedirectToLogin(error)) {
        navigate('/auth');
        return;
      }
      handleApiError(error);
      setError('Failed to load trade history');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const getFilteredTrades = () => {
    switch (filter) {
      case 'settled':
        return trades.filter(trade => trade.is_settled);
      case 'active':
        return trades.filter(trade => !trade.is_settled);
      default:
        return trades;
    }
  };

  const getProfitLossClass = (profitLoss) => {
    if (profitLoss > 0) return 'profit';
    if (profitLoss < 0) return 'loss';
    return 'neutral';
  };

  if (loading) {
    return (
      <div className="trade-history">
        <div className="loading-spinner">Loading trade history...</div>
      </div>
    );
  }

  const filteredTrades = getFilteredTrades();

  return (
    <div className="trade-history">
      <div className="trade-history-header">
        <div className="header-content">
          <h1>Trade History</h1>
          <button 
            onClick={() => navigate('/trading')} 
            className="btn btn-secondary"
          >
            Back to Trading
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Summary Cards */}
      <div className="summary-section">
        <div className="summary-card">
          <h3>Total Trades</h3>
          <div className="summary-number">{summary.totalTrades}</div>
        </div>
        <div className="summary-card">
          <h3>Settled Trades</h3>
          <div className="summary-number">{summary.settledTrades}</div>
        </div>
        <div className={`summary-card profit-loss ${getProfitLossClass(summary.totalProfitLoss)}`}>
          <h3>Total P&L</h3>
          <div className="summary-number">{formatCurrency(summary.totalProfitLoss || 0)}</div>
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="filter-section">
        <button 
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          All Trades ({trades.length})
        </button>
        <button 
          className={`filter-btn ${filter === 'active' ? 'active' : ''}`}
          onClick={() => setFilter('active')}
        >
          Active ({trades.filter(t => !t.is_settled).length})
        </button>
        <button 
          className={`filter-btn ${filter === 'settled' ? 'active' : ''}`}
          onClick={() => setFilter('settled')}
        >
          Settled ({trades.filter(t => t.is_settled).length})
        </button>
      </div>

      {/* Trade Cards */}
      <div className="trades-grid">
        {filteredTrades.length === 0 ? (
          <div className="no-trades">
            <p>No trades found for the selected filter.</p>
          </div>
        ) : (
          filteredTrades.map(trade => (
            <div key={trade.id} className={`trade-card ${trade.is_settled ? 'settled' : 'active'}`}>
              <div className="trade-card-header">
                <div className="market-info">
                  <h3 className="market-premise">{trade.market.premise}</h3>
                  <span className={`market-status status-${trade.market.status.toLowerCase()}`}>
                    {trade.market.status}
                  </span>
                </div>
                <div className={`position-badge ${getPositionClass(trade.position)}`}>
                  {trade.position}
                </div>
              </div>

              <div className="trade-details">
                <div className="detail-row">
                  <span className="label">Position Size:</span>
                  <span className="value">{trade.quantity} units</span>
                </div>
                <div className="detail-row">
                  <span className="label">Entry Price:</span>
                  <span className="value">{formatCurrency(trade.price)}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Total Cost:</span>
                  <span className="value">{formatCurrency(trade.total_cost)}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Trade Date:</span>
                  <span className="value">{formatDateTime(trade.created_at)}</span>
                </div>
              </div>

              {trade.is_settled ? (
                <div className="settlement-section">
                  <div className="settlement-header">
                    <h4>Settlement Details</h4>
                    <span className={`outcome-badge ${trade.won ? 'won' : 'lost'}`}>
                      {trade.won ? 'WON' : 'LOST'}
                    </span>
                  </div>
                  
                  <div className="settlement-details">
                    <div className="detail-row">
                      <span className="label">Market Outcome:</span>
                      <span className="value">
                        {trade.market_outcome ? 'YES' : 'NO'}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="label">Settlement Amount:</span>
                      <span className="value">{formatCurrency(trade.settlement_amount)}</span>
                    </div>
                    <div className="detail-row profit-loss-row">
                      <span className="label">Profit/Loss:</span>
                      <span className={`value profit-loss ${getProfitLossClass(trade.profit_loss)}`}>
                        {trade.profit_loss >= 0 ? '+' : ''}{formatCurrency(trade.profit_loss)}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="label">Settled:</span>
                      <span className="value">{formatDateTime(trade.settled_at)}</span>
                    </div>
                  </div>

                  <div className={`settlement-summary ${getProfitLossClass(trade.profit_loss)}`}>
                    <div className="summary-text">
                      {trade.profit_loss > 0 
                        ? `You made ${formatCurrency(trade.profit_loss)} profit!`
                        : trade.profit_loss < 0
                        ? `You lost ${formatCurrency(Math.abs(trade.profit_loss))}`
                        : 'Break even'
                      }
                    </div>
                  </div>
                </div>
              ) : (
                <div className="active-trade-section">
                  <div className="status-indicator">
                    <span className="status-dot active"></span>
                    <span>Position Active</span>
                  </div>
                  <p className="status-text">
                    This trade will be settled when the market closes and the outcome is determined.
                  </p>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default TradeHistory; 