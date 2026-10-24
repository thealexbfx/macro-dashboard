export type Transformation = 'level' | 'percent' | 'yoy' | 'mom' | 'pp' | 'indexed' | 'standardized';
export const transformLabels: Record<Transformation, string> = { level: 'Original levels', percent: '% per observation', yoy: 'Year-over-year %', mom: 'Month-over-month %', pp: 'Percentage-point change', indexed: 'Indexed to 100', standardized: 'Standardized deviations' };
export interface Observation {
    date: string;
    value: number | null;
}
export interface Dataset {
    id: string;
    name: string;
    provider_id: string;
    source: string;
    category: string;
    region: string;
    frequency: string;
    units: string;
    seasonal_adjustment: string | null;
    representation: string;
    original_transformation: string;
    source_url: string;
    allowed_transformations: Transformation[];
    status: 'ok' | 'stale' | 'unavailable';
    latest_observation_date: string | null;
    coverage_start: string | null;
    coverage_end: string | null;
    retrieved_at: string | null;
    publication_date: string | null;
    message: string;
    observations: Observation[];
    latest_value: number | null;
    change: number | null;
    change_units: string | null;
    previous_observation_date: string | null;
}
export interface Comparison {
    series: {
        id: string;
        name: string;
        units: string;
        transformation: Transformation;
        observations: Observation[];
    }[];
    datasets: Dataset[];
    statistics: {
        left: string;
        right: string;
        transformations: Transformation[];
        frequency: string;
        alignment: string;
        missing_periods: number;
        rolling_window: number;
        rolling: Observation[];
        observations: number;
        correlation: number | null;
        start: string | null;
        end: string | null;
    }[];
    alignment: string;
    warnings: string[];
    raw_observations: Record<string, Observation[]>;
}
export interface Investigation {
    id: string;
    title: string;
    datasets: string[];
    note: string;
    collection: string;
    version?: 2;
    transformations?: Record<string, Transformation>;
    start?: string;
    end?: string;
    alignment?: 'native' | 'period_end';
    rolling_window?: number;
}
export async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> { const r = await fetch(`/api/v2/${path}`, { method: body ? 'POST' : 'GET', body: body ? JSON.stringify(body) : undefined, headers: { 'Content-Type': 'application/json' }, signal }); const json = await r.json(); if (!r.ok)
    throw Error(typeof json.detail === 'string' ? json.detail : 'Invalid research request'); return json; }
