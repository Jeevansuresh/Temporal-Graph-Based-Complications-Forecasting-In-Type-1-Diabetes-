'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Users, Activity, Heart, Eye, Network, BookOpen, Search, LogOut } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import styles from './Sidebar.module.css';

const navItems: { href: string; label: string; icon: any; exact?: boolean; suffix?: boolean; badge?: string }[] = [
  { href: '/patients', label: 'Patient Cohort', icon: Users, exact: true },
  { href: '/kidney', label: 'Kidney Module', icon: Activity, suffix: true },
  { href: '/cardio', label: 'Cardio Module', icon: Heart, suffix: true },
  { href: '/retinopathy', label: 'Retinopathy', icon: Eye, suffix: true },
  { href: '/knowledge-graph', label: 'Knowledge Graph', icon: Network },
  { href: '/evidence', label: 'Evidence Library', icon: BookOpen },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <div className={styles.iconContainer}>
          <Network className={styles.logoIcon} />
          <div className={styles.pulseRing}></div>
        </div>
        <h1>T1D-CareGraph</h1>
      </div>

      <div className={styles.search}>
        <Search className={styles.searchIcon} size={16} />
        <input type="text" placeholder="Search patient ID..." />
      </div>

      <nav className={styles.nav}>
        <ul>
          {navItems.map((item) => {
            const Icon = item.icon;
            let isActive = false;
            if (item.exact) {
              isActive = pathname === item.href || pathname === '/';
            } else if (item.suffix) {
              isActive = pathname.endsWith(item.href);
            } else {
              isActive = pathname.startsWith(item.href);
            }
            
            return (
              <li key={item.href}>
                <Link href={item.href} className={`${styles.link} ${isActive ? styles.active : ''}`}>
                  <Icon size={18} />
                  <span>{item.label}</span>
                  {item.badge && <span className={styles.badge}>{item.badge}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      
      <div className={styles.footer}>
        {user && (
          <div className={styles.userCard}>
            <div className={styles.userAvatar}>
              <span>{user.avatarInitials}</span>
            </div>
            <div className={styles.userInfo}>
              <span className={styles.userName}>{user.name}</span>
              <span className={styles.userHospital}>{user.hospital}</span>
            </div>
            <button
              onClick={logout}
              className={styles.logoutBtn}
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut size={16} />
            </button>
          </div>
        )}

        <div className={styles.status}>
          <div className={styles.statusDot}></div>
          <span>Clinical Pipeline Online</span>
        </div>
      </div>
    </aside>
  );
}
