// Small composable: run an async API call, expose data / error / loading.
import { ref } from './vue.js';

export function useLoader(fn, { immediate = true } = {}) {
  const data = ref(null);
  const error = ref(null);
  const loading = ref(false);
  async function reload(...args) {
    loading.value = true;
    error.value = null;
    try {
      data.value = await fn(...args);
    } catch (e) {
      error.value = e;
    } finally {
      loading.value = false;
    }
    return data.value;
  }
  if (immediate) reload();
  return { data, error, loading, reload };
}
