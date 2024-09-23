import React, { useState, useEffect } from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import UserManagementScreen from './pages/UserManagementScreen';
import RoleProtectedRoute from './components/RoleProtectedRoute';

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');

  if (!token) {
    return <Navigate to="/login" />;
  }

  return children;
};

function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Dashboard - Protected Content</div>
            </ProtectedRoute>
          }
        />
        <Route
          path="/user-management"
          element={
            <RoleProtectedRoute allowedRoles={['Admin']}>
              <UserManagementScreen />
            </RoleProtectedRoute>
          }
        />
      </Routes>
    </>
  );
}

export default App;