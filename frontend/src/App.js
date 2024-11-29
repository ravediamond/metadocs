import React from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import NewDomainPage from './pages/NewDomainPage';
import DomainPage from './pages/DomainPage';
import DomainConfigPage from './pages/DomainConfigPage';
import DomainVersionsPage from './pages/DomainVersionsPage';
import UserConfigPage from './pages/UserConfigPage';
import TenantSelectionPage from './pages/TenantSelectionPage';
import FileManagerPage from './pages/FileManagerPage';
import ProcessingWorkspacePage from './pages/ProcessingWorkspacePage';
import VersionDetailPage from './pages/VersionDetailPage';
import KnowledgeGraphPage from './pages/KnowledgeGraphPage';
import SystemSettingsPage from './pages/SystemSettingsPage';
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
        {/* Public Routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        <Route path="/select-tenant" element={<TenantSelectionPage />} />

        {/* Protected Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />

        {/* Domain Routes */}
        <Route
          path="/domain/:domain_id"
          element={
            <ProtectedRoute>
              <DomainPage />
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
          path="/domains/:domain_id/config"
          element={
            <ProtectedRoute>
              <DomainConfigPage />
            </ProtectedRoute>
          }
        />

        {/* File Management */}
        <Route
          path="/domains/:domain_id/files"
          element={
            <ProtectedRoute>
              <FileManagerPage />
            </ProtectedRoute>
          }
        />

        {/* Processing Workspace */}
        <Route
          path="/domains/:domain_id/process"
          element={
            <ProtectedRoute>
              <ProcessingWorkspacePage />
            </ProtectedRoute>
          }
        />

        {/* Knowledge Graph */}
        <Route
          path="/domains/:domain_id/graph"
          element={
            <ProtectedRoute>
              <KnowledgeGraphPage />
            </ProtectedRoute>
          }
        />

        {/* User Settings */}
        <Route
          path="/user/config"
          element={
            <ProtectedRoute>
              <UserConfigPage />
            </ProtectedRoute>
          }
        />

        {/* Version Management Routes */}
        <Route
          path="/domains/:domain_id/versions"
          element={
            <ProtectedRoute>
              <DomainVersionsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/domains/:domain_id/versions/:version_id"
          element={
            <ProtectedRoute>
              <VersionDetailPage />
            </ProtectedRoute>
          }
        />

        {/* System Settings */}
        <Route
          path="/admin/settings"
          element={
            <ProtectedRoute>
              <SystemSettingsPage />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}

export default App;