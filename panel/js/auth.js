// Auth guard — import FIRST in every panel page
import { pb } from './pb.js';

// Redirect to login if not authenticated
if (!pb.authStore.isValid) {
  window.location.href = '/panel/login.html';
}

// Listen for auth changes (logout, token expiry)
pb.authStore.onChange((token, record) => {
  if (!pb.authStore.isValid) {
    window.location.href = '/panel/login.html';
  }
});

// Helper: get current business owner ID
export const getOwnerId = () => pb.authStore.record?.id;

// Helper: get current business record (requires expand=owner in query)
export const getCurrentBusiness = async () => {
  if (!pb.authStore.isValid) return null;
  const ownerId = pb.authStore.record.id;
  const result = await pb.collection('negocios').getFirstListItem(`owner="${ownerId}"`, {
    expand: 'categoria'
  });
  return result;
};