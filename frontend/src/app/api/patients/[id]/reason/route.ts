import { NextResponse } from 'next/server';
import { getNeo4jDriver } from '@/lib/neo4j';
import { getOpenAIClient } from '@/lib/openai';

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const driver = getNeo4jDriver();
  const session = driver.session();
  const { id: patientId } = await params;
  
  try {
    const body = await request.json();
    const { packet } = body;
    
    const client = getOpenAIClient();
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT_MAIN || 'gpt-4o';
    
    const prompt = `
You are an evidence-grounded clinical reasoning assistant.
You are reviewing a synthetic pediatric Type 1 diabetes
patient for longitudinal kidney-risk assessment.

Use ONLY the structured temporal findings and clinical
knowledge supplied below.

Do not invent medical relationships.
Do not diagnose the patient.
Do not convert risk signals into confirmed disease.
Do not treat a single abnormal value as persistent disease.
Clearly distinguish observed findings from interpretation.

Return the response using exactly these sections in Markdown format:

### CLINICAL SUMMARY
### TRAJECTORY
### KEY FINDINGS
### CLINICAL INTERPRETATION
### WHAT TO REVIEW
### EVIDENCE

Keep the output concise and clinician-facing.

Structured reasoning packet:
${JSON.stringify(packet, null, 2)}
`;

    const response = await client.chat.completions.create({
      model: deployment,
      messages: [
        { role: 'system', content: 'You are an evidence-grounded clinical reasoning assistant.' },
        { role: 'user', content: prompt }
      ],
      temperature: 0,
    });
    
    return NextResponse.json({ result: response.choices[0].message.content });
    
  } catch (error: any) {
    console.error('Error generating reasoning:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  } finally {
    await session.close();
  }
}
