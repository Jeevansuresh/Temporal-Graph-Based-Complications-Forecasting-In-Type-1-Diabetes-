'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar/Sidebar';
import { AuthProvider, useAuth } from '@/context/AuthContext';

function MainContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isLoading, user } = useAuth();
  const isLoginPage = pathname === '/login';

  if (isLoginPage) {
    return <>{children}</>;
  }

  // Prevent flash of protected content while checking auth state
  if (isLoading || !user) {
    return (
      <div style={{
        height: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#0B0F19',
        color: '#06b6d4',
        fontFamily: 'var(--font-sans, sans-serif)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid rgba(6, 182, 212, 0.2)',
            borderTopColor: '#06b6d4',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            margin: '0 auto 16px auto'
          }} />
          <p style={{ fontSize: '0.9rem', color: '#9CA3AF' }}>Verifying Clinical Session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <Sidebar />
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}

export default function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <MainContent>{children}</MainContent>
    </AuthProvider>
  );
}
