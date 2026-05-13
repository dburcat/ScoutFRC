import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import api from '@/api/client';
import { User, AuthResponse } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  login: (data: AuthResponse) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    const checkUser = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const response = await api.get<User>('/me');
        setUser(response.data);
      } catch {
        localStorage.removeItem('token');
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    const timeout = setTimeout(() => setIsLoading(false), 5000);
    checkUser().then(() => clearTimeout(timeout));
    return () => clearTimeout(timeout);
  }, []);

  const login = async (data: AuthResponse) => {
    // Clear any cached data from a previous user before setting the new one
    queryClient.clear();
    localStorage.setItem('token', data.access_token);
    const response = await api.get<User>('/me');
    setUser(response.data);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    // Wipe all cached query data so the next user starts fresh
    queryClient.clear();
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};