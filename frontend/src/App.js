import React from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import NewDomainPage from './pages/NewDomainPage';
import DomainPage from './pages/DomainPage';
import DomainConfigPage from './pages/DomainConfigPage';  // Import DomainConfigPage
import UserConfigPage from './pages/UserConfigPage';  // Import UserConfigPage

import { AuthProvider } from './context/AuthContext';

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');

  if (!token) {
    return <Navigate to="/login" />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/new-domain"
          element={
            <ProtectedRoute>
              <NewDomainPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/domain/:domain_id"
          element={
            <ProtectedRoute>
              <DomainPage />
            </ProtectedRoute>
          }
        />
        {/* Add Domain Config Page Route */}
        <Route
          path="/domains/:domain_id/config"
          element={
            <ProtectedRoute>
              <DomainConfigPage />
            </ProtectedRoute>
          }
        />
        {/* Add User Config Page Route */}
        <Route
          path="/user/config"
          element={
            <ProtectedRoute>
              <UserConfigPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;