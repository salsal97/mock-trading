import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './components/Auth/Auth';
import Dashboard from './components/Dashboard/Dashboard';
import Trading from './components/Trading/Trading';
import Admin from './components/Admin/Admin';
import AdminLanding from './components/Admin/AdminLanding';
import MarketManagement from './components/Admin/MarketManagement';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Auth />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/trading" element={<Trading />} />
          <Route path="/admin" element={<AdminLanding />} />
          <Route path="/admin/users" element={<Admin />} />
          <Route path="/admin/market" element={<MarketManagement />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
 