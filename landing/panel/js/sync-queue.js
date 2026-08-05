// Offline-first sync queue — localStorage backed, flushes on online/reload
const QUEUE_KEY = 'verificuba_sync_queue';

function readQueue() {
  try {
    return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  } catch {
    return [];
  }
}

function writeQueue(queue) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export async function enqueueCreate(collection, data) {
  const queue = readQueue();
  queue.push({ collection, data, ts: Date.now(), type: 'create' });
  writeQueue(queue);
  return { queued: true };
}

export async function flushQueue(pb) {
  const queue = readQueue();
  if (!queue.length) return { flushed: 0 };

  const remaining = [];
  let flushed = 0;

  for (const item of queue) {
    try {
      if (item.type === 'create') {
        await pb.collection(item.collection).create(item.data);
      }
      // add update/delete types here if needed
      flushed++;
    } catch (err) {
      console.warn('[sync] flush failed for', item, err);
      remaining.push(item);
    }
  }

  writeQueue(remaining);
  return { flushed, remaining: remaining.length };
}

// Auto-flush on online event
window.addEventListener('online', () => {
  console.log('[sync] online — flushing queue');
  import('./pb.js').then(({ pb }) => flushQueue(pb));
});

// Flush on panel page load
export async function initSync(pb) {
  const { flushed, remaining } = await flushQueue(pb);
  if (flushed) console.log('[sync] flushed', flushed, 'items');
  if (remaining) console.log('[sync]', remaining, 'items still pending');
}