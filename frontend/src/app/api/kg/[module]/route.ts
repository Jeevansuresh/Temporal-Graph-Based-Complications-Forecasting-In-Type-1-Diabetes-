import { NextResponse } from 'next/server';
import { getNeo4jDriver, DEFAULT_DATABASE } from '@/lib/neo4j';
import { getCardioDriver, CARDIO_DATABASE } from '@/lib/neo4jCardio';
import { getRetinopathyDriver, RETINOPATHY_DATABASE } from '@/lib/neo4jRetinopathy';
import path from 'path';
import fs from 'fs';

export async function GET(
  request: Request,
  { params }: { params: Promise<{ module: string }> }
) {
  const { module } = await params;
  const mod = (module || 'kidney').toLowerCase();

  try {
    let rawLinks: { source: string; target: string; label: string }[] = [];

    if (mod === 'cardio') {
      const driver = getCardioDriver();
      const session = driver.session(CARDIO_DATABASE ? { database: CARDIO_DATABASE } : undefined);
      try {
        const result = await session.run(`
          MATCH (source:Concept)-[r:CLINICAL_RELATIONSHIP]->(target:Concept)
          RETURN source.name AS source, coalesce(r.relation, type(r)) AS relation, target.name AS target
        `);
        rawLinks = result.records.map((r: any) => ({
          source: r.get('source'),
          target: r.get('target'),
          label: r.get('relation'),
        }));
      } finally {
        await session.close();
      }
    } else if (mod === 'retinopathy') {
      let fetched = false;
      try {
        const driver = getRetinopathyDriver();
        const session = driver.session(RETINOPATHY_DATABASE ? { database: RETINOPATHY_DATABASE } : undefined);
        try {
          const result = await session.run(`
            MATCH (source:Concept)-[r:CLINICAL_RELATIONSHIP]->(target:Concept)
            RETURN source.name AS source, coalesce(r.relation, type(r)) AS relation, target.name AS target
          `);
          if (result.records.length > 0) {
            rawLinks = result.records.map((r: any) => ({
              source: r.get('source'),
              target: r.get('target'),
              label: r.get('relation'),
            }));
            fetched = true;
          }
        } finally {
          await session.close();
        }
      } catch (e) {
        console.warn('Retinopathy Neo4j query failed, falling back to CKG CSV:', e);
      }

      if (!fetched) {
        // Fallback: Read Retinopathy relationships.csv
        const relCsvPath = path.resolve(process.cwd(), '../Retinopathy/relationships.csv');
        if (fs.existsSync(relCsvPath)) {
          const content = fs.readFileSync(relCsvPath, 'utf-8');
          const lines = content.split(/\r?\n/);
          for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (!line) continue;
            const parts = line.split(',');
            if (parts.length >= 3) {
              rawLinks.push({
                source: parts[0].trim(),
                label: parts[1].trim(),
                target: parts[2].trim(),
              });
            }
          }
        }
      }
    } else {
      // Default: Kidney module
      const driver = getNeo4jDriver();
      const session = driver.session(DEFAULT_DATABASE ? { database: DEFAULT_DATABASE } : undefined);
      try {
        const result = await session.run(`
          MATCH (source:Concept)-[r:CLINICAL_RELATIONSHIP]->(target:Concept)
          RETURN source.name AS source, r.relation AS relation, target.name AS target
        `);
        rawLinks = result.records.map((r: any) => ({
          source: r.get('source'),
          target: r.get('target'),
          label: r.get('relation'),
        }));
      } finally {
        await session.close();
      }
    }

    const links = rawLinks.filter(l => l.source && l.target && l.label);

    const nodesMap = new Map<string, { id: string; group: number }>();
    links.forEach((l) => {
      if (!nodesMap.has(l.source)) nodesMap.set(l.source, { id: l.source, group: 1 });
      if (!nodesMap.has(l.target)) nodesMap.set(l.target, { id: l.target, group: 2 });
    });

    const nodes = Array.from(nodesMap.values());

    return NextResponse.json({ nodes, links });
  } catch (error: any) {
    console.error(`Error fetching KG for ${module}:`, error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
