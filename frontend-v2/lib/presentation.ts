import type { Dataset, Observation } from './contracts';
export const TIMEFRAMES = ['1M', '3M', 'YTD', '1Y', '3Y', '5Y', '10Y', 'MAX'] as const;
export type Timeframe = typeof TIMEFRAMES[number];
export const HISTORY_FLOOR = '1990-01-01';
export function timeframeStart(timeframe: Timeframe, end: string): string {
    if (timeframe === 'MAX')
        return HISTORY_FLOOR;
    const date = new Date(`${end}T00:00:00Z`);
    if (Number.isNaN(date.getTime()))
        throw new Error('Invalid end date');
    if (timeframe === 'YTD')
        return `${date.getUTCFullYear()}-01-01`;
    const months = ({ '1M': 1, '3M': 3, '1Y': 12, '3Y': 36, '5Y': 60, '10Y': 120 } as const)[timeframe];
    const day = date.getUTCDate();
    date.setUTCDate(1);
    date.setUTCMonth(date.getUTCMonth() - months);
    const lastDay = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
    date.setUTCDate(Math.min(day, lastDay));
    return date.toISOString().slice(0, 10) < HISTORY_FLOOR ? HISTORY_FLOOR : date.toISOString().slice(0, 10);
}
export function formatNumber(value: number | null | undefined, digits = 2): string {
    return value === null || value === undefined || !Number.isFinite(value) ? 'Unavailable' : value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
export function formatDatasetValue(d: Dataset): string {
    if (d.status === 'unavailable')
        return 'Unavailable';
    const digits = ['payrolls','initial_claims','job_openings','housing_starts','building_permits','retail_sales'].includes(d.id) ? 0 : d.id === 'unemployment' || d.id === 'real_gdp_growth' ? 1 : 2;
    const number = formatNumber(d.latest_value, digits);
    if (d.latest_value === null)
        return number;
    if (d.units.toLowerCase().startsWith('percent'))
        return `${number}%`;
    return (d.units.startsWith('USD /')||d.id==='hourly_earnings') ? `$${number}` : number;
}
export function dateLabel(value: string | null | undefined): string {
    if (!value)
        return 'Date unavailable';
    const date = new Date(value.includes('T')?value:`${value}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}
export function referenceLabel(d: Dataset): string {
    if(d.latest_native_label)return d.latest_native_label;
    if (!d.latest_observation_date)
        return 'Reference unavailable';
    if (d.frequency === 'quarterly')
        return `Q${Math.floor((Number(d.latest_observation_date.slice(5, 7)) - 1) / 3) + 1} ${d.latest_observation_date.slice(0, 4)}`;
    if (d.frequency === 'monthly')
        return new Date(`${d.latest_observation_date}T00:00:00Z`).toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
    return dateLabel(d.latest_observation_date);
}
export function freshness(d: Dataset | undefined): string {
    if (!d || d.status === 'unavailable' || d.latest_value === null || !d.latest_observation_date)
        return 'Unavailable';
    return d.status === 'stale' ? 'Stale data' : d.frequency === 'daily' ? 'Delayed data' : 'Latest available';
}
export function marketMovement(d: Dataset): {
    value: number | null;
    unit: string;
    label: string;
} {
    const unit=d.representation==='rate'?'bp':'%';
    if(d.status==='unavailable'||d.latest_value===null||!d.market_movement||!d.previous_observation_date||!d.observations.some(o=>o.date===d.previous_observation_date))return {value:null,unit,label:'Server-validated change unavailable'};
    return d.market_movement;
}
export function formatHeadlineValue(d:Dataset):string{
    const h=d.headline;
    if(d.status==='unavailable'||!h||h.value==null||!h.units)return 'Unavailable';
    if(h.transformation==='jobs')return `${h.value>0?'+':''}${formatNumber(h.value,0)}`;
    return `${formatNumber(h.value,d.id==='fed_funds'?2:1)}${h.units.toLowerCase().startsWith('percent')?'%':''}`;
}

export function recentObservations(d: Dataset): Observation[] {
    return d.status === 'unavailable' || !d.latest_observation_date ? [] : d.observations.filter(o => o.date <= d.latest_observation_date!).slice(-22);
}

// Compact session view only; analytical inputs retain every missing cell.
export function sparklineObservations(d: Dataset): Observation[] {
    return recentObservations(d).filter(o => o.value !== null && Number.isFinite(o.value));
}
export const tooltipNumber = (value: unknown): string =>
    typeof value === 'number' ? formatNumber(value, 2) : 'Unavailable';
export function defaultRollingWindow(frequency: string): number {
    return frequency === 'daily' ? 60 : frequency === 'weekly' ? 26 : 12;
}
export function correlationInterpretation(value: number | null): string {
    if (value === null || !Number.isFinite(value)) return 'Not enough overlapping, varying observations to measure a relationship.';
    const strength = Math.abs(value) < .2 ? 'Little linear relationship' : Math.abs(value) < .4 ? 'A weak linear relationship' : Math.abs(value) < .7 ? 'A moderate linear relationship' : 'A strong linear relationship';
    return `${strength}${Math.abs(value) < .2 ? '' : value > 0 ? ': the series tended to move together' : ': the series tended to move in opposite directions'} over this period. This does not establish causation.`;
}

/** Presentation only: visibility is enforced by backend rights and registry checks. */
export function storedSourceDetails(d: Dataset): [string, string][] {
    const p = d.stored_provenance;
    if (!p) return [];
    return [
        ['Benchmark', p.benchmark],
        ['Attribution', p.attribution.join('; ')],
        ['Source unit', p.source_unit],
        ['Stored reference coverage', p.stored_start + ' – ' + p.stored_end],
        ['Reference convention', p.reference_convention],
        ['License', p.license_url],
        ['AI use', 'Not enabled'],
    ];
}
