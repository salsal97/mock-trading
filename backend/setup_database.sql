-- Database setup script for Mock Trading Platform
-- Run this after installing PostgreSQL

-- Create database
CREATE DATABASE mock_trading;

-- Create user (if needed)
-- CREATE USER postgres WITH PASSWORD 'password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mock_trading TO postgres;

-- Connect to the database
\c mock_trading;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO postgres; 