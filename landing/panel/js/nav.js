// Shared navigation — injects sidebar into any panel page
const NAV_HTML = `
<nav id="panel-nav" class="panel-nav" role="navigation" aria-label="Panel principal">
  <div class="nav-header">
    <a href="/panel/dashboard.html" class="nav-brand" aria-label="VerifiCuba Panel">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
      </svg>
      <span>VerifiCuba</span>
    </a>
  </div>
  <ul class="nav-menu">
    <li><a href="/panel/dashboard.html" data-nav="dashboard">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
      <span>Dashboard</span>
    </a></li>
    <li><a href="/panel/calculadora.html" data-nav="calculadora">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="4" y="2" width="16" height="20" rx="2"/><path d="M4 8h16"/><path d="M8 12h8"/><path d="M8 16h4"/></svg>
      <span>Calculadora ONAT</span>
    </a></li>
    <li><a href="/panel/facturas.html" data-nav="facturas">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>
      <span>Facturas</span>
    </a></li>
    <li><a href="/panel/finanzas.html" data-nav="finanzas">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>
      <span>Finanzas</span>
    </a></li>
    <li><a href="/panel/perfil.html" data-nav="perfil">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
      <span>Mi Perfil</span>
    </a></li>
  </ul>
  <div class="nav-footer">
    <button id="nav-logout" class="nav-link nav-logout" aria-label="Cerrar sesión">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      <span>Salir</span>
    </button>
  </div>
</nav>
<div id="nav-overlay" class="nav-overlay" aria-hidden="true"></div>
`;

function injectNav(activePage) {
  const mount = document.getElementById('nav-mount');
  if (!mount) return;

  mount.innerHTML = NAV_HTML;

  // Highlight active
  const activeLink = mount.querySelector(`[data-nav="${activePage}"]`);
  if (activeLink) activeLink.classList.add('active');

  // Mobile toggle
  const toggle = document.getElementById('nav-toggle');
  const nav = document.getElementById('panel-nav');
  const overlay = document.getElementById('nav-overlay');
  if (toggle && nav && overlay) {
    toggle.addEventListener('click', () => {
      nav.classList.toggle('open');
      overlay.classList.toggle('show');
    });
    overlay.addEventListener('click', () => {
      nav.classList.remove('open');
      overlay.classList.remove('show');
    });
  }

  // Logout
  const logoutBtn = document.getElementById('nav-logout');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      const { pb } = await import('./pb.js');
      pb.authStore.clear();
      window.location.href = '/panel/login.html';
    });
  }
}

// Auto-inject if mount point exists
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    const mount = document.getElementById('nav-mount');
    if (mount && mount.dataset.nav) {
      injectNav(mount.dataset.nav);
    }
  });
} else {
  const mount = document.getElementById('nav-mount');
  if (mount && mount.dataset.nav) {
    injectNav(mount.dataset.nav);
  }
}

export { injectNav };