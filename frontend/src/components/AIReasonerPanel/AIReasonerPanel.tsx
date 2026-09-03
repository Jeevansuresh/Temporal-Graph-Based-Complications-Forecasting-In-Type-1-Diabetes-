'use client';
import { useState } from 'react';
import { Bot, ChevronDown, ChevronUp } from 'lucide-react';
import MarkdownView from '@/components/MarkdownView/MarkdownView';
import styles from './AIReasonerPanel.module.css';

export default function AIReasonerPanel({ content, loading }: { content: string | null; loading: boolean }) {
  const [expanded, setExpanded] = useState(true);

  if (loading) {
    return (
      <div className={styles.panel}>
        <div className={styles.header}>
          <div className={styles.titleBox}>
            <Bot className={styles.icon} size={20} />
            <h3>AI Clinical Reasoner (Azure OpenAI)</h3>
          </div>
        </div>
        <div className={styles.content}>
          <div className={styles.skeleton}></div>
          <div className={styles.skeleton} style={{ width: '80%' }}></div>
          <div className={styles.skeleton} style={{ width: '90%' }}></div>
        </div>
      </div>
    );
  }

  if (!content) return null;

  return (
    <div className={styles.panel}>
      <div className={styles.header} onClick={() => setExpanded(!expanded)}>
        <div className={styles.titleBox}>
          <Bot className={styles.icon} size={20} />
          <h3>AI Clinical Reasoner (Azure OpenAI)</h3>
        </div>
        <button className={styles.toggleBtn}>
          {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
      </div>
      
      {expanded && (
        <div className={styles.content}>
          <MarkdownView content={content} />
        </div>
      )}
    </div>
  );
}
