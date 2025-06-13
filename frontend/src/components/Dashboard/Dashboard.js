import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Dashboard.css';

const Dashboard = () => {
    const [userData, setUserData] = useState(null);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (!token) {
            navigate('/');
            return;
        }

        // Fetch user data
        const fetchUserData = async () => {
            try {
                const response = await axios.get('http://localhost:8000/api/auth/user-profile/', {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setUserData(response.data);
            } catch (error) {
                console.error('Error fetching user data:', error);
                setError('Error loading user data. Please try again.');
                if (error.response?.status === 401) {
                    localStorage.removeItem('token');
                    navigate('/');
                }
            }
        };

        fetchUserData();
    }, [navigate]);

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/');
    };

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
                <button onClick={handleLogout} className="logout-button">
                    Logout
                </button>
            </div>
            <div className="dashboard-content">
                <div className="dashboard-card">
                    <h2>Account Overview</h2>
                    <p>Email: {userData.email}</p>
                    <p>Account Status: {userData.is_verified ? 'Verified' : 'Pending Verification'}</p>
                    <p>Member Since: {new Date(userData.date_joined).toLocaleDateString()}</p>
                </div>
                <div className="dashboard-card">
                    <h2>Trading Features</h2>
                    <p>Coming soon...</p>
                </div>
            </div>
        </div>
    );
};

export default Dashboard; 