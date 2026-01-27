const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
console.log('API_URL:', API_URL); 

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

export interface FullJudgment {
  id: number;
  signature: string;
  text: string;
  judgment_date: string;
  court_type: string;
}

export async function searchRulings(
  query: string,
  numResults: number = 5,
  useReranking: boolean = true
): Promise<SearchResponse> {
  const res = await fetch(`${API_URL}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query,
      num_results: numResults,
      use_reranking: useReranking,
    }),
  });

  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

export async function getFullJudgment(id: number): Promise<FullJudgment> {
  const res = await fetch(`${API_URL}/judgment/${id}`);
  if (!res.ok) throw new Error('Failed to fetch judgment');
  return res.json();
}