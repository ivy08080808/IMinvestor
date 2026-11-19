// Shared UI components: status bar (market clock), error box, order panel.
import { ref, computed, watch, onMounted, onUnmounted } from './vue.js';
import { api } from './api.js';
import { auth, market } from './store.js';
import { POLL_MS } from './config.js';
import { PHASE_CLASS, SIDE } from './constants.js';
import { money, price, dt } from './format.js';

export const ErrorBox = {
  props: { error: Object },
  template: `
    <div v-if="error" :class="['error-box', error.notImplemented ? 'todo' : '']">
{{ error.message }}
      <small v-if="error.code && !error.notImplemented"> ({{ error.code }})</small>
    </div>`,
};

// Top bar: Taipei time, market phase, belong date of a new order, cash summary.
// Polls every POLL_MS so two browser windows stay in sync.
export const StatusBar = {
  setup() {
    const err = ref(null);
    let timer = null;
    async function poll() {
      try {
        market.status = await api.marketStatus();
        if (auth.isLoggedIn && !auth.isAdmin) {
          market.account = await api.account().catch(() => null);
        }
        market.tick += 1;
        err.value = null;
      } catch (e) {
        err.value = e;
      }
    }
    onMounted(() => { poll(); timer = setInterval(poll, POLL_MS); });
    onUnmounted(() => clearInterval(timer));
    const s = computed(() => market.status);
    const phaseClass = computed(() => s.value ? PHASE_CLASS[s.value.phase] : '');
    return { s, err, phaseClass, auth, market, money, dt };
  },
  template: `
    <div class="status-bar">
      <template v-if="s">
        <span class="clock">🕒 台北 {{ dt(s.now) }}</span>
        <span :class="['phase', phaseClass]">{{ s.phase_label }}</span>
        <span v-if="s.can_place_order">新委託歸屬：<b>{{ s.order_belong_date }}</b></span>
        <span v-else class="warn">暫停下單</span>
        <span class="muted">最新行情：{{ s.latest_price_date || '尚無' }}</span>
        <span v-if="s.message" class="warn">{{ s.message }}</span>
      </template>
      <span v-else-if="err" class="warn">{{ err.message }}</span>
      <span v-else class="muted">載入市場狀態…</span>
      <span class="spacer"></span>
      <span v-if="market.account">
        可用 {{ money(market.account.available_cash) }} ／ 凍結 {{ money(market.account.frozen_cash) }}
        <span v-if="market.account.status === '凍結'" class="warn">（帳戶凍結）</span>
      </span>
    </div>`,
};

// Exact fee estimate with BigInt cents (mirrors backend app/fees.py).
function estimateBuyFreeze(p, q) {
  const cents = BigInt(Math.round(Number(p) * 100)) * BigInt(q);
  let fee = (cents * 1425n) / 100000000n;
  if (fee < 1n) fee = 1n;
  return Number(cents) / 100 + Number(fee);
}

export const OrderPanel = {
  components: { ErrorBox },
  props: { securityId: String },
  emits: ['placed'],
  setup(props, { emit }) {
    const rule = ref(null);
    const ruleErr = ref(null);
    const side = ref(SIDE.BUY);
    const px = ref('');
    const qty = ref(1000);
    const submitErr = ref(null);
    const okMsg = ref('');
    const busy = ref(false);

    async function loadRule() {
      try {
        rule.value = await api.orderRule(props.securityId);
        ruleErr.value = null;
        if (!px.value && rule.value.reference_price) px.value = rule.value.reference_price;
      } catch (e) { ruleErr.value = e; }
    }
    onMounted(loadRule);
    watch(() => market.status && market.status.phase, loadRule);   // phase change -> new belong date

    const estimate = computed(() => {
      if (!px.value || !qty.value || side.value !== SIDE.BUY) return null;
      return estimateBuyFreeze(px.value, qty.value);
    });

    async function submit() {
      busy.value = true; submitErr.value = null; okMsg.value = '';
      try {
        const o = await api.placeOrder({
          security_id: props.securityId, side: side.value,
          price: String(px.value), quantity: Number(qty.value),
        });
        okMsg.value = `委託 #${o.order_id} 已送出，歸屬 ${o.belong_date}，將於該日 15:00 自動結算。`;
        emit('placed', o);
      } catch (e) { submitErr.value = e; }
      busy.value = false;
    }
    return { rule, ruleErr, side, px, qty, estimate, submit, submitErr, okMsg, busy, SIDE, price, money };
  },
  template: `
    <div class="card">
      <h3>限價下單</h3>
      <ErrorBox :error="ruleErr" />
      <div v-if="rule">
        <p class="muted" v-if="rule.tradable">
          歸屬交易日 {{ rule.order_belong_date }}｜參考價 {{ price(rule.reference_price) }}｜
          允許區間 {{ price(rule.limit_low) }} ～ {{ price(rule.limit_high) }}
        </p>
        <p class="warn" v-else>{{ rule.reason }}</p>
        <div class="form-row">
          <label><input type="radio" :value="SIDE.BUY" v-model="side"> 買</label>
          <label><input type="radio" :value="SIDE.SELL" v-model="side"> 賣</label>
          <label>價格 <input type="number" step="0.01" min="0.01" v-model="px"></label>
          <label>股數 <input type="number" step="1" min="1" v-model="qty"></label>
          <button :disabled="busy || !rule.tradable" @click="submit">送出委託</button>
        </div>
        <p class="muted" v-if="estimate !== null">預估凍結金額（含手續費）：{{ money(estimate) }} 元</p>
        <ErrorBox :error="submitErr" />
        <p class="ok" v-if="okMsg">{{ okMsg }}</p>
      </div>
    </div>`,
};
