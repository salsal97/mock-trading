import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './components/Auth/Auth';
import Dashboard from './components/Dashboard/Dashboard';
import AdminLanding from './components/Admin/AdminLanding';
import UserManagement from './components/Admin/UserManagement';
import MarketManagement from './components/Admin/MarketManagement';
import MarketSettlement from './components/Admin/MarketSettlement';
import Trading from './components/Trading/Trading';
import TradeHistory from './components/Trading/TradeHistory';
import './styles/common.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/admin" element={<AdminLanding />} />
          <Route path="/admin/users" element={<UserManagement />} />
          <Route path="/admin/markets" element={<MarketManagement />} />
          <Route path="/admin/settlement" element={<MarketSettlement />} />
          <Route path="/trading" element={<Trading />} />
          <Route path="/trade-history" element={<TradeHistory />} />
          <Route path="/" element={<Navigate to="/auth" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
 