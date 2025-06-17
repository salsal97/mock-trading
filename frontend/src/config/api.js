// API Configuration with explicit environment detection
const isProduction = process.env.NODE_ENV === 'production';
const isDevelopment = process.env.NODE_ENV === 'development';

console.log('Environment Detection:', {
    NODE_ENV: process.env.NODE_ENV,
    isProduction,
    isDevelopment
});

const API_BASE_URL = isProduction 
    ? 'https://salonis-mock-trading-app.azurewebsites.net' 
    : 'http://localhost:8000';

console.log('API_BASE_URL selected:', API_BASE_URL);

export default API_BASE_URL; 