'use client';
import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import styles from './KGExplorer.module.css';

export default function KGExplorer({ nodes, links }: { nodes: any[]; links: any[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    containerRef.current.innerHTML = ''; // Clear previous

    const svg = d3.select(containerRef.current)
      .append('svg')
      .attr('width', width)
      .attr('height', height);
      
    // Add zoom capabilities
    const zoom = d3.zoom().on('zoom', (e) => {
      g.attr('transform', e.transform);
    });
    
    svg.call(zoom as any);
    
    const g = svg.append('g');

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Draw lines
    const link = g.append('g')
      .attr('stroke', 'var(--color-border-strong)')
      .attr('stroke-opacity', 0.6)
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke-width', 2);

    // Draw link labels (relation names)
    const linkLabels = g.append('g')
      .selectAll('text')
      .data(links)
      .join('text')
      .text((d: any) => d.label)
      .attr('font-size', '10px')
      .attr('fill', 'var(--color-text-muted)')
      .attr('text-anchor', 'middle')
      .attr('pointer-events', 'none');

    // Draw nodes
    const node = g.append('g')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', 15)
      .attr('fill', (d: any) => {
        // Pseudo logic for color based on type, since we just have names now
        if (d.id.includes('Risk') || d.id === 'ASCVD') return 'var(--color-red)';
        if (d.id.includes('BP') || d.id === 'eGFR' || d.id === 'UACR') return 'var(--color-cyan)';
        return 'var(--color-amber)';
      })
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        setSelectedNode(d);
      });

    // Draw node labels
    const nodeLabels = g.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text((d: any) => d.id)
      .attr('font-size', '12px')
      .attr('fill', 'var(--color-text-primary)')
      .attr('dx', 18)
      .attr('dy', 4)
      .attr('pointer-events', 'none');

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      linkLabels
        .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
        .attr('y', (d: any) => (d.source.y + d.target.y) / 2 - 5);

      node
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      nodeLabels
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });
    
    // Drag functionality
    const drag = d3.drag()
      .on('start', (event, d: any) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d: any) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d: any) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    node.call(drag as any);

    return () => {
      simulation.stop();
    };
  }, [nodes, links]);

  return (
    <div className={styles.container}>
      <div ref={containerRef} className={styles.canvas}></div>
      
      {selectedNode && (
        <div className={styles.sidePanel}>
          <div className={styles.panelHeader}>
            <h3>{selectedNode.id}</h3>
            <button onClick={() => setSelectedNode(null)}>✕</button>
          </div>
          <div className={styles.panelContent}>
            <p className={styles.label}>Relationships</p>
            <ul className={styles.relList}>
              {links.filter(l => l.source.id === selectedNode.id || l.target.id === selectedNode.id).map((l, i) => {
                const isSource = l.source.id === selectedNode.id;
                return (
                  <li key={i}>
                    {isSource ? (
                      <><span className={styles.relBadge}>{l.label} ➔</span> {l.target.id}</>
                    ) : (
                      <>{l.source.id} <span className={styles.relBadge}>➔ {l.label}</span></>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
