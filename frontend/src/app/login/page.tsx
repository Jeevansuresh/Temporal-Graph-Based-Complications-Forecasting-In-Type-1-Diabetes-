'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Network, Mail, Lock, Eye, EyeOff, ShieldCheck, AlertCircle, ArrowRight, Building2 } from 'lucide-react';
import styles from './login.module.css';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) {
      router.push('/patients');
    }
  }, [user, isLoading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const res = await login(email, password);
      if (res.success) {
        router.push('/patients');
      } else {
        setError(res.error || 'Authentication failed');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const autofillDemoCredentials = () => {
    setEmail('drjeevan@apollo.com');
    setPassword('Doctor7604@!');
    setError(null);
  };

  return (
    <div className={styles.container}>
      <div className={styles.bgGrid} />
      <div className={styles.glowOrb} />

      <div className={styles.loginCard}>
        <div className={styles.header}>
          <div className={styles.brandLogo}>
            <Network size={28} />
          </div>
          <h1 className={styles.title}>T1D-CareGraph</h1>
          <p className={styles.subtitle}>Temporal Complications Forecasting Portal</p>
          <div className={styles.hospitalBadge}>
            <Building2 size={13} />
            <span>Apollo Hospitals System</span>
          </div>
        </div>

        {error && (
          <div className={styles.errorBox}>
            <AlertCircle size={18} shrink-0="true" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="email">Doctor Email</label>
            <div className={styles.inputWrapper}>
              <Mail className={styles.inputIcon} size={18} />
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="drjeevan@apollo.com"
                className={styles.input}
              />
            </div>
          </div>

          <div className={styles.inputGroup}>
            <label className={styles.label} htmlFor="password">Password</label>
            <div className={styles.inputWrapper}>
              <Lock className={styles.inputIcon} size={18} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className={styles.input}
              />
              <button
                type="button"
                className={styles.togglePassword}
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={styles.submitBtn}
          >
            {isSubmitting ? (
              <>
                <div className={styles.spinner} />
                <span>Authenticating...</span>
              </>
            ) : (
              <>
                <span>Sign In to Clinical Workspace</span>
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <div className={styles.hintCard}>
          <div className={styles.hintHeader}>
            <span>Authorized Clinical Credentials</span>
            <button 
              type="button" 
              onClick={autofillDemoCredentials}
              className={styles.autofillBtn}
            >
              Auto-fill Credentials
            </button>
          </div>
          <div className={styles.hintDetails}>
            <div><strong>Email:</strong> drjeevan@apollo.com</div>
            <div><strong>Password:</strong> Doctor7604@!</div>
          </div>
        </div>

        <div className={styles.footer}>
          <ShieldCheck size={14} />
          <span>HIPAA Compliant &amp; 256-Bit Encrypted Portal</span>
        </div>
      </div>
    </div>
  );
}
