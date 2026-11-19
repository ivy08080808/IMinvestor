// Global reactive state: login session and the latest market status.
import { reactive } from './vue.js';

const KEY = 'iminvestor.session';

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
}

export const auth = reactive({
  token: load().token || null,
  user: load().user || null,
  get isLoggedIn() { return !!this.token; },
  get isAdmin() { return this.user && this.user.role === 'Admin'; },
  login({ access_token, user }) {
    this.token = access_token;
    this.user = user;
    market.account = null;
    try { localStorage.setItem(KEY, JSON.stringify({ token: access_token, user })); } catch { /* private mode */ }
  },
  logout() {
    this.token = null;
    this.user = null;
    market.account = null;   // don't leak the previous user's cash into the next session
    try { localStorage.removeItem(KEY); } catch { /* ignore */ }
  },
});

// Updated by the status bar every POLL_MS; pages may read it (e.g. order panel).
export const market = reactive({ status: null, account: null, tick: 0 });
