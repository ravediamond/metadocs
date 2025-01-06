import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [tenantIds, setTenantIds] = useState([]); // Store tenant IDs
  const [currentTenant, setCurrentTenant] = useState(null); // Store current tenant
  const [currentUserRole, setCurrentUserRole] = useState(null); // Store user role
  const navigate = useNavigate();

  useEffect(() => {
    if (token) {
      // Decode token to extract tenant IDs
      const decodedToken = jwtDecode(token);
      const tenants = decodedToken.tenant_ids || [];
      setTenantIds(tenants);
    }
  }, [token]);

  // Trigger fetchUserProfile whenever currentTenant is updated
  useEffect(() => {
    if (token && currentTenant) {
      fetchUserProfile(); // Fetch user profile when the tenant is set
    }
  }, [currentTenant]);

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
        // Once user profile is fetched, fetch their role
        fetchUserRole(currentTenant, data.user_id);
      } else {
        handleLogout();
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
      handleLogout();
    }
  };

  // Fetch the user's role in the selected tenant
  const fetchUserRole = async (tenantId, userId) => {
    try {
      const response = await fetch(
        `${process.env.REACT_APP_BACKEND_URL}/roles/tenants/${tenantId}/users/${userId}/roles`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await response.json();
      if (response.ok && data.length > 0) {
        // Assuming the role is returned as a list, and we take the first role
        setCurrentUserRole(data[0].role_name); // Set the current role from the response
      } else {
        setCurrentUserRole(null); // If no role is found, set it to null
      }
    } catch (error) {
      console.error('Error fetching user role:', error);
      setCurrentUserRole(null);
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

  const handleTenantChange = (tenantId) => {
    setCurrentTenant(tenantId); // Update the selected tenant
    if (user) {
      fetchUserRole(tenantId, user.user_id); // Fetch the role for the new tenant
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setTenantIds([]);
    setCurrentTenant(null);
    setCurrentUserRole(null); // Reset the role on logout
    navigate('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        tenantIds,
        currentTenant,
        setCurrentTenant,
        currentUserRole, // Provide the role in the context
        handleLogin,
        handleLogout,
        handleTenantChange, // Allow changing tenants and fetching new role
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;