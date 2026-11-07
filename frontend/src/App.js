import MarketWorkspace from './components/Trading/MarketWorkspace';
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Auth from './components/Auth/Auth';
import Dashboard from './components/Dashboard/Dashboard';
import './styles/common.css';

function App() {
  return (
    <Router future={{v7_startTransition: true, v7_relativeSplatPath: true}}>
      <div className="App">
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route path="/markets" element={<MarketWorkspace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/" element={<Navigate to="/auth" />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
 