// Offline-first sync queue using localStorage
const QUEUE_KEY = 'verificuba_sync_queue';

export function encolarLocal(datos) {
  const cola = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  cola.push({ ...datos, timestamp: Date.now() });
  localStorage.setItem(QUEUE_KEY, JSON.stringify(cola));
  console.log('[sync-queue] Encolado:', datos);
}

export function leerCola() {
  return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
}

export function quitarDeCola(item) {
  const cola = leerCola();
  const idx = cola.findIndex(i => i.timestamp === item.timestamp);
  if (idx >= 0) {
    cola.splice(idx, 1);
    localStorage.setItem(QUEUE_KEY, JSON.stringify(cola));
  }
}

export async function flushCola(pb) {
  const pendientes = leerCola();
  if (!pendientes.length) return;

  console.log('[sync-queue] Flushing', pendientes.length, 'items');

  for (const item of pendientes) {
    try {
      await pb.collection(item.collection).create(item.data);
      quitarDeCola(item);
      console.log('[sync-queue] Synced:', item);
    } catch (err) {
      console.warn('[sync-queue] Failed, will retry:', err.message);
      // Keep in queue for next attempt
    }
  }
}

// Auto-flush when online
window.addEventListener('online', () => {
  if (window.pb) flushCola(window.pb);
});

// Expose for manual trigger
export const syncQueue = { encolarLocal, leerCola, quitarDeCola, flushCola };