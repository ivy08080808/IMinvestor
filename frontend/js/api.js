// REST client. One function per endpoint in docs/API.md — pages must call
// these instead of fetch() so the contract lives in one file.
import { API_BASE } from './config.js';
import { auth } from './store.js';

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
  get notImplemented() { return this.status === 501; }
}

async function request(method, path, { body, query } = {}) {
  const url = new URL(API_BASE + path);
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
  });
  const headers = { 'Content-Type': 'application/json' };
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;

  let resp;
  try {
    resp = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch (e) {
    throw new ApiError(0, 'NETWORK', '無法連線到後端，請確認後端已啟動。');
  }
  const data = resp.status === 204 ? null : await resp.json().catch(() => null);
  if (!resp.ok) {
    if (resp.status === 401) auth.logout();
    const err = data && data.error;
    const detail = data && data.detail;  // FastAPI validation errors (422)
    throw new ApiError(
      resp.status,
      err ? err.code : 'HTTP_' + resp.status,
      err ? err.message : (Array.isArray(detail) ? detail.map(d => d.msg).join('；') : resp.statusText),
    );
  }
  return data;
}

export const api = {
  // auth
  register: (body) => request('POST', '/api/auth/register', { body }),
  login: (body) => request('POST', '/api/auth/login', { body }),
  me: () => request('GET', '/api/auth/me'),
  changePassword: (body) => request('POST', '/api/auth/password', { body }),

  // market clock
  marketStatus: () => request('GET', '/api/market/status'),

  // securities & quotes
  searchSecurities: (q, limit = 20) => request('GET', '/api/securities', { query: { q, limit } }),
  quotes: (ids) => request('GET', '/api/securities/quotes', { query: { ids: ids.join(',') } }),
  quote: (id) => request('GET', `/api/securities/${encodeURIComponent(id)}/quote`),
  history: (id, from, to) => request('GET', `/api/securities/${encodeURIComponent(id)}/history`, { query: { from, to } }),
  orderRule: (id) => request('GET', `/api/securities/${encodeURIComponent(id)}/order-rule`),

  // watchlist
  watchlist: () => request('GET', '/api/watchlist'),
  addWatch: (security_id) => request('POST', '/api/watchlist', { body: { security_id } }),
  removeWatch: (id) => request('DELETE', `/api/watchlist/${encodeURIComponent(id)}`),

  // trading
  placeOrder: (body) => request('POST', '/api/orders', { body }),
  cancelOrder: (orderId) => request('POST', `/api/orders/${orderId}/cancel`),
  orders: (status, limit = 50, offset = 0) => request('GET', '/api/orders', { query: { status, limit, offset } }),
  trades: (limit = 50, offset = 0) => request('GET', '/api/trades', { query: { limit, offset } }),
  account: () => request('GET', '/api/account'),
  portfolio: () => request('GET', '/api/portfolio'),

  // admin
  admin: {
    securities: (q, limit = 50, offset = 0) => request('GET', '/api/admin/securities', { query: { q, limit, offset } }),
    createSecurity: (body) => request('POST', '/api/admin/securities', { body }),
    updateSecurity: (id, body) => request('PATCH', `/api/admin/securities/${encodeURIComponent(id)}`, { body }),
    calendar: (from, to) => request('GET', '/api/admin/calendar', { query: { from, to } }),
    setCalendarDay: (body) => request('PUT', '/api/admin/calendar', { body }),
    users: (q, limit = 50, offset = 0) => request('GET', '/api/admin/users', { query: { q, limit, offset } }),
    setAccountStatus: (userId, status) => request('PUT', `/api/admin/users/${userId}/status`, { body: { status } }),
    userPortfolio: (userId) => request('GET', `/api/admin/users/${userId}/portfolio`),
    userOrders: (userId, status) => request('GET', `/api/admin/users/${userId}/orders`, { query: { status } }),
    userTrades: (userId) => request('GET', `/api/admin/users/${userId}/trades`),
    securityStats: (from, to, limit = 50) => request('GET', '/api/admin/stats/securities', { query: { from, to, limit } }),
    settlementRuns: (limit = 30) => request('GET', '/api/admin/settlement-runs', { query: { limit } }),
  },
};
