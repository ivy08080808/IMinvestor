// User (一般使用者) pages. Owner: 模組 D (UI) — data comes from the API only.
import { ref, computed, watch } from '../vue.js';
import { api } from '../api.js';
import { auth, market } from '../store.js';
import { useLoader } from '../useLoader.js';
import { ErrorBox, OrderPanel } from '../components.js';
import { ORDER_STATUS } from '../constants.js';
import { money, price, pct, signed, trendClass, dt, isoDate } from '../format.js';

const fmt = { money, price, pct, signed, trendClass, dt };

export const LoginPage = {
  components: { ErrorBox },
  setup() {
    const mode = ref('login');
    const form = ref({ user_name: '', email: '', password: '' });
    const error = ref(null);
    async function submit() {
      error.value = null;
      try {
        const res = mode.value === 'login'
          ? await api.login({ user_name: form.value.user_name, password: form.value.password })
          : await api.register(form.value);
        auth.login(res);
        location.hash = res.user.role === 'Admin' ? '#/admin/securities' : '#/market';
      } catch (e) { error.value = e; }
    }
    return { mode, form, error, submit };
  },
  template: `
    <div class="card narrow">
      <div class="tabs">
        <button :class="{active: mode==='login'}" @click="mode='login'">登入</button>
        <button :class="{active: mode==='register'}" @click="mode='register'">註冊</button>
      </div>
      <form @submit.prevent="submit" class="stack">
        <label>使用者名稱 <input v-model="form.user_name" required maxlength="20"></label>
        <label v-if="mode==='register'">信箱 <input v-model="form.email" type="email" required maxlength="50"></label>
        <label>密碼 <input v-model="form.password" type="password" required minlength="6"></label>
        <button type="submit">{{ mode==='login' ? '登入' : '註冊並取得 1,000,000 元虛擬資金' }}</button>
      </form>
      <ErrorBox :error="error" />
    </div>`,
};

const QuoteTable = {
  props: { rows: Array, removable: Boolean },
  emits: ['remove'],
  setup() { return fmt; },
  template: `
    <table>
      <thead><tr><th>代號</th><th>名稱</th><th>日期</th><th>昨收(參考價)</th><th>開盤</th><th>最高</th><th>最低</th>
        <th>收盤</th><th>漲跌</th><th>幅度</th><th>成交量</th><th v-if="removable"></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.security_id">
          <td><a :href="'#/security/' + r.security_id">{{ r.security_id }}</a></td>
          <td>{{ r.security_name }}</td><td>{{ r.trade_date || '—' }}</td>
          <td>{{ price(r.prev_close) }}</td>
          <td>{{ price(r.open_price) }}</td><td>{{ price(r.high_price) }}</td><td>{{ price(r.low_price) }}</td>
          <td>{{ price(r.close_price) }}</td>
          <td :class="trendClass(r.change)">{{ signed(r.change) }}</td>
          <td :class="trendClass(r.change)">{{ pct(r.change_pct) }}</td>
          <td>{{ money(r.volume) }}</td>
          <td v-if="removable"><button class="link" @click="$emit('remove', r.security_id)">移除</button></td>
        </tr>
        <tr v-if="!rows || !rows.length"><td colspan="12" class="muted">沒有資料</td></tr>
      </tbody>
    </table>`,
};

export const MarketPage = {
  components: { ErrorBox, QuoteTable },
  setup() {
    const q = ref('');
    const rows = ref([]);
    const error = ref(null);
    async function search() {
      error.value = null;
      try {
        const secs = await api.searchSecurities(q.value);
        rows.value = secs.length ? await api.quotes(secs.map(s => s.security_id)) : [];
      } catch (e) { error.value = e; }
    }
    return { q, rows, error, search };
  },
  template: `
    <div>
      <h2>行情查詢</h2>
      <form class="form-row" @submit.prevent="search">
        <input v-model="q" placeholder="輸入代號或名稱，例如 2330、台積、0050">
        <button type="submit">搜尋</button>
      </form>
      <ErrorBox :error="error" />
      <QuoteTable :rows="rows" />
      <p class="muted">顯示最新一個交易日的行情（含當日開盤價）；漲跌以昨收（參考價）為基準。行情於每個交易日 15:00 自動更新。</p>
    </div>`,
};

export const SecurityPage = {
  components: { ErrorBox, OrderPanel },
  props: { id: String },
  setup(props) {
    const quote = useLoader(() => api.quote(props.id));
    const today = new Date();
    const from = ref(isoDate(new Date(today.getTime() - 90 * 864e5)));
    const to = ref(isoDate(today));
    const history = useLoader(() => api.history(props.id, from.value, to.value));
    const watchMsg = ref(''); const watchErr = ref(null);
    async function addWatch() {
      watchErr.value = null;
      try { await api.addWatch(props.id); watchMsg.value = '已加入自選股'; } catch (e) { watchErr.value = e; }
    }
    return { quote, history, from, to, addWatch, watchMsg, watchErr, isUser: computed(() => !auth.isAdmin), ...fmt };
  },
  template: `
    <div>
      <h2>{{ id }} <span v-if="quote.data.value">{{ quote.data.value.security_name }}</span>
        <button v-if="isUser" class="small" @click="addWatch">＋自選股</button>
        <span class="ok small-text">{{ watchMsg }}</span></h2>
      <ErrorBox :error="quote.error.value" /><ErrorBox :error="watchErr" />
      <div class="card" v-if="quote.data.value">
        <span>收盤 <b :class="trendClass(quote.data.value.change)">{{ price(quote.data.value.close_price) }}</b></span>
        <span :class="trendClass(quote.data.value.change)"> {{ signed(quote.data.value.change) }} ({{ pct(quote.data.value.change_pct) }})</span>
        <span class="muted">｜昨收 {{ price(quote.data.value.prev_close) }}｜開 {{ price(quote.data.value.open_price) }}｜高 {{ price(quote.data.value.high_price) }}｜低 {{ price(quote.data.value.low_price) }}｜{{ quote.data.value.trade_date }}</span>
      </div>
      <OrderPanel v-if="isUser" :security-id="id" />
      <div class="card">
        <h3>歷史行情</h3>
        <form class="form-row" @submit.prevent="history.reload()">
          <label>從 <input type="date" v-model="from"></label><label>到 <input type="date" v-model="to"></label>
          <button type="submit">查詢</button>
        </form>
        <ErrorBox :error="history.error.value" />
        <table v-if="history.data.value">
          <thead><tr><th>日期</th><th>昨收(參考價)</th><th>開盤</th><th>最高</th><th>最低</th><th>收盤</th><th>漲跌</th><th>幅度</th><th>成交量</th></tr></thead>
          <tbody><tr v-for="b in history.data.value" :key="b.trade_date">
            <td>{{ b.trade_date }}</td><td>{{ price(b.prev_close) }}</td><td>{{ price(b.open_price) }}</td><td>{{ price(b.high_price) }}</td>
            <td>{{ price(b.low_price) }}</td><td>{{ price(b.close_price) }}</td>
            <td :class="trendClass(b.change)">{{ signed(b.change) }}</td><td :class="trendClass(b.change)">{{ pct(b.change_pct) }}</td>
            <td>{{ money(b.volume) }}</td></tr></tbody>
        </table>
      </div>
    </div>`,
};

export const WatchlistPage = {
  components: { ErrorBox, QuoteTable },
  setup() {
    const list = useLoader(() => api.watchlist());
    const error = ref(null);
    async function remove(id) {
      try { await api.removeWatch(id); list.reload(); } catch (e) { error.value = e; }
    }
    return { list, remove, error };
  },
  template: `
    <div><h2>自選股</h2>
      <ErrorBox :error="list.error.value" /><ErrorBox :error="error" />
      <QuoteTable :rows="list.data.value || []" removable @remove="remove" />
    </div>`,
};

export const OrdersPage = {
  components: { ErrorBox },
  setup() {
    const status = ref('');
    const list = useLoader(() => api.orders(status.value || undefined));
    const error = ref(null);
    async function cancel(o) {
      error.value = null;
      try { await api.cancelOrder(o.order_id); list.reload(); } catch (e) { error.value = e; list.reload(); }
    }
    watch(status, () => list.reload());
    watch(() => market.tick, () => list.reload());   // see settlement results / other window
    return { status, list, cancel, error, ORDER_STATUS, ...fmt };
  },
  template: `
    <div><h2>委託紀錄</h2>
      <div class="form-row"><select v-model="status"><option value="">全部狀態</option>
        <option v-for="s in ORDER_STATUS" :key="s" :value="s">{{ s }}</option></select></div>
      <ErrorBox :error="list.error.value" /><ErrorBox :error="error" />
      <table v-if="list.data.value"><thead><tr><th>#</th><th>證券</th><th>買賣</th><th>價格</th><th>股數</th>
        <th>送出時間</th><th>歸屬日</th><th>狀態</th><th></th></tr></thead>
        <tbody><tr v-for="o in list.data.value" :key="o.order_id">
          <td>{{ o.order_id }}</td><td>{{ o.security_id }} {{ o.security_name }}</td><td>{{ o.side }}</td>
          <td>{{ price(o.price) }}</td><td>{{ money(o.quantity) }}</td><td>{{ dt(o.submit_time) }}</td>
          <td>{{ o.belong_date }}</td><td>{{ o.status }}</td>
          <td><button v-if="o.status==='待成交'" class="link" @click="cancel(o)">取消</button></td></tr></tbody></table>
    </div>`,
};

export const TradesPage = {
  components: { ErrorBox },
  setup() { return { list: useLoader(() => api.trades()), ...fmt }; },
  template: `
    <div><h2>成交紀錄／資金明細</h2>
      <ErrorBox :error="list.error.value" />
      <table v-if="list.data.value"><thead><tr><th>成交時間</th><th>證券</th><th>買賣</th><th>價格</th><th>股數</th>
        <th>成交金額</th><th>手續費</th><th>交易稅</th><th>收付金額</th><th>已實現損益</th></tr></thead>
        <tbody><tr v-for="t in list.data.value" :key="t.trade_id">
          <td>{{ dt(t.trade_time) }}</td><td>{{ t.security_id }} {{ t.security_name }}</td><td>{{ t.side }}</td>
          <td>{{ price(t.price) }}</td><td>{{ money(t.quantity) }}</td><td>{{ money(t.amount, 2) }}</td>
          <td>{{ money(t.fee) }}</td><td>{{ money(t.tax) }}</td>
          <td :class="trendClass(t.net_amount)">{{ signed(t.net_amount) }}</td>
          <td :class="trendClass(t.realized_profit)">{{ signed(t.realized_profit) }}</td></tr></tbody></table>
    </div>`,
};

export const PortfolioPage = {
  components: { ErrorBox },
  setup() {
    const p = useLoader(() => api.portfolio());
    watch(() => market.tick, () => p.reload());
    return { p, ...fmt };
  },
  template: `
    <div><h2>庫存與損益</h2>
      <ErrorBox :error="p.error.value" />
      <template v-if="p.data.value">
        <div class="card kpis">
          <div><small>總資產</small><b>{{ money(p.data.value.total_assets) }}</b></div>
          <div><small>可用現金</small><b>{{ money(p.data.value.available_cash) }}</b></div>
          <div><small>凍結現金</small><b>{{ money(p.data.value.frozen_cash) }}</b></div>
          <div><small>持股市值</small><b>{{ money(p.data.value.holdings_value) }}</b></div>
        </div>
        <table><thead><tr><th>證券</th><th>股數</th><th>凍結</th><th>平均成本</th><th>現價</th><th>市值</th>
          <th>未實現損益</th><th>報酬率</th><th>今日損益</th></tr></thead>
          <tbody><tr v-for="h in p.data.value.holdings" :key="h.security_id">
            <td><a :href="'#/security/' + h.security_id">{{ h.security_id }} {{ h.security_name }}</a></td>
            <td>{{ money(h.quantity) }}</td><td>{{ money(h.frozen_quantity) }}</td><td>{{ money(h.average_cost, 4) }}</td>
            <td>{{ price(h.current_price) }}</td><td>{{ money(h.market_value) }}</td>
            <td :class="trendClass(h.unrealized_pnl)">{{ signed(h.unrealized_pnl, 0) }}</td>
            <td :class="trendClass(h.return_rate)">{{ pct(h.return_rate === null ? null : h.return_rate * 100) }}</td>
            <td :class="trendClass(h.today_pnl)">{{ signed(h.today_pnl, 0) }}</td></tr></tbody></table>
      </template>
    </div>`,
};
