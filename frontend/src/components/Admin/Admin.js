import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, handleApiError, shouldRedirectToLogin } from '../../utils/apiUtils';
import './Admin.css';

const Admin = () => {
  const [isAdmin, setIsAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const verifyAdminStatus = async () => {
      try {
        setIsLoading(true);
        const response = await apiGet('/api/auth/verify-admin/');
        // Admin verification successful
        setIsAdmin(true);
      } catch (error) {
        console.error('Admin verification failed:', error);
        if (shouldRedirectToLogin(error)) {
          navigate('/auth');
          return;
        }
        handleApiError(error);
        setIsAdmin(false);
      } finally {
        setIsLoading(false);
      }
    };

    verifyAdminStatus();
  }, [navigate]);

  if (isLoading) {
    return (
      <div className="admin-container">
        <div className="loading">Verifying admin access...</div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="admin-container">
        <div className="error">Access denied. Admin privileges required.</div>
      </div>
    );
  }

  return (
    <div className="admin-container">
      <h1>Admin Dashboard</h1>
      <div className="admin-nav">
        <button onClick={() => navigate('/admin/users')}>Manage Users</button>
        <button onClick={() => navigate('/admin/markets')}>Manage Markets</button>
        <button onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
      </div>
    </div>
  );
};

export default Admin; 