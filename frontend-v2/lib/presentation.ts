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
    const digits = d.id === 'payrolls' ? 0 : d.id === 'unemployment' || d.id === 'real_gdp_growth' ? 1 : 2;
    const number = formatNumber(d.latest_value, digits);
    if (d.latest_value === null)
        return number;
    if (d.units.toLowerCase().startsWith('percent'))
        return `${number}%`;
    return d.units.startsWith('USD /') ? `$${number}` : number;
}
export function dateLabel(value: string | null | undefined): string {
    if (!value)
        return 'Date unavailable';
    const date = new Date(`${value}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}
export function referenceLabel(d: Dataset): string {
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
    const unit = d.representation === 'rate' ? 'bp' : '%';
    if (d.status === 'unavailable' || d.latest_value === null || !d.latest_observation_date || !d.previous_observation_date)
        return { value: null, unit, label: 'Change unavailable' };
    const latest = d.observations.find(o => o.date === d.latest_observation_date)?.value;
    const previous = d.observations.find(o => o.date === d.previous_observation_date)?.value;
    if (latest === undefined || latest === null || previous === undefined || previous === null || !Number.isFinite(latest) || !Number.isFinite(previous))
        return { value: null, unit, label: 'Change unavailable' };
    // Display conversion only: yield percentage points to bp; positive price bases to %.
    if (d.representation !== 'rate' && previous <= 0)
        return { value: latest - previous, unit: d.units, label: 'Absolute change (nonpositive prior price)' };
    const value = d.representation === 'rate' ? (latest - previous) * 100 : (latest / previous - 1) * 100;
    return { value, unit, label: d.representation === 'rate' ? 'Yield change; not a bond return' : 'Change vs previous available close' };
}
export function recentObservations(d: Dataset): Observation[] {
    return d.status === 'unavailable' || !d.latest_observation_date ? [] : d.observations.filter(o => o.date <= d.latest_observation_date!).slice(-22);
}
