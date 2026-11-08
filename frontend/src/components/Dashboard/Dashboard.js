import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatDateTime } from '../../utils/dateUtils';
import { apiGet, apiPost, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import '../../styles/common.css';
import './Dashboard.css';

const sections = [
    { title: 'Active markets', statuses: ['OPEN'] },
    { title: 'Spread bidding', statuses: ['CREATED'] },
    { title: 'Completed markets', statuses: ['CLOSED', 'SETTLED'] },
];

export default function Dashboard() {
    const [markets, setMarkets] = useState([]);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        Promise.all([apiGet('/api/auth/user-profile/'), apiGet('/api/market/')])
            .then(([profile, list]) => { setUser(profile); setMarkets(list); })
            .catch(err => {
                if (shouldRedirectToLogin(err)) navigate('/auth');
                else setError(handleApiError(err));
            })
            .finally(() => setLoading(false));
    }, [navigate]);

    const trade = async (marketId, position) => {
        try {
            setError('');
            await apiPost(`/api/market/${marketId}/place_trade/`, { position });
            setMarkets(await apiGet('/api/market/'));
        } catch (err) {
            setError(handleApiError(err));
        }
    };

    if (loading) return <div className="loading-spinner">Loading dashboard...</div>;

    return <div className="dashboard-container">
        <header className="dashboard-header">
            <div><h1>Market dashboard</h1>{user && <p>Welcome, {user.username}. Balance: ${Number(user.balance).toFixed(2)}</p>}</div>
            <div className="header-actions">
                <button className="btn btn-primary" onClick={() => navigate('/markets')}>Market workspace</button>
                <button className="btn btn-outline" onClick={() => { localStorage.removeItem('token'); navigate('/auth'); }}>Log out</button>
            </div>
        </header>
        {error && <div className="error-message" role="alert">{error}</div>}
        <div className="dashboard-stats">
            {[
                ['Total markets', markets.length],
                ['Active markets', markets.filter(m => m.status === 'OPEN').length],
                ['Your positions', markets.filter(m => m.user_trade).length],
                ['Markets you make', markets.filter(m => m.status === 'OPEN' && m.market_maker_username === user?.username).length],
            ].map(([label, count]) => <div className="stat-card" key={label}><div className="stat-number">{count}</div><div className="stat-label">{label}</div></div>)}
        </div>
        {sections.map(({title, statuses}) => {
            const list = markets.filter(m => statuses.includes(m.status));
            if (!list.length) return null;
            return <section className="market-status-section" key={title}><h2>{title}</h2><div className="markets-grid">
                {list.map(market => <article className={`market-card ${market.status.toLowerCase()}`} key={market.id}>
                    <div className="market-header"><h3>{market.premise}</h3><span className="status-badge">{market.status}</span></div>
                    {market.status === 'OPEN' && <div className="market-info">
                        <p>Spread: {market.final_spread_low} – {market.final_spread_high}</p>
                        <p>Closes: {formatDateTime(market.trading_close)}</p>
                        {['buyers', 'sellers'].map(side => {
                            const group = market.position_display?.[side];
                            return <div key={side}>{side.toUpperCase()}: {group?.count > 7 ? group.count : group?.names.join(', ') || 'None'}</div>;
                        })}
                    </div>}
                    {market.status === 'CREATED' && <p>Bidding closes: {formatDateTime(market.spread_bidding_close_trading_open)}</p>}
                    {market.status === 'SETTLED' && <p>Outcome: {market.settlement_price}</p>}
                    {market.status === 'OPEN' && market.user_trade && <p>Your position: {market.user_trade.position} at {market.user_trade.price}</p>}
                    {market.status === 'OPEN' && market.can_user_trade?.can_trade && <div className="trade-buttons">
                        <button className="btn btn-success btn-small" onClick={() => trade(market.id, 'BUY')}>BUY {market.market_maker_spread_high}</button>
                        <button className="btn btn-danger btn-small" onClick={() => trade(market.id, 'SELL')}>SELL {market.market_maker_spread_low}</button>
                    </div>}
                    <button className="btn btn-secondary btn-small" onClick={() => navigate('/markets')}>View market</button>
                </article>)}
            </div></section>;
        })}
        {!markets.length && <p>No markets available.</p>}
    </div>;
}
