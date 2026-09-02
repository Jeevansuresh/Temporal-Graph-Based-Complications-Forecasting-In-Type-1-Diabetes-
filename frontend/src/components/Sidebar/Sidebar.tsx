'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Users, Activity, Heart, Eye, Network, BookOpen, Search } from 'lucide-react';
import styles from './Sidebar.module.css';

const navItems = [
  { href: '/patients', label: 'Patient Cohort', icon: Users, exact: true },
  { href: '/kidney', label: 'Kidney Module', icon: Activity, suffix: true },
  { href: '/cardio', label: 'Cardio Module', icon: Heart, suffix: true },
  { href: '/retinopathy', label: 'Retinopathy', icon: Eye, suffix: true, badge: 'Soon' as const },
  { href: '/knowledge-graph', label: 'Knowledge Graph', icon: Network },
  { href: '/evidence', label: 'Evidence Library', icon: BookOpen },
];

export default function Sidebar() {
  const pathname = usePathname();

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
            // For module links, match by suffix of current path
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
        <div className={styles.status}>
          <div className={styles.statusDot}></div>
          <span>System Online</span>
        </div>
      </div>
    </aside>
  );
}
