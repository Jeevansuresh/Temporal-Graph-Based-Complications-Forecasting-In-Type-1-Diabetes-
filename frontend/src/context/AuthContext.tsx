'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';

export interface User {
  name: string;
  email: string;
  role: string;
  hospital: string;
  avatarInitials: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, pass: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => ({ success: false }),
  logout: () => {},
  isLoading: true,
});

const DEFAULT_USER: User = {
  name: 'Dr. Jeevan Suresh',
  email: 'drjeevan@apollo.com',
  role: 'Lead Endocrinologist',
  hospital: 'Apollo Hospitals',
  avatarInitials: 'JS',
};

const STORAGE_KEY = 't1d_caregraph_auth_user';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        setUser(JSON.parse(stored));
      }
    } catch (e) {
      console.error('Failed to parse auth token', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isLoading) {
      if (!user && pathname !== '/login') {
        router.push('/login');
      }
    }
  }, [user, isLoading, pathname, router]);

  const login = async (email: string, pass: string): Promise<{ success: boolean; error?: string }> => {
    // Standard delay for realistic smooth transition
    await new Promise((res) => setTimeout(res, 600));

    const cleanEmail = email.trim().toLowerCase();
    
    if (cleanEmail === 'drjeevan@apollo.com' && pass === 'Doctor7604@!') {
      setUser(DEFAULT_USER);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_USER));
      return { success: true };
    } else {
      return { 
        success: false, 
        error: 'Invalid credentials. Please verify your email and password.' 
      };
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
