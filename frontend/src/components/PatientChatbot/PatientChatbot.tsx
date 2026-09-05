'use client';
import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles, MessageSquare } from 'lucide-react';
import MarkdownView from '@/components/MarkdownView/MarkdownView';
import { useAuth } from '@/context/AuthContext';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Lock, LogIn } from 'lucide-react';
import styles from './PatientChatbot.module.css';

interface PatientChatbotProps {
  module: 'kidney' | 'cardio' | 'retinopathy';
  patientId: string;
  patientData: any;
}

const MODULE_CONFIG = {
  kidney: {
    title: 'Kidney Clinical Assistant',
    color: 'var(--color-cyan, #06b6d4)',
    suggestions: [
      "What is driving this patient's CKD risk trajectory?",
      "How is the eGFR slope progressing over time?",
      "Are there any UACR / Albuminuria warning signals?",
      "What KDIGO management steps are indicated?"
    ]
  },
  cardio: {
    title: 'Cardio Risk Assistant',
    color: 'var(--color-amber, #f59e0b)',
    suggestions: [
      "Summarize this patient's cardiovascular risk profile.",
      "How are blood pressure and LDL cholesterol interacting?",
      "What triggered the heart failure / ASCVD risk flags?",
      "What secondary prevention steps are indicated?"
    ]
  },
  retinopathy: {
    title: 'Retinopathy AI Assistant',
    color: '#a855f7',
    suggestions: [
      "What is this patient's current retinal stage and trajectory?",
      "Is there an elevated risk of NPDR progression?",
      "How do HbA1c and Blood Pressure affect DR risk here?",
      "When should the next dilated eye exam be scheduled?"
    ]
  }
};

export default function PatientChatbot({ module, patientId, patientData }: PatientChatbotProps) {
  const config = MODULE_CONFIG[module] ?? MODULE_CONFIG.kidney;

  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([
    {
      role: 'assistant',
      content: `Hello! I am your **${config.title}**. I have loaded full clinical context for **Patient ${patientId}**.\nHow can I help you analyze this patient's longitudinal trajectory or risk stratification?`
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  
  const { user } = useAuth();
  const pathname = usePathname();

  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function sendMessage(textToSend?: string) {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMessage = { role: 'user' as const, content: query };
    const updatedMessages = [...messages, userMessage];

    setMessages(updatedMessages);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.NEXT_PUBLIC_CLINICAL_PASSWORD || ''}`
        },
        body: JSON.stringify({
          module,
          patientId,
          messages: updatedMessages,
          patientData
        })
      });

      const data = await response.json();
      if (data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${data.error}` }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      }
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Network error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  }

  if (!user) {
    return (
      <div className={styles.card} style={{ '--theme-color': config.color } as any}>
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <div className={styles.iconWrap} style={{ color: config.color }}>
              <Bot size={22} />
            </div>
            <div className={styles.titleBox}>
              <h3>{config.title}</h3>
            </div>
          </div>
          <span className={styles.premiumBadge}>⭐ Premium</span>
        </div>
        <div className={styles.lockedContent}>
          <div className={styles.lockIcon}><Lock size={32} /></div>
          <p className={styles.lockTitle}>Premium Feature</p>
          <p className={styles.lockSub}>Sign in to chat with the AI assistant. (This feature consumes real LLM tokens!)</p>
          <Link href={`/login?next=${encodeURIComponent(pathname)}`} className={styles.loginBtn}>
            <LogIn size={16} />
            Sign in to Access
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.card} style={{ '--theme-color': config.color } as any}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.iconWrap} style={{ color: config.color }}>
            <Bot size={22} />
          </div>
          <div className={styles.titleBox}>
            <h3>
              {config.title}
              <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>({patientId})</span>
            </h3>
            <p>Evidence-grounded assistant for {module.toUpperCase()} complications</p>
          </div>
        </div>
        <div className={styles.statusBadge}>
          <div className={styles.statusDot}></div>
          <span>Azure OpenAI • GPT-4</span>
        </div>
      </div>

      {/* Suggested Chat Prompt Chips */}
      <div className={styles.suggestionsBox}>
        <span className={styles.suggestionsTitle}>
          <Sparkles size={12} style={{ display: 'inline', marginRight: '4px' }} />
          Suggested Clinical Queries ({module})
        </span>
        <div className={styles.chipsGrid}>
          {config.suggestions.map((prompt, idx) => (
            <button
              key={idx}
              className={styles.chipBtn}
              onClick={() => sendMessage(prompt)}
              disabled={loading}
            >
              <MessageSquare size={13} />
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* Feed */}
      <div className={styles.messagesFeed} ref={feedRef}>
        {messages.map((m, index) => (
          <div key={index} className={`${styles.messageRow} ${styles[m.role]}`}>
            <div className={styles.avatar}>
              {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>
            <div className={styles.bubble}>
              <MarkdownView content={m.content} />
            </div>
          </div>
        ))}

        {loading && (
          <div className={`${styles.messageRow} ${styles.assistant}`}>
            <div className={styles.avatar}>
              <Bot size={16} />
            </div>
            <div className={styles.bubble}>
              <div className={styles.typingIndicator}>
                <div className={styles.typingDot}></div>
                <div className={styles.typingDot}></div>
                <div className={styles.typingDot}></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className={styles.inputBar}>
        <input
          type="text"
          className={styles.input}
          placeholder={`Ask about ${patientId}'s ${module} trajectory or clinical flags...`}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          disabled={loading}
        />
        <button
          className={styles.sendBtn}
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
        >
          <Send size={16} />
          Send
        </button>
      </div>
    </div>
  );
}
