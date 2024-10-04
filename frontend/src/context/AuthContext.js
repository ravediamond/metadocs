import React, { createContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [tenantIds, setTenantIds] = useState([]); // Store tenant IDs
  const [currentTenant, setCurrentTenant] = useState(null); // Store current tenant
  const navigate = useNavigate();

  useEffect(() => {
    if (token) {
      // Decode token to extract tenant IDs
      const decodedToken = jwtDecode(token);
      const tenants = decodedToken.tenant_ids || [];
      setTenantIds(tenants);

      // Optionally fetch user profile or verify token here
      fetchUserProfile();
    }
  }, [token]);

  const fetchUserProfile = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await response.json();
      if (response.ok) {
        setUser(data);
      } else {
        handleLogout();
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      handleLogout();
    }
  };

  const handleLogin = async (email, password) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.access_token);
        setToken(data.access_token);

        // Decode the token to extract tenant IDs
        const decodedToken = jwtDecode(data.access_token);
        setTenantIds(decodedToken.tenant_ids || []);

        // Redirect to tenant selection if there are multiple tenants
        if (decodedToken.tenant_ids && decodedToken.tenant_ids.length > 1) {
          navigate('/select-tenant');
        } else {
          // Set the single tenant as the current tenant and navigate to the dashboard
          setCurrentTenant(decodedToken.tenant_ids[0]);
          navigate('/dashboard');
        }
      } else {
        throw new Error(data.detail || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setTenantIds([]);
    setCurrentTenant(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider
      value={{ user, token, tenantIds, currentTenant, setCurrentTenant, handleLogin, handleLogout }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;