// components/RoleProtectedRoute.js

import React from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { Navigate } from 'react-router-dom';

const RoleProtectedRoute = ({ allowedRoles, children }) => {
  const { isAuthenticated, isLoading, user, loginWithRedirect } = useAuth0();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    loginWithRedirect();
    return null;
  }

  const roles = user && user['https://metadocs.co/roles'] ? user['https://metadocs.co/roles'] : [];

  const hasAccess = allowedRoles.some((role) => roles.includes(role));

  if (!hasAccess) {
    return <Navigate to="/not-authorized" />;
  }

  return children;
};

export default RoleProtectedRoute;