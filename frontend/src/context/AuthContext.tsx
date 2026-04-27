import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import api from '@/api/client'; // Ensure your @ alias is set up
import { User, AuthResponse } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  login: (data: AuthResponse) => Promise<void>;
  logout: () => void;
  isLoading: boolean; // Changed to camelCase
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    const checkUser = async () => {
      // Must match the key used in axios.ts
      const token = localStorage.getItem('token'); 
      if (token) {
        try {
          const response = await api.get<User>('/me'); // Specify the return type
          setUser(response.data);
        } catch (error) {
          localStorage.removeItem('token');
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    checkUser();
  }, []);

  const login = async (data: AuthResponse) => {
    localStorage.setItem('token', data.access_token);
    const response = await api.get<User>('/me');
    setUser(response.data);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    // Optional: redirect to login
    window.location.href = '/login'; 
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