// Mirror of backend/app/constants.py — keep both in sync.
export const SIDE = { BUY: '買', SELL: '賣' };
export const ORDER_STATUS = ['待成交', '已成交', '已取消', '已失效'];
export const ACCOUNT_STATUS = { ACTIVE: '啟用', FROZEN: '凍結' };
export const SECURITY_STATUS = { ACTIVE: '啟用', DISABLED: '停用' };
export const CATEGORIES = [
  { id: 1, name: '普通股' },
  { id: 2, name: 'ETF' },
  { id: 3, name: '債券ETF' },
];
export const PHASE_CLASS = {
  HOLIDAY: 'phase-off', PRE_OPEN: 'phase-pre', OPEN: 'phase-open',
  CLOSED: 'phase-closed', SETTLING: 'phase-settling', SETTLED: 'phase-off',
};
