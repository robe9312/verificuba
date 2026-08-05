// PocketBase instance — single source for the whole panel
// URL is injected by tunnel-sync.sh at deploy time (see PB_URL in index.html)
const PB_URL = (typeof window !== 'undefined' && window.PB_URL) || 'http://localhost:8090';

import PocketBase from 'https://cdn.jsdelivr.net/npm/pocketbase@0.23.0/dist/pocketbase.es.min.mjs';

export const pb = new PocketBase(PB_URL);

// Auto-refresh auth on page load
pb.authStore.onChange(() => {
  console.log('[pb] authStore changed:', pb.authStore.isValid ? 'valid' : 'invalid');
});