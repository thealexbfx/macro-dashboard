type Row = {date: string; value: number | null};

function isReferenceDate(date: string) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
    const parsed = new Date(date);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
}

export function summarizeObservations(rows: Row[]) {
    const byDate = new Map<string, number>();
    for (const row of rows) {
        if (!isReferenceDate(row.date) || row.value === null || !Number.isFinite(row.value)) continue;
        const known = byDate.get(row.date);
        if (known !== undefined && known !== row.value) return null;
        byDate.set(row.date, row.value);
    }
    const [latest, previous] = [...byDate].sort(([a], [b]) => b.localeCompare(a));
    if (!latest || !previous) return null;
    const change = latest[1] - previous[1];
    if (!Number.isFinite(change)) return null;
    return {latest: {date: latest[0], value: latest[1]}, previous: {date: previous[0], value: previous[1]}, change};
}

export function relativeChange(evidence: NonNullable<ReturnType<typeof summarizeObservations>>) {
    if (evidence.previous.value <= 0 || evidence.latest.value <= 0) return null;
    const percent = (evidence.change / evidence.previous.value) * 100;
    return Number.isFinite(percent) ? percent : null;
}
