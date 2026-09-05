import { NextResponse } from 'next/server';

export function checkApiAuth(request: Request): NextResponse | null {
  const secret = process.env.CLINICAL_API_SECRET;
  if (!secret) return null; // no secret configured — allow (dev mode)
  const auth = request.headers.get('authorization') || '';
  if (auth !== `Bearer ${secret}`) {
    return NextResponse.json(
      { error: 'Unauthorized. Sign in to access AI clinical reasoning.' },
      { status: 401 }
    );
  }
  return null; // authorized
}
