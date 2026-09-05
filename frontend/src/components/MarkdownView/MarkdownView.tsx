import React from 'react';
import styles from './MarkdownView.module.css';

function parseInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\[.*?\]\(.*?\)|\*\*.*?\*\*|\*.*?\*|`.*?`)/g);
  return parts.map((part, index) => {
    if (part.startsWith('[') && part.includes('](') && part.endsWith(')')) {
      const match = part.match(/\[(.*?)\]\((.*?)\)/);
      if (match) {
        return <a key={index} href={match[2]} className={styles.link}>{match[1]}</a>;
      }
    }
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={index}>{parseInline(part.slice(2, -2))}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return <em key={index}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return <code key={index} className={styles.inlineCode}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

export default function MarkdownView({ content }: { content: string }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let listBuffer: { type: 'ul' | 'ol'; items: string[] } | null = null;

  function flushList() {
    if (!listBuffer) return;
    if (listBuffer.type === 'ul') {
      elements.push(
        <ul key={`ul-${elements.length}`} className={styles.list}>
          {listBuffer.items.map((item, idx) => (
            <li key={idx}>{parseInline(item)}</li>
          ))}
        </ul>
      );
    } else {
      elements.push(
        <ol key={`ol-${elements.length}`} className={styles.list}>
          {listBuffer.items.map((item, idx) => (
            <li key={idx}>{parseInline(item)}</li>
          ))}
        </ol>
      );
    }
    listBuffer = null;
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Horizontal Rule
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      flushList();
      elements.push(<hr key={`hr-${index}`} className={styles.hr} />);
      return;
    }

    // Headings
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h3 key={`h3-${index}`} className={styles.h3}>{parseInline(trimmed.slice(4))}</h3>);
      return;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h2 key={`h2-${index}`} className={styles.h2}>{parseInline(trimmed.slice(3))}</h2>);
      return;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h1 key={`h1-${index}`} className={styles.h1}>{parseInline(trimmed.slice(2))}</h1>);
      return;
    }

    // Unordered List (- or *)
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const text = trimmed.slice(2);
      if (!listBuffer || listBuffer.type !== 'ul') {
        flushList();
        listBuffer = { type: 'ul', items: [text] };
      } else {
        listBuffer.items.push(text);
      }
      return;
    }

    // Numbered List (1. 2. etc)
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      const text = numMatch[2];
      if (!listBuffer || listBuffer.type !== 'ol') {
        flushList();
        listBuffer = { type: 'ol', items: [text] };
      } else {
        listBuffer.items.push(text);
      }
      return;
    }

    // Empty lines or normal paragraphs
    flushList();
    if (trimmed === '') {
      return;
    }

    elements.push(<p key={`p-${index}`} className={styles.p}>{parseInline(trimmed)}</p>);
  });

  flushList();

  return <div className={styles.markdownBody}>{elements}</div>;
}
