// =============================================================================
// TO_EXTRACTOR v7.0 - AUTH CONTEXT
// =============================================================================
// Gestione centralizzata autenticazione utente
// =============================================================================

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Verifica autenticazione all'avvio
  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        try {
          const userData = await authApi.getMe();
          setUser(userData);
        } catch (err) {
          console.error('Auth check failed:', err);
          await authApi.logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  // Login
  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const result = await authApi.login(username, password);
      setUser(result.user);
      return result.user;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Credenziali non valide';
      setError(msg);
      throw err;
    }
  }, []);

  // Logout
  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  // Verifica permessi per ruolo
  const hasPermission = useCallback((permission) => {
    if (!user) return false;

    const PERMESSI_RUOLO = {
      admin: ['*'],
      supervisore: ['dashboard', 'upload', 'database', 'supervisione', 'tracciati', 'settings'],
      operatore: ['dashboard', 'upload', 'database', 'tracciati', 'settings'],
      readonly: ['dashboard', 'database']
    };

    const userRole = user.ruolo?.toLowerCase() || 'readonly';
    const allowedPerms = PERMESSI_RUOLO[userRole] || PERMESSI_RUOLO.readonly;

    return allowedPerms.includes('*') || allowedPerms.includes(permission);
  }, [user]);

  // Verifica se utente e admin
  const isAdmin = useCallback(() => {
    return user?.ruolo?.toLowerCase() === 'admin';
  }, [user]);

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    hasPermission,
    isAdmin,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export default AuthContext;
