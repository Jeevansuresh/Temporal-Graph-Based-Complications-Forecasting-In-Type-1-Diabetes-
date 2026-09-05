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
You are a clinical reasoning assistant specializing in Retinopathy forecasting for Type 1 Diabetes.

Patient ID: ${patientId}
Risk State: ${packet.risk_state}
Risk Reason: ${packet.risk_reason}

PROFILE & EVALUATION:
${JSON.stringify(packet, null, 2)}

Provide a clinical reasoning report with these exact markdown sections:
### RETINAL TRAJECTORY
### SYSTEMIC RISK FACTORS
### RISK STATE JUSTIFICATION
### CLINICAL RECOMMENDATIONS
`;

    const response = await client.chat.completions.create({
      model: deployment,
      messages: [
        { role: 'system', content: 'You are an evidence-grounded clinical reasoning assistant for Type 1 diabetes retinopathy complications.' },
        { role: 'user', content: prompt },
      ],
      temperature: 0,
    });

    return NextResponse.json({ result: response.choices[0].message.content });
  } catch (error: any) {
    console.error('Retinopathy reasoning error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
