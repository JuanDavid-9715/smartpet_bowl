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


// Menu de navegacion en el celular: la barra de enlaces se pliega detras de
// la hamburguesa y se cierra al elegir un enlace, al tocar fuera o con Escape.
(function () {
  var boton = document.querySelector('[data-nav-toggle]');
  var menu = document.getElementById('site-nav');
  if (!boton || !menu) { return; }

  function abrir(estado) {
    menu.classList.toggle('is-open', estado);
    boton.setAttribute('aria-expanded', estado ? 'true' : 'false');
    boton.setAttribute('aria-label', estado ? 'Cerrar menu' : 'Abrir menu');
  }

  boton.addEventListener('click', function (evento) {
    evento.stopPropagation();
    abrir(!menu.classList.contains('is-open'));
  });

  menu.addEventListener('click', function (evento) {
    if (evento.target.closest('a')) { abrir(false); }
  });

  document.addEventListener('click', function (evento) {
    if (!menu.classList.contains('is-open')) { return; }
    if (menu.contains(evento.target) || boton.contains(evento.target)) { return; }
    abrir(false);
  });

  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape') { abrir(false); }
  });
})();
