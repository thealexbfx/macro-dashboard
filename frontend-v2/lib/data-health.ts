export type HealthRow = {
  id: string; name: string; provider: string; frequency: string;
  last_success: string | null; last_check: string | null;
  next_check: string | null; latest_observation_date: string | null;
  health: string; failures: number; error_code: string | null;
};
export type DataHealth = {
  as_of: string;
  summary: { public: number; automatic_refresh: number; verified_automatic_refresh: number; healthy: number; needs_attention: number };
  items: HealthRow[]; total: number; next_offset: number | null;
  resources: { sqlite_bytes: Record<string, number>; free_disk_bytes: number; disk_attention: boolean; 'memory.current': string | null; 'memory.max': string | null };
};
export function healthLabel(state: string): string {
  return ({ healthy: 'Healthy', source_failure: 'Source check failed', never_verified: 'Awaiting first successful check', refresh_disabled: 'Refresh inactive', check_overdue: 'Source check overdue', source_lag_review: 'Review source publication lag' } as Record<string, string>)[state] || 'Needs review';
}
export function displayTime(value: string | null): string {
  if (!value) return 'Not recorded';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Unknown' : date.toISOString().replace('T', ' ').replace('.000Z', ' UTC');
}
