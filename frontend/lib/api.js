const API_URL = process.env.NEXT_PUBLIC_MACROLENS_API_URL || 'http://127.0.0.1:8000';
export async function getRelationshipSeries() {
  const response = await fetch(`${API_URL}/api/research/relationships/series`);
  if (!response.ok) throw new Error('Unable to load supported research series.');
  return response.json();
}
export async function getRelationship(target, driver, timeframe, economy) {
  const query = new URLSearchParams({target, driver, timeframe, economy});
  const response = await fetch(`${API_URL}/api/research/relationships?${query}`);
  if (!response.ok) throw new Error('Relationship data is unavailable, insufficient, or unsupported.');
  return response.json();
}
export async function askMacroLens(question) {
  const response = await fetch(`${API_URL}/api/ask`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})});
  if (!response.ok) throw new Error(`MacroLens API returned ${response.status}`);
  return response.json();
}
export async function getHomeSnapshot() {
  const response = await fetch(`${API_URL}/api/home`, {cache:'no-store'});
  if (!response.ok) throw new Error(`MacroLens API returned ${response.status}`);
  return response.json();
}
