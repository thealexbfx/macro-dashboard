import type {Investigation, Transformation, WorkspaceSettings} from './contracts';

export interface DiscoveryFinding {
    id:string;type:'unusual'|'correlation'|'divergence';label:string;classification:string;
    headline:string;datasets:string[];observation_date:string;frequency:string;rationale:string;
    evidence:{observation_date:string;baseline:{start:string;end:string;observations:number;expected:number;missing:number;completeness:number};recent?:{start:string;end:string;observations:number;expected:number;missing:number;completeness:number};movement?:number;units?:string;display_movement?:number;display_units?:string;standardized_magnitude?:number;absolute_movement_percentile?:number;recent_correlation?:number;baseline_correlation?:number;correlation_difference?:number;divergence_z?:number;absolute_divergence_percentile?:number;method:string;[key:string]:unknown};
    ranking:{score:number;components:Record<string,number>;meaning:string};
    configuration:{datasets:string[];transformations:Record<string,Transformation>;start:string;end:string;timeframe:string;alignment:'native'|'period_end';rolling_window:number;workspace:WorkspaceSettings};
    preview:{id:string;name:string;units:string;observations:{date:string;value:number|null}[]}[];
    sources:{id:string;name:string;source:string;url:string;latest_observation_date:string;retrieved_at:string;publication_date:string|null;revision_count:number;verification?:{status?:string;limitation?:string};limitations:string[]}[];
    limitations:string[];methodology_version:string;
}
export interface DiscoveryReport {
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
