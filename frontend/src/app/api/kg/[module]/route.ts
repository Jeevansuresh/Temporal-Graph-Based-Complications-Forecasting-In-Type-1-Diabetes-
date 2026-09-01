import { NextResponse } from 'next/server';
import { getNeo4jDriver } from '@/lib/neo4j';

export async function GET(request: Request, { params }: { params: Promise<{ module: string }> }) {
  const { module } = await params;
  // We'll return both Kidney and Cardio mock logic/fetch depending on what is available in the neo4j db
  // For Kidney we know it's in the DB, for cardio it might not be.
  const driver = getNeo4jDriver();
  const session = driver.session();
  
  try {
    // Attempt to fetch all concepts and relationships.
    // If a module system was explicitly defined by labels (e.g. :KidneyConcept), we'd filter.
    // Since we only have a single DB for kidney currently, we'll fetch everything.
    const result = await session.run(`
      MATCH (source:Concept)-[r:CLINICAL_RELATIONSHIP]->(target:Concept)
      RETURN source.name AS source, r.relation AS relation, target.name AS target
    `);
    
    const links = result.records.map((r: any) => ({
      source: r.get('source'),
      target: r.get('target'),
      label: r.get('relation'),
    }));
    
    // Extract unique nodes
    const nodesMap = new Map();
    links.forEach((l: any) => {
      if (!nodesMap.has(l.source)) nodesMap.set(l.source, { id: l.source, group: 1 });
      if (!nodesMap.has(l.target)) nodesMap.set(l.target, { id: l.target, group: 2 });
    });
    
    const nodes = Array.from(nodesMap.values());
    
    return NextResponse.json({ nodes, links });
    
  } catch (error: any) {
    console.error('Error fetching KG:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
