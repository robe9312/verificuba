import { pb } from './pb.js';

// Auth guard - redirects to login if not authenticated
if (!pb.authStore.isValid) {
  window.location.href = '/panel/login.html';
}

// Listen for auth changes (logout, token expiry)
pb.authStore.onChange(() => {
  if (!pb.authStore.isValid) {
    window.location.href = '/panel/login.html';
  }
});

// Helper to get current negocio ID for the logged-in user
export async function getCurrentNegocioId() {
  if (!pb.authStore.isValid) return null;
  
  const user = pb.authStore.model;
  if (!user) return null;
  
  try {
    const records = await pb.collection('negocios').getList(1, 1, {
      filter: `owner = "${user.id}"`,
      sort: '-created'
    });
    return records.items.length > 0 ? records.items[0].id : null;
  } catch (err) {
    console.error('[auth] Error getting negocio:', err);
    return null;
  }
}

// Logout helper
export async function logout() {
  pb.authStore.clear();
  window.location.href = '/panel/login.html';
}