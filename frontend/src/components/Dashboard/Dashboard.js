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
    const [bidAmount, setBidAmount] = useState('');
    const [selectedMarket, setSelectedMarket] = useState(null);
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

    const handleBid = async (marketId) => {
        if (!bidAmount) {
            setError('Please enter a bid amount');
            return;
        }

        try {
            await apiPost(`/api/market/${marketId}/bid/`, {
                amount: parseFloat(bidAmount)
            });
            setBidAmount('');
            setSelectedMarket(null);
            // Refresh data after successful bid
            const response = await apiGet('/api/market/');
            setMarkets(response);
        } catch (error) {
            console.error('Error placing bid:', error);
            handleApiError(error);
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
        <div className="dashboard">
            <div className="dashboard-header">
                <h1>Market Dashboard</h1>
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

            {userData && (
                <div className="user-info">
                    <h2>Welcome, {userData.username}!</h2>
                    <p>Balance: ${userData.balance || 0}</p>
                </div>
            )}

            <div className="markets-grid">
                {markets.map(market => (
                    <div key={market.id} className="market-card">
                        <h3>{market.premise}</h3>
                        <div className="market-details">
                            <p><strong>Status:</strong> 
                                <span 
                                    className={`status-badge ${getStatusColor(market.status)}`}
                                    style={{ backgroundColor: getStatusColor(market.status) }}
                                >
                                    {getStatusText(market.status)}
                                </span>
                            </p>
                            <p><strong>Opens:</strong> {formatDateTime(market.trading_open)}</p>
                            <p><strong>Closes:</strong> {formatDateTime(market.trading_close)}</p>
                            <p><strong>Current Price:</strong> ${market.current_price || 'N/A'}</p>
                        </div>
                        
                        {market.status === 'OPEN' && (
                            <div className="bid-section">
                                <input
                                    type="number"
                                    placeholder="Bid amount"
                                    value={selectedMarket === market.id ? bidAmount : ''}
                                    onChange={(e) => {
                                        setBidAmount(e.target.value);
                                        setSelectedMarket(market.id);
                                    }}
                                    className="form-input"
                                />
                                <button 
                                    onClick={() => handleBid(market.id)}
                                    className="btn btn-primary"
                                >
                                    Place Bid
                                </button>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {markets.length === 0 && !loading && (
                <div className="no-markets">
                    <p>No markets available at the moment.</p>
                </div>
            )}
        </div>
    );
};

export default Dashboard; 