function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  localStorage.setItem('theme', isDark ? 'light' : 'dark');
  updateThemeIcon();
}

function updateThemeIcon() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  document.querySelectorAll('#themeIcon').forEach(el => {
    el.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
  });
}

(function() {
  const saved = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  document.addEventListener('DOMContentLoaded', updateThemeIcon);
})();

function toggleSidebar() {
  document.getElementById('sidebar')?.classList.toggle('open');
}

document.addEventListener('click', function(e) {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  if (sidebar && !sidebar.contains(e.target) && toggle && !toggle.contains(e.target)) {
    sidebar.classList.remove('open');
  }
});

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.module-toggle-card').forEach(card => {
    const cb = card.querySelector('input[type="checkbox"]');
    if (!cb) return;
    cb.addEventListener('change', () => {
      card.classList.toggle('active', cb.checked);
    });
  });

  setTimeout(() => {
    document.querySelectorAll('.alert.fade.show').forEach(a => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(a);
      bsAlert.close();
    });
  }, 5000);
});
