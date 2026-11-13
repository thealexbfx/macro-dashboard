type Row = {date: string; value: number | null};

export function summarizeObservations(rows: Row[]) {
    const byDate = new Map<string, number>();
    for (const row of rows) {
        if (!/^\d{4}-\d{2}-\d{2}$/.test(row.date) || row.value === null || !Number.isFinite(row.value)) continue;
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
