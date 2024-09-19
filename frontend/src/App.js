import React from 'react';
import { Route, Routes } from 'react-router-dom';
import { useAuth0 } from '@auth0/auth0-react';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import UserManagementScreen from './pages/UserManagementScreen';
import RoleProtectedRoute from './components/RoleProtectedRoute';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();

  if (isLoading) {
    return <div>Loading...</div>; // You can replace this with a proper loading spinner or component
  }

  if (!isAuthenticated) {
    loginWithRedirect();
    return null; // Return null while redirecting
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
            {/* Replace with your actual Dashboard component */}
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