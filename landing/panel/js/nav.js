// Shared navigation sidebar for /panel/ pages
const NAV_ITEMS = [
  { href: 'dashboard.html', label: '📊 Dashboard', id: 'nav-dashboard' },
  { href: 'calculadora.html', label: '🧮 Calculadora', id: 'nav-calculadora' },
  { href: 'facturas.html', label: '📄 Facturas', id: 'nav-facturas' },
  { href: 'finanzas.html', label: '💰 Finanzas', id: 'nav-finanzas' },
  { href: 'perfil.html', label: '👤 Perfil', id: 'nav-perfil' }
];

export function renderNav(activeId) {
  const nav = document.getElementById('panel-nav');
  if (!nav) return;

  let html = '<nav class="panel-sidebar"><ul>';
  for (const item of NAV_ITEMS) {
    const active = item.id === activeId ? ' class="active"' : '';
    html += `<li${active}><a href="${item.href}">${item.label}</a></li>`;
  }
  html += '</ul></nav>';
  nav.innerHTML = html;
}

// Auto-detect active page from URL
export function initNav() {
  const path = window.location.pathname;
  let activeId = 'nav-dashboard';
  
  if (path.includes('calculadora')) activeId = 'nav-calculadora';
  else if (path.includes('facturas')) activeId = 'nav-facturas';
  else if (path.includes('finanzas')) activeId = 'nav-finanzas';
  else if (path.includes('perfil')) activeId = 'nav-perfil';
  
  renderNav(activeId);
}

// Run on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initNav);
} else {
  initNav();
}