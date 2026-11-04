export type Transformation = 'level' | 'percent' | 'yoy' | 'mom' | 'pp' | 'indexed' | 'standardized' | 'jobs';
export const transformLabels: Record<Transformation, string> = { level: 'Original levels', percent: 'Percentage change', yoy: 'Year-over-year %', mom: 'Month-over-month %', pp: 'Percentage-point change', indexed: 'Indexed to 100', standardized: 'Standardized deviations', jobs: 'Monthly jobs added/lost' };
export function transformationLabel(mode:Transformation,horizon=1):string { return horizon>1&&mode==='mom'?'Multi-period percentage change':horizon>1&&mode==='jobs'?'Multi-period net employment change':transformLabels[mode]; }
export interface Observation {
    date: string;
    value: number | null;
    key?: string; native_label?: string; period_start?:string; period_end?:string; event_id?:string|null; source_flags?:string[]; release_at?:string|null; revision?:number;
}
export type ChartMode = 'overlay' | 'separate' | 'scatter';
export type ChartType = 'line' | 'area' | 'bar' | 'scatter';
export interface LeadLag { dataset_id: string; periods: number; unit: 'months' | 'quarters' | 'calendar_days' | 'weeks' }
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
    native_storage?:boolean;
    native_history_start?:string|null;
    native_calendar?:Record<string,unknown>;
    latest_native_label?:string;
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
    stored_provenance?: {attribution:string[];license_url:string;benchmark:string;source_unit:string;stored_start:string;stored_end:string;reference_convention:string;ai_allowed:false} | null;
    provider_metadata?:Record<string,unknown>;
    revision_count?:number;
    market_movement?:{value:number|null;unit:string;label:string;previous_date?:string;reference_date?:string;calculation_status?:string};
}
export interface Comparison {
    provenance?: CalculationReceipt | null;
    series: {
        native_frequency?: string;
        horizon_observations?: number;
        observation_basis?: string;
        calendar_quality?: Record<string,unknown>;
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
    horizons?: Record<string,number>;
    observation_basis?: 'native' | 'trading_sessions';
    historical_context?: import('./discovery').HistoricalRecord;
    discovery?: import('./discovery').DiscoverySnapshot;
    id: string;
    title: string;
    datasets: string[];
    note: string;
    collection: string;
    version?: 2 | 3 | 4;
    research_question?: string;
    workspace?: WorkspaceSettings;
    timeframe?: string;
    transformations?: Record<string, Transformation>;
    start?: string;
    end?: string;
    alignment?: 'native' | 'period_end';
    rolling_window?: number;
}
export interface CalculationReceipt {
    schema_version: 1;
    method_version: string;
    calculated_at: string;
    parameters: Record<string, unknown>;
    parameter_fingerprint: string;
    result_fingerprint: string;
    datasets: {dataset_id:string;provider:string|null;source_identifier:string|null;source_url:string|null;definition_identifier:string;definition_identifier_kind:string;units:string;frequency:string;seasonal_adjustment:string|null;retrieved_at:string|null;source_checked_at:string|null;generation_references:string[];generation_reference_count:number;input_fingerprint:string;input_count:number;input_start:string|null;input_end:string|null;input_scope:string}[];
    effective_ranges: {dataset_id:string;start:string|null;end:string|null;units:string;transformation:string}[];
    statistics: Record<string, unknown>[];
    limitations: string[];
    exact_replay: {available:false;reason:string};
}
export interface EvidenceReference {
    id:string; dataset_ids:string[]; start:string|null; end:string|null;
    calculation_fingerprint:string|null; note:string;
    capture?: {
        attached_at:string; dataset_labels:Record<string,string>; timeframe:string;
        workspace:WorkspaceSettings; receipt:CalculationReceipt;
    };
}
export interface InvestigationV4 extends Investigation {
    version:4; research_question:string; working_hypothesis:string;
    supporting_evidence:EvidenceReference[]; contradictory_evidence:EvidenceReference[];
    alternative_explanations:string; limitations_and_uncertainty:string;
    conclusion:string; created_at:string|null; updated_at:string|null;
    migrated_at:string|null; revision:number;
    workspace:WorkspaceSettings; transformations:Record<string,Transformation>;
    horizons:Record<string,number>; observation_basis:'native'|'trading_sessions';
    start:string; end:string; timeframe:string; alignment:'native'|'period_end';
    rolling_window:number; window_explicit:boolean;
    original_calculation:CalculationReceipt|null; saved_calculation:CalculationReceipt|null;
}
async function retryDelay(milliseconds: number, signal?: AbortSignal) {
    signal?.throwIfAborted();
    return new Promise<void>((resolve,reject)=>{
        const abort=()=>{clearTimeout(timer);reject(signal?.reason);};
        const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve();},milliseconds);
        signal?.addEventListener('abort',abort,{once:true});
    });
}
export async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    // Retry only rejected reads/pure comparisons, never refresh or administrative actions.
    const retryable=(!body||path==='compare'||path==='catalog/search')&&!path.includes('/admin/');
    for(let attempt=0;;attempt++){
        signal?.throwIfAborted();
        const r=await fetch(`/api/v2/${path}`,{method:body?'POST':'GET',body:body?JSON.stringify(body):undefined,headers:{'Content-Type':'application/json'},signal});
        const json=await r.json();
        const retryAfter=r.headers.get('retry-after');
        if(retryable&&attempt<2&&[429,503].includes(r.status)&&retryAfter!==null&&Number.isFinite(Number(retryAfter))){
            await retryDelay(Math.max(0,Math.min(5,Number(retryAfter)))*1000,signal);
            continue;
        }
        if(!r.ok)throw Error(typeof json.detail==='string'?json.detail:'Invalid research request');
        return json;
    }
}
