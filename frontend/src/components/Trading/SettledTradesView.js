import React, { useState, useEffect, useCallback } from 'react';
import { apiGet } from '../../utils/apiUtils';
import { formatCurrency, formatDateTime } from '../../utils/dateUtils';
import './SettledTradesView.css';

const SettledTradesView = ({ marketId }) => {
    const [trades, setTrades] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showTrades, setShowTrades] = useState(false);

    const fetchSettledTrades = useCallback(async () => {
        try {
            setLoading(true);
            setError('');
            const response = await apiGet(`/api/market/${marketId}/settled-trades/`);
            setTrades(response.trades);
        } catch (err) {
            console.error('Error fetching settled trades:', err);
            setError('Failed to load trade details');
        } finally {
            setLoading(false);
        }
    }, [marketId]);

    useEffect(() => {
        if (showTrades && marketId) {
            fetchSettledTrades();
        }
    }, [showTrades, marketId, fetchSettledTrades]);

    const getPositionClass = (position) => {
        return position === 'BUY' ? 'position-long' : 'position-short';
    };

    const getProfitLossClass = (profitLoss) => {
        return profitLoss >= 0 ? 'profit' : 'loss';
    };

    return (
        <div className="settled-trades-view">
            <div className="trade-visibility-header">
                <h4>Public Trade Results</h4>
                <button
                    onClick={() => setShowTrades(!showTrades)}
                    className="btn btn-outline"
                >
                    {showTrades ? 'Hide' : 'Show'} All Trades ({trades.length})
                </button>
            </div>

            {showTrades && (
                <div className="settled-trades-content">
                    {loading && (
                        <div className="loading">Loading trade details...</div>
                    )}

                    {error && (
                        <div className="error-message">{error}</div>
                    )}

                    {!loading && !error && trades.length === 0 && (
                        <div className="no-trades">No trades found for this market.</div>
                    )}

                    {!loading && !error && trades.length > 0 && (
                        <div className="trades-table">
                            <div className="table-header">
                                <span>Trader</span>
                                <span>Position</span>
                                <span>Trade Price</span>
                                <span>Settlement Price</span>
                                <span>Profit/Loss</span>
                                <span>Trade Time</span>
                            </div>

                            {trades.map(trade => (
                                <div key={trade.id} className="table-row">
                                    <span className="trader-name">{trade.trader}</span>
                                    <span className={`position ${getPositionClass(trade.position)}`}>
                                        {trade.position === 'BUY' ? 'BUY' : 'SELL'}
                                    </span>
                                    <span>{formatCurrency(trade.trade_price)}</span>
                                    <span>{formatCurrency(trade.settlement_amount)}</span>
                                    <span className={`profit-loss ${getProfitLossClass(trade.profit_loss)}`}>
                                        {trade.profit_loss >= 0 ? '+' : ''}{formatCurrency(trade.profit_loss)}
                                        {trade.won !== null && (
                                            <span className={`win-indicator ${trade.won ? 'won' : 'lost'}`}>
                                                {trade.won ? ' ✓' : ' ✗'}
                                            </span>
                                        )}
                                    </span>
                                    <span className="trade-time">{formatDateTime(trade.trade_time)}</span>
                                </div>
                            ))}

                            <div className="trades-summary">
                                <p>
                                    <strong>Total Trades:</strong> {trades.length} |
                                    <strong> Winners:</strong> {trades.filter(t => t.won).length} |
                                    <strong> Losers:</strong> {trades.filter(t => !t.won).length}
                                </p>
                                <p className="transparency-note">
                                    📊 All trade details are publicly visible for settled markets to ensure transparency.
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default SettledTradesView;
