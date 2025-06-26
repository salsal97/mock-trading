import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders login form', () => {
  render(<App />);
  const welcomeText = screen.getByText(/welcome back/i);
  expect(welcomeText).toBeInTheDocument();
  
  const loginButton = screen.getByRole('button', { name: /login/i });
  expect(loginButton).toBeInTheDocument();
});

test('renders username and password fields', () => {
  render(<App />);
  const usernameInput = screen.getByLabelText(/username/i);
  expect(usernameInput).toBeInTheDocument();
  
  const passwordInput = screen.getByLabelText(/password/i);
  expect(passwordInput).toBeInTheDocument();
});
