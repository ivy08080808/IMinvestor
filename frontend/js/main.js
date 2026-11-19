// App shell: hash router, navigation by role, status bar.
import { createApp, ref, computed, onMounted, onUnmounted } from './vue.js';
import { auth } from './store.js';
import { StatusBar } from './components.js';
import {
  LoginPage, MarketPage, SecurityPage, WatchlistPage, OrdersPage, TradesPage, PortfolioPage,
} from './pages/user.js';
import {
  AdminSecuritiesPage, AdminCalendarPage, AdminUsersPage, AdminStatsPage, AdminSettlementPage,
} from './pages/admin.js';

// path pattern -> { component, role } ; role: null = public, 'User', 'Admin', 'any'
const ROUTES = [
  { path: '/login', component: LoginPage, role: null },
  { path: '/market', component: MarketPage, role: 'any' },
  { path: '/security/:id', component: SecurityPage, role: 'any' },
  { path: '/watchlist', component: WatchlistPage, role: 'User' },
  { path: '/orders', component: OrdersPage, role: 'User' },
  { path: '/trades', component: TradesPage, role: 'User' },
  { path: '/portfolio', component: PortfolioPage, role: 'User' },
  { path: '/admin/securities', component: AdminSecuritiesPage, role: 'Admin' },
  { path: '/admin/calendar', component: AdminCalendarPage, role: 'Admin' },
  { path: '/admin/users', component: AdminUsersPage, role: 'Admin' },
  { path: '/admin/stats', component: AdminStatsPage, role: 'Admin' },
  { path: '/admin/settlement', component: AdminSettlementPage, role: 'Admin' },
];

const NAV = {
  User: [['#/market', '行情'], ['#/watchlist', '自選股'], ['#/portfolio', '庫存'], ['#/orders', '委託'], ['#/trades', '成交／資金']],
  Admin: [['#/market', '行情'], ['#/admin/securities', '證券'], ['#/admin/calendar', '交易日曆'],
          ['#/admin/users', '使用者'], ['#/admin/stats', '統計'], ['#/admin/settlement', '自動結算']],
};

function match(hashPath) {
  for (const r of ROUTES) {
    const keys = [];
    const re = new RegExp('^' + r.path.replace(/:(\w+)/g, (_, k) => { keys.push(k); return '([^/]+)'; }) + '$');
    const m = hashPath.match(re);
    if (m) return { route: r, params: Object.fromEntries(keys.map((k, i) => [k, decodeURIComponent(m[i + 1])])) };
  }
  return null;
}

const App = {
  components: { StatusBar },
  setup() {
    const path = ref(location.hash.slice(1) || '/market');
    const onHash = () => { path.value = location.hash.slice(1) || '/market'; };
    onMounted(() => window.addEventListener('hashchange', onHash));
    onUnmounted(() => window.removeEventListener('hashchange', onHash));

    const current = computed(() => {
      const m = match(path.value) || match('/market');
      const role = m.route.role;
      if (role && !auth.isLoggedIn) return match('/login');
      if (role === 'User' && auth.isAdmin) return match('/admin/securities');
      if (role === 'Admin' && !auth.isAdmin) return match('/market');
      return m;
    });
    const nav = computed(() => (auth.user ? NAV[auth.user.role] : []));
    function logout() { auth.logout(); location.hash = '#/login'; }
    return { current, nav, auth, logout, path };
  },
  template: `
    <header>
      <div class="brand">IMinvestor</div>
      <nav><a v-for="[href, label] in nav" :key="href" :href="href" :class="{active: '#' + path === href}">{{ label }}</a></nav>
      <div class="user" v-if="auth.user">{{ auth.user.user_name }}（{{ auth.user.role }}）<button class="link" @click="logout">登出</button></div>
    </header>
    <StatusBar />
    <main><component :is="current.route.component" v-bind="current.params" :key="path" /></main>`,
};

createApp(App).mount('#app');
