export type Transformation = 'level' | 'percent' | 'yoy' | 'mom' | 'pp' | 'indexed' | 'standardized' | 'jobs';
export const transformLabels: Record<Transformation, string> = { level: 'Original levels', percent: '% per observation', yoy: 'Year-over-year %', mom: 'Month-over-month %', pp: 'Percentage-point change', indexed: 'Indexed to 100', standardized: 'Standardized deviations', jobs: 'Monthly jobs added/lost' };
export interface Observation {
    date: string;
    value: number | null;
}
export type ChartMode = 'overlay' | 'separate' | 'scatter';
export type ChartType = 'line' | 'area' | 'bar' | 'scatter';
export interface LeadLag { dataset_id: string; periods: number; unit: 'months' | 'quarters' | 'calendar_days' }
export interface WorkspaceSettings {
    mode: ChartMode;
    chart_type: ChartType;
    layout: 'stacked' | 'grid';
    axes: 'shared' | 'dual';
    axis_assignment: Record<string, 'left' | 'right'>;
    recession: boolean;
    lead_lag: LeadLag;
    hidden: string[];
}
export interface HistoricalContext {
    kind: string; source_id: string; source: string; source_url: string;
    status: 'ok' | 'stale'; message: string | null; latest_reference: string;
    retrieved_at: string; coverage_start: string; coverage_end: string; methodology: string;
    periods: {id:string;start:string;end:string;original_start:string;original_end:string;label:string}[];
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
    provider?: string;
    definition?: string;
    source_type?: string;
    observation_type?: string;
    recommended_headline_transformation?: Transformation;
    headline_name?: string;
    primary_source_url?: string;
    freshness_expectation?: string;
    known_limitations?: string[];
    headline?: {name:string;transformation:Transformation;value:number|null;units:string;reference_period:string;seasonal_adjustment:string|null;source_dataset_id:string;calculation_status:string};
    verification?: {status:string;raw_status?:string;headline_status?:string;audit_checked_at?:string;source_url?:string;limitation?:string;headline_reconciliation?:{reference:string;release_date:string|null;published_value:number;calculated_value:number;rounded_to_release_precision:number;difference_at_release_precision:number;source_url:string;vintage_note:string}};
    quality_warnings?: string[];
    release_metadata?: {release_date?:string|null;next_release_date?:string|null;distributor_updated_at?:string|null;release_url?:string|null;audit_checked_at?:string;freshness_assessment?:string};
    provider_metadata?:Record<string,unknown>;
    revision_count?:number;
    market_movement?:{value:number|null;unit:string;label:string;previous_date?:string;reference_date?:string;calculation_status?:string};
}
export interface Comparison {
    series: {
        native_frequency?: string;
        source_dates?: Record<string, string | null>;
        shift_periods?: number;
        shift_unit?: string | null;
        id: string;
        name: string;
        units: string;
        transformation: Transformation;
        observations: Observation[];
    }[];
    scatter?: {date:string;x:number;y:number;x_source_date:string|null;y_source_date:string|null}[];
    lead_lag?: LeadLag | null;
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
        lead_lag?: LeadLag | null;
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
    version?: 2 | 3;
    workspace?: WorkspaceSettings;
    timeframe?: string;
    transformations?: Record<string, Transformation>;
    start?: string;
    end?: string;
    alignment?: 'native' | 'period_end';
    rolling_window?: number;
}
export async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> { const r = await fetch(`/api/v2/${path}`, { method: body ? 'POST' : 'GET', body: body ? JSON.stringify(body) : undefined, headers: { 'Content-Type': 'application/json' }, signal }); const json = await r.json(); if (!r.ok)
    throw Error(typeof json.detail === 'string' ? json.detail : 'Invalid research request'); return json; }
