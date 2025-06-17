const API_BASE_URL = process.env.NODE_ENV === 'production' 
    ? 'https://salonis-mock-trading-app.azurewebsites.net' 
    : 'http://localhost:8000';

export default API_BASE_URL; 