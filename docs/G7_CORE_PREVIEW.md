# Private G7 core preview

Run from the repository root with the backend dependencies installed. Place the eleven development receipts produced by the G7 capture commands in one local directory. Each filename must be its mapping ID plus `.json`:

- `G7-CA-01`, `G7-CA-11`, `G7-CA-22`, `G7-CA-23`
- `G7-GB-23`, `G7-DE-23`, `G7-FR-23`, `G7-IT-23`
- `G7-JP-01`, `G7-JP-11`, `G7-JP-23`

```sh
python -m scripts.serve_g7_core_preview /path/to/receipts /path/to/new-workspace
```

From `frontend-v2`, start the existing frontend locally:

```sh
MACROLENS_V2_API_URL=http://127.0.0.1:8140 npm run dev -- --hostname 127.0.0.1
```

Open Dataset Explorer and select the **G7 core** category. The API filter is
`/api/v2/catalog?category=G7%20core`. Native observation previews and comparisons
use the same application endpoints as the regular dataset explorer. The preview
builds a new SQLite database and content-addressed snapshots. It preserves
publisher nulls and carries receipt hashes through the native ingestion engine.

This loopback preview contains the eleven new histories. The existing release
database and the six CPI development histories are separate. Legacy metadata
remains visible, while legacy provider fetching, scheduled refresh, and AI are
disabled. Rights review remains pending. Use private local development only.
