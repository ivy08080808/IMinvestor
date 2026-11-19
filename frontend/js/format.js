// Display helpers. Money arrives from the API as strings (Decimal); only format here.
export function money(v, digits = 0) {
  if (v === null || v === undefined || v === '') return '—';
  return Number(v).toLocaleString('zh-TW', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
export function price(v) { return money(v, 2); }
export function pct(v) {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  return (n > 0 ? '+' : '') + n.toFixed(2) + '%';
}
export function signed(v, digits = 2) {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  return (n > 0 ? '+' : '') + money(n, digits);
}
// Taiwan convention: red = up, green = down.
export function trendClass(v) {
  if (v === null || v === undefined) return '';
  const n = Number(v);
  return n > 0 ? 'up' : n < 0 ? 'down' : '';
}
export function dt(v) { return v ? String(v).replace('T', ' ').slice(0, 19) : '—'; }
export function isoDate(d) { return d.toISOString().slice(0, 10); }
