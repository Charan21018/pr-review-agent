const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ReviewRecord {
  id: string;
  repo: string;
  pr_number: number;
  created_at: string;
  status: string;
  summary?: string;
  total_cost_usd: number;
  total_tokens: number;
}

export interface FindingRecord {
  id: string;
  review_id: string;
  file_path: string;
  line_start?: number;
  line_end?: number;
  severity: string;
  description: string;
  confidence: number;
  created_at: string;
}

export interface HitlItem {
  id: string;
  review_id: string;
  escalated_at: string;
  status: string;
  claimed_by?: string;
  resolved_at?: string;
  decision?: string;
  reviewer_comments?: string;
  reason: string;
}

export interface EconomicsData {
  daily_cost_usd: number;
  total_reviews_count: number;
  average_latency_ms: number;
  total_tokens_consumed: number;
  agent_costs: Record<string, number>;
}

export interface TraceEvent {
  id: string;
  ts: string;
  review_id: string;
  agent: string;
  event_type: string;
  span_id: string;
  parent_span?: string;
  model?: string;
  tokens_in?: number;
  tokens_out?: number;
  cost_usd?: number;
  latency_ms?: number;
  outcome?: string;
  confidence?: number;
  payload: Record<string, any>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API Error: ${response.status} ${response.statusText} - ${text}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getReviews: () => request<ReviewRecord[]>('/api/reviews'),
  
  getReview: (id: string) => request<ReviewRecord>(`/api/reviews/${id}`),
  
  getReviewFindings: (id: string) => request<FindingRecord[]>(`/api/reviews/${id}/findings`),
  
  getHitlQueue: () => request<HitlItem[]>('/api/hitl/queue'),
  
  claimHitlItem: (id: string, reviewerName: string) => 
    request<{ success: boolean }>(`/api/hitl/queue/${id}/claim`, {
      method: 'POST',
      body: JSON.stringify({ reviewer_name: reviewerName }),
    }),
    
  resolveHitlItem: (id: string, decision: 'APPROVE' | 'REJECT', reviewerName: string, comments?: string) =>
    request<{ success: boolean }>(`/api/hitl/queue/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        reviewer_name: reviewerName,
        comments,
      }),
    }),
    
  getEconomics: () => request<EconomicsData>('/api/economics'),
  
  getReviewTrace: (id: string) => request<TraceEvent[]>(`/api/reviews/${id}/trace`),
};
