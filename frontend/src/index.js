import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Remove any worker installed by older builds so it cannot serve stale bundles.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistration().then(registration => registration?.unregister());
}
