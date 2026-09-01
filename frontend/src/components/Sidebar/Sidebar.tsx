'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Users, Activity, Heart, Eye, Network, BookOpen, Search } from 'lucide-react';
import styles from './Sidebar.module.css';

const navItems = [
  { href: '/patients', label: 'Patient Cohort', icon: Users },
  { href: '/patients/P001/kidney', label: 'Kidney Module', icon: Activity },
  { href: '/patients/P001/cardio', label: 'Cardio Module', icon: Heart, badge: 'Soon' },
  { href: '/patients/P001/retinopathy', label: 'Retinopathy', icon: Eye, badge: 'Soon' },
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
            const isActive = pathname.startsWith(item.href) || 
              (item.href === '/patients' && pathname === '/');
            
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
