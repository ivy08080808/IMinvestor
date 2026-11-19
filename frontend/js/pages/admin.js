// Admin (業務經營者) pages. Owner: 模組 D (UI) — data comes from the API only.
import { ref, watch } from '../vue.js';
import { api } from '../api.js';
import { useLoader } from '../useLoader.js';
import { ErrorBox } from '../components.js';
import { CATEGORIES, SECURITY_STATUS, ACCOUNT_STATUS } from '../constants.js';
import { money, dt, pct, isoDate } from '../format.js';

export const AdminSecuritiesPage = {
  components: { ErrorBox },
  setup() {
    const q = ref('');
    const list = useLoader(() => api.admin.securities(q.value));
    const form = ref({ security_id: '', security_name: '', category_id: 1, status: SECURITY_STATUS.ACTIVE });
    const error = ref(null);
    async function create() {
      error.value = null;
      try { await api.admin.createSecurity(form.value); list.reload(); } catch (e) { error.value = e; }
    }
    async function toggle(s) {
      error.value = null;
      const status = s.status === SECURITY_STATUS.ACTIVE ? SECURITY_STATUS.DISABLED : SECURITY_STATUS.ACTIVE;
      try { await api.admin.updateSecurity(s.security_id, { status }); list.reload(); } catch (e) { error.value = e; }
    }
    async function setCategory(s, category_id) {
      error.value = null;
      try { await api.admin.updateSecurity(s.security_id, { category_id: Number(category_id) }); list.reload(); }
      catch (e) { error.value = e; }
    }
    return { q, list, form, create, toggle, setCategory, error, CATEGORIES };
  },
  template: `
    <div><h2>證券管理</h2>
      <form class="form-row" @submit.prevent="list.reload()"><input v-model="q" placeholder="代號或名稱"><button>查詢</button></form>
      <div class="card"><h3>新增證券</h3>
        <form class="form-row" @submit.prevent="create">
          <input v-model="form.security_id" placeholder="代號" required maxlength="10">
          <input v-model="form.security_name" placeholder="名稱" required maxlength="50">
          <select v-model.number="form.category_id"><option v-for="c in CATEGORIES" :key="c.id" :value="c.id">{{ c.name }}</option></select>
          <button>新增</button></form></div>
      <ErrorBox :error="list.error.value" /><ErrorBox :error="error" />
      <table v-if="list.data.value"><thead><tr><th>代號</th><th>名稱</th><th>類別</th><th>狀態</th><th></th></tr></thead>
        <tbody><tr v-for="s in list.data.value" :key="s.security_id">
          <td>{{ s.security_id }}</td><td>{{ s.security_name }}</td>
          <td><select :value="s.category_id" @change="setCategory(s, $event.target.value)">
            <option v-for="c in CATEGORIES" :key="c.id" :value="c.id">{{ c.name }}</option></select></td>
          <td>{{ s.status }}</td>
          <td><button class="link" @click="toggle(s)">{{ s.status === '啟用' ? '停用' : '啟用' }}</button></td></tr></tbody></table>
    </div>`,
};

export const AdminCalendarPage = {
  components: { ErrorBox },
  setup() {
    const from = ref(isoDate(new Date()));
    const to = ref(isoDate(new Date(Date.now() + 60 * 864e5)));
    const list = useLoader(() => api.admin.calendar(from.value, to.value));
    const error = ref(null);
    async function toggle(day) {
      error.value = null;
      try {
        await api.admin.setCalendarDay({ calendar_date: day.calendar_date, is_trading_day: !day.is_trading_day });
        list.reload();
      } catch (e) { error.value = e; }
    }
    return { from, to, list, toggle, error };
  },
  template: `
    <div><h2>交易日曆</h2>
      <form class="form-row" @submit.prevent="list.reload()">
        <label>從 <input type="date" v-model="from"></label><label>到 <input type="date" v-model="to"></label><button>查詢</button></form>
      <ErrorBox :error="list.error.value" /><ErrorBox :error="error" />
      <table v-if="list.data.value"><thead><tr><th>日期</th><th>交易日</th><th></th></tr></thead>
        <tbody><tr v-for="d in list.data.value" :key="d.calendar_date">
          <td>{{ d.calendar_date }}</td><td>{{ d.is_trading_day ? '是' : '休市' }}</td>
          <td><button class="link" @click="toggle(d)">{{ d.is_trading_day ? '設為休市' : '設為交易日' }}</button></td></tr></tbody></table>
    </div>`,
};

export const AdminUsersPage = {
  components: { ErrorBox },
  setup() {
    const q = ref('');
    const list = useLoader(() => api.admin.users(q.value));
    const selected = ref(null);
    const detail = ref(null);
    const error = ref(null);
    async function toggle(u) {
      error.value = null;
      const status = u.account_status === ACCOUNT_STATUS.ACTIVE ? ACCOUNT_STATUS.FROZEN : ACCOUNT_STATUS.ACTIVE;
      try { await api.admin.setAccountStatus(u.user_id, status); list.reload(); } catch (e) { error.value = e; }
    }
    async function open(u) {
      selected.value = u; detail.value = null; error.value = null;
      try {
        const [portfolio, orders, trades] = await Promise.all([
          api.admin.userPortfolio(u.user_id), api.admin.userOrders(u.user_id), api.admin.userTrades(u.user_id)]);
        detail.value = { portfolio, orders, trades };
      } catch (e) { error.value = e; }
    }
    return { q, list, toggle, open, selected, detail, error, money, dt };
  },
  template: `
    <div><h2>使用者管理</h2>
      <p class="muted">系統不提供刪除使用者；停用帳戶請使用「凍結」，交易紀錄完整保留。</p>
      <form class="form-row" @submit.prevent="list.reload()"><input v-model="q" placeholder="名稱或信箱"><button>查詢</button></form>
      <ErrorBox :error="list.error.value" /><ErrorBox :error="error" />
      <table v-if="list.data.value"><thead><tr><th>ID</th><th>名稱</th><th>信箱</th><th>角色</th><th>帳戶</th><th>可用</th><th>凍結</th><th></th></tr></thead>
        <tbody><tr v-for="u in list.data.value" :key="u.user_id">
          <td>{{ u.user_id }}</td><td><a href="" @click.prevent="open(u)">{{ u.user_name }}</a></td><td>{{ u.email }}</td><td>{{ u.role }}</td>
          <td>{{ u.account_status || '—' }}</td><td>{{ money(u.available_cash) }}</td><td>{{ money(u.frozen_cash) }}</td>
          <td><button v-if="u.account_status" class="link" @click="toggle(u)">{{ u.account_status === '啟用' ? '凍結' : '解凍' }}</button></td></tr></tbody></table>
      <div class="card" v-if="selected && detail">
        <h3>{{ selected.user_name }}：總資產 {{ money(detail.portfolio.total_assets) }}</h3>
        <p>持股 {{ detail.portfolio.holdings.length }} 檔｜委託 {{ detail.orders.length }} 筆｜成交 {{ detail.trades.length }} 筆</p>
      </div>
    </div>`,
};

export const AdminStatsPage = {
  components: { ErrorBox },
  setup() {
    const from = ref(isoDate(new Date(Date.now() - 30 * 864e5)));
    const to = ref(isoDate(new Date()));
    const list = useLoader(() => api.admin.securityStats(from.value, to.value));
    return { from, to, list, money, pct };
  },
  template: `
    <div><h2>全站交易統計</h2>
      <form class="form-row" @submit.prevent="list.reload()">
        <label>從 <input type="date" v-model="from"></label><label>到 <input type="date" v-model="to"></label><button>查詢</button></form>
      <ErrorBox :error="list.error.value" />
      <table v-if="list.data.value"><thead><tr><th>證券</th><th>委託數</th><th>成交數</th><th>委託成交率</th><th>成交股數</th></tr></thead>
        <tbody><tr v-for="s in list.data.value" :key="s.security_id">
          <td>{{ s.security_id }} {{ s.security_name }}</td><td>{{ money(s.order_count) }}</td><td>{{ money(s.filled_count) }}</td>
          <td>{{ pct(s.fill_rate === null ? null : s.fill_rate * 100) }}</td><td>{{ money(s.filled_shares) }}</td></tr></tbody></table>
    </div>`,
};

export const AdminSettlementPage = {
  components: { ErrorBox },
  setup() { return { list: useLoader(() => api.admin.settlementRuns()), dt, money }; },
  template: `
    <div><h2>每日自動結算紀錄</h2>
      <p class="muted">每個交易日 15:00 系統自動抓取當日行情一次並結算，無手動操作。</p>
      <ErrorBox :error="list.error.value" />
      <table v-if="list.data.value"><thead><tr><th>交易日</th><th>狀態</th><th>開始</th><th>結束</th>
        <th>匯入行情</th><th>成交</th><th>失效</th><th>訊息</th></tr></thead>
        <tbody><tr v-for="r in list.data.value" :key="r.trade_date">
          <td>{{ r.trade_date }}</td><td>{{ r.status }}</td><td>{{ dt(r.started_at) }}</td><td>{{ dt(r.finished_at) }}</td>
          <td>{{ money(r.price_rows) }}</td><td>{{ money(r.filled_count) }}</td><td>{{ money(r.expired_count) }}</td>
          <td>{{ r.message || '' }}</td></tr>
          <tr v-if="!list.data.value.length"><td colspan="8" class="muted">尚無紀錄</td></tr></tbody></table>
    </div>`,
};
