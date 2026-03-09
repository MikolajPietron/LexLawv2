const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SearchResult {
  origin_id: number;
  signature: string;
  judgment_date: string;
  court_type: string;
  court_name: string;
  judgment_type: string;
  keywords: string[];
  judges: string[];
  matched_chunk: string;
  score: number;
}

export interface SearchResponse {
  original_query: string;
  optimized_query: string;
  results: SearchResult[];
}

export interface AskResponse {
  original_query: string;
  optimized_query: string;
  answer: string;
  results: SearchResult[];
}

export interface FullJudgment {
  id: number;
  signature: string;
  text: string;
  judgment_date: string;
  court_type: string;
}

export interface RateLimitError {
  detail: 'rate_limit';
  limit: number;
  authenticated: boolean;
}

export async function searchRulings(
  query: string,
  numResults: number = 5,
  useReranking: boolean = true,
  token: string | null = null
): Promise<SearchResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}/search`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      query,
      num_results: numResults,
      use_reranking: useReranking,
    }),
  });

  if (res.status === 429) {
    const data: RateLimitError = await res.json();
    throw data;
  }
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

export async function askQuestion(
  query: string,
  numResults: number = 5,
  useReranking: boolean = true,
  token: string | null = null
): Promise<AskResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}/ask`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      query,
      num_results: numResults,
      use_reranking: useReranking,
    }),
  });

  if (res.status === 429) {
    const data: RateLimitError = await res.json();
    throw data;
  }
  if (!res.ok) throw new Error('Ask failed');
  return res.json();
}

export async function getFullJudgment(
  id: number,
  token: string | null = null
): Promise<FullJudgment> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}/judgment/${id}`, { headers });
  if (!res.ok) throw new Error('Failed to fetch judgment');
  return res.json();
}