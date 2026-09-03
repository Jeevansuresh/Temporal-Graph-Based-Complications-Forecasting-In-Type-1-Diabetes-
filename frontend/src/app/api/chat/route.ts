import { NextResponse } from 'next/server';
import { getOpenAIClient } from '@/lib/openai';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { module, patientId, messages, patientData } = body;

    if (!module || !patientId || !messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const client = getOpenAIClient();
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT_MAIN || 'gpt-4.1-mini';

    let moduleTitle = 'Kidney (DKD/CKD)';
    let focusArea = 'Diabetic Kidney Disease, eGFR slope, UACR albuminuria, and KDIGO/ADA risk staging';

    if (module === 'cardio') {
      moduleTitle = 'Cardiovascular (ASCVD/CAD/HF)';
      focusArea = 'Cardiovascular Disease risk stratification, blood pressure & lipid co-progression, NT-proBNP, and ACC/ADA guidelines';
    } else if (module === 'retinopathy') {
      moduleTitle = 'Diabetic Retinopathy (DR)';
      focusArea = 'Retinopathy ICDR stage trajectory, HbA1c variability, systemic BP impact, screening timing, and ADA vision standards';
    }

    const systemPrompt = `
You are an expert, evidence-grounded AI Clinical Reasoning Assistant specialized in ${moduleTitle} for Type 1 Diabetes (T1D).
You are discussing SYNTHETIC Patient ID: ${patientId}.

FOCUS AREA: ${focusArea}

CRITICAL CLINICAL ASSISTANT RULES:
1. Base all answers strictly on the supplied patient profile, longitudinal trajectory, biomarker data, rules, and clinical flags provided below.
2. Be direct, precise, concise, and professional. Format your response cleanly using GitHub-style Markdown (bullet points, bold text, clear section headers).
3. Do not invent clinical findings or lab values not present in the data.
4. Distinguish clearly between primary prevention and secondary prevention when analyzing risk.
5. If asked for recommendations, explicitly ground them in established guidelines (e.g. ADA Standards of Care, KDIGO 2024, ACC/AHA CVD guidelines).

PATIENT CLINICAL CONTEXT & DATA PACKET:
${JSON.stringify(patientData, null, 2)}
`;

    const apiMessages = [
      { role: 'system', content: systemPrompt },
      ...messages.map((m: any) => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content,
      })),
    ];

    const response = await client.chat.completions.create({
      model: deployment,
      messages: apiMessages as any,
      temperature: 0.2,
    });

    const reply = response.choices[0]?.message?.content ?? 'No response generated.';
    return NextResponse.json({ reply });

  } catch (error: any) {
    console.error('Chat API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
