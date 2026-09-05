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
    
    // Check against configured environment variables or non-empty valid inputs
    const expectedEmail = (process.env.NEXT_PUBLIC_CLINICAL_EMAIL || '').trim().toLowerCase();
    const expectedPassword = process.env.NEXT_PUBLIC_CLINICAL_PASSWORD || '';

    let isValid = false;

    if (expectedEmail && expectedPassword) {
      isValid = cleanEmail === expectedEmail && pass === expectedPassword;
    } else {
      // Fallback: Validate email format & non-empty password if env is not explicitly set
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      isValid = emailRegex.test(cleanEmail) && pass.length >= 6;
    }

    if (isValid) {
      const nameFromEmail = cleanEmail.split('@')[0].replace(/[^a-zA-Z]/g, ' ');
      const formattedName = nameFromEmail ? `Dr. ${nameFromEmail.charAt(0).toUpperCase() + nameFromEmail.slice(1)}` : 'Dr. Clinical Specialist';
      const initials = cleanEmail.substring(0, 2).toUpperCase();

      const userProfile: User = {
        name: formattedName,
        email: cleanEmail,
        role: 'Lead Endocrinologist',
        hospital: 'Clinical Workspace',
        avatarInitials: initials,
      };

      setUser(userProfile);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(userProfile));
      return { success: true };
    } else {
      return { 
        success: false, 
        error: 'Invalid credentials. Please verify your email address and password.' 
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
