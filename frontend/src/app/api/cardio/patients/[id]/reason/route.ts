import { NextResponse } from 'next/server';
import { getOpenAIClient } from '@/lib/openai';
import { checkApiAuth } from '@/lib/apiAuth';

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const authError = checkApiAuth(request);
  if (authError) return authError;

  const { id: patientId } = await params;

  try {
    const body = await request.json();
    const { packet } = body;

    const client = getOpenAIClient();
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT_MAIN || 'gpt-4.1-mini';

    const prompt = `
You are an evidence-grounded clinical reasoning research assistant specializing in cardiovascular disease forecasting in Type 1 Diabetes (T1D).

You are analyzing a SYNTHETIC patient (ID: ${patientId}) for cardiovascular risk stratification.

CRITICAL INSTRUCTIONS:
- You are NOT providing an unverified diagnostic prescription.
- Use ONLY the information contained in the reasoning packet.
- Do not invent clinical relationships not present in the supplied data.
- Distinguish primary prevention vs. secondary prevention contexts.
- Check whether clinical rules (R001-R007) are satisfied before claiming they apply.

REASONING PACKET:
${JSON.stringify(packet, null, 2)}

Analyze the patient's longitudinal cardiometabolic trajectory and return the analysis in EXACTLY these sections using markdown:

### TEMPORAL FINDINGS
### KG-GROUNDED FINDINGS
### RULE EVALUATION
### JOINT TEMPORAL PATTERN
### EVIDENCE CONTEXT
### CLINICAL INTERPRETATION & RISK STRATIFICATION
### LIMITATIONS & RECOMMENDED INVESTIGATIONS
`;

    const response = await client.chat.completions.create({
      model: deployment,
      messages: [
        { role: 'system', content: 'You are an evidence-grounded clinical reasoning assistant for Type 1 diabetes cardiovascular complications.' },
        { role: 'user', content: prompt },
      ],
      temperature: 0,
    });

    return NextResponse.json({ result: response.choices[0].message.content });
  } catch (error: any) {
    console.error('Cardio reasoning error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
