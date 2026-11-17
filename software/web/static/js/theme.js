(function () {
  var root = document.documentElement;
  var buttons = document.querySelectorAll('[data-theme-toggle]');

  function label() {
    var dark = root.dataset.theme === 'dark';
    document.querySelectorAll('[data-theme-label]').forEach(function (el) {
      el.textContent = dark ? 'Claro' : 'Oscuro';
    });
  }

  function set(theme) {
    root.dataset.theme = theme;
    try { localStorage.setItem('smartpet-theme', theme); } catch (e) {}
    label();
  }

  buttons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      set(root.dataset.theme === 'dark' ? 'light' : 'dark');
    });
  });

  label();
})();
