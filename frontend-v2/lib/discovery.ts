import type {Investigation, Transformation, WorkspaceSettings} from './contracts';

export interface DiscoveryFinding {
    summary?:string;key_number?:string;horizon_label?:string;horizon_observations?:number;
    evidence_version?:number;evidence_fingerprint?:string;
    primary_preview?:DiscoveryPreview;
    lifecycle?:{status:'New'|'Updated'|'Ongoing'|'Archived';first_detected:string;last_meaningful_update:string;last_seen_qualifying:string;qualifies_now:boolean;what_changed:string;related_discoveries:string[]};
    history?:{version:number;detected_at:string;reason:string;headline:string;evidence:Record<string,unknown>}[];
    current_source_status?:Record<string,string>;
    suggestions?:ResearchSuggestion[];
    alternative_timeframes?:{label:string;horizon_observations:number;headline:string;summary:string;key_number:string;evidence:DiscoveryFinding['evidence'];configuration:DiscoveryFinding['configuration']}[];
    id:string;type:'unusual'|'correlation'|'divergence';label:string;classification:string;
    headline:string;datasets:string[];observation_date:string;frequency:string;rationale:string;
    evidence:{observation_date:string;baseline:{start:string;end:string;observations:number;expected:number;missing:number;completeness:number};recent?:{start:string;end:string;observations:number;expected:number;missing:number;completeness:number};movement?:number;units?:string;display_movement?:number;display_units?:string;standardized_magnitude?:number;absolute_movement_percentile?:number;recent_correlation?:number;baseline_correlation?:number;correlation_difference?:number;divergence_z?:number;absolute_divergence_percentile?:number;method:string;[key:string]:unknown};
    ranking:{score:number;components:Record<string,number>;meaning:string};
    configuration:{horizons?:Record<string,number>;observation_basis?:'native'|'trading_sessions';datasets:string[];transformations:Record<string,Transformation>;start:string;end:string;timeframe:string;alignment:'native'|'period_end';rolling_window:number;workspace:WorkspaceSettings};
    preview:{id:string;name:string;units:string;observations:{date:string;value:number|null}[]}[];
    sources:{id:string;name:string;source:string;url:string;latest_observation_date:string;retrieved_at:string;publication_date:string|null;revision_count:number;verification?:{status?:string;limitation?:string};limitations:string[]}[];
    limitations:string[];methodology_version:string;
}
export interface DiscoveryReport {
    archived_total?:number;following_total?:number;historical_total?:number;
    following?:DiscoveryFinding[];archived?:DiscoveryFinding[];historical?:HistoricalRecord[];source_times?:{id:string;observed:string;retrieved:string;published:string|null;status:string;checked:string;next_check:string}[];
    findings:DiscoveryFinding[];as_of:string;generated_at:string;snapshot_fingerprint:string;
    qualified_before_deduplication:number;excluded:{id:string;reason:string}[];
    universe:{single_series:number;curated_pairs:number;exploratory_pairs:number;pairs:{datasets:string[];rationale:string}[];transformations:Record<string,string>};
    methodology:Record<string,string>;limitations:string[];methodology_version:string;
}
export interface DiscoverySnapshot {finding:DiscoveryFinding;generated_at:string;snapshot_fingerprint:string}
export function discoveryInvestigation(finding:DiscoveryFinding,report:Pick<DiscoveryReport,'generated_at'|'snapshot_fingerprint'>,id:string,note=''):Investigation {
    // Clone the complete evidence/configuration so future revisions cannot alter this snapshot.
    return structuredClone({id,title:finding.headline,note,collection:'Discovery Radar',version:3,
        ...finding.configuration,discovery:{finding,generated_at:report.generated_at,snapshot_fingerprint:report.snapshot_fingerprint}});
}

export interface DiscoveryPreview {id:string;name:string;units:string;observations:{date:string;value:number|null}[];missing_in_preview?:number;basis?:string}
export interface ResearchSuggestion {id:string;label:string;origin:string;context:string;configuration:DiscoveryFinding['configuration']}
export interface HistoricalPattern {observations:{date:string;value:number|null}[];units:string;required:number}
export interface HistoricalRecord {id:string;label:string;created_at:string;notes:string;snapshot:{finding:DiscoveryFinding;pattern:HistoricalPattern;captured_at:string};current_pattern:HistoricalPattern|null;similarity:{matches:boolean;reason:string;shape_correlation?:number;standardized_rmse?:number;amplitude_ratio?:number;then_last_change?:number;now_last_change?:number};comparison_configuration:DiscoveryFinding['configuration']|null}
export function suggestionInvestigation(finding:DiscoveryFinding,suggestion:ResearchSuggestion,report:Pick<DiscoveryReport,'generated_at'|'snapshot_fingerprint'>,id:string):Investigation {
    return {...discoveryInvestigation(finding,report,id),...structuredClone(suggestion.configuration),title:suggestion.label,note:suggestion.origin+'. '+suggestion.context};
}

export interface DiscoverySummary {id:string;headline:string;observation_date:string;frequency:string;type:DiscoveryFinding['type'];status:string;evidence_version:number}
export interface DiscoveryPage<T> {items:T[];total:number;offset:number;next_offset:number|null}
