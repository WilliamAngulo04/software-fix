// Editor del patrón de desbloqueo de 3x3 (ver clientes/patron.py).
// Se dibuja arrastrando el dedo o el mouse; como en Android, si el trazo pasa sobre
// un punto intermedio todavía libre, ese punto se agrega automáticamente.
(() => {
  const RADIO_TOQUE = 38;
  const centro = (p) => [50 + 100 * ((p - 1) % 3), 50 + 100 * Math.floor((p - 1) / 3)];

  function iniciar(editor) {
    const input = document.getElementById(editor.dataset.input);
    const svg = editor.querySelector('svg');
    const trazo = editor.querySelector('.patron-trazo');
    const texto = editor.querySelector('.patron-texto');
    let secuencia = (input.value || '').split('').map(Number).filter(Boolean);
    let dibujando = false;
    let cursor = null;

    function pintar() {
      const puntos = secuencia.map(centro);
      if (dibujando && cursor) puntos.push(cursor);
      trazo.setAttribute('points', puntos.map((p) => p.join(',')).join(' '));
      editor.querySelectorAll('.patron-punto').forEach((c) => {
        const n = Number(c.dataset.punto);
        c.classList.toggle('activo', secuencia.includes(n));
        c.classList.toggle('inicio', secuencia[0] === n);
      });
      input.value = secuencia.join('');
      if (!secuencia.length) texto.textContent = 'Dibuja el patrón uniendo los puntos';
      else if (secuencia.length < 4) texto.textContent = `${secuencia.length} puntos · mínimo 4`;
      else texto.textContent = `Patrón de ${secuencia.length} puntos ✓`;
    }

    function posicion(ev) {
      const caja = svg.getBoundingClientRect();
      return [(ev.clientX - caja.left) * 300 / caja.width, (ev.clientY - caja.top) * 300 / caja.height];
    }

    function agregar(p) {
      if (secuencia.includes(p)) return;
      const anterior = secuencia[secuencia.length - 1];
      if (anterior) {
        // Punto intermedio en línea recta (ej. 1 → 3 pasa por 2).
        const [x1, y1] = centro(anterior);
        const [x2, y2] = centro(p);
        const medio = [(x1 + x2) / 2, (y1 + y2) / 2];
        for (let q = 1; q <= 9; q++) {
          const [x, y] = centro(q);
          if (x === medio[0] && y === medio[1] && !secuencia.includes(q)) secuencia.push(q);
        }
      }
      secuencia.push(p);
    }

    function puntoEn([x, y]) {
      for (let p = 1; p <= 9; p++) {
        const [cx, cy] = centro(p);
        if (Math.hypot(x - cx, y - cy) < RADIO_TOQUE) return p;
      }
      return null;
    }

    svg.addEventListener('pointerdown', (ev) => {
      const p = puntoEn(posicion(ev));
      if (!p) return;
      ev.preventDefault();
      svg.setPointerCapture(ev.pointerId);
      secuencia = [p];
      dibujando = true;
      cursor = posicion(ev);
      pintar();
    });
    svg.addEventListener('pointermove', (ev) => {
      if (!dibujando) return;
      cursor = posicion(ev);
      const p = puntoEn(cursor);
      if (p) agregar(p);
      pintar();
    });
    const terminar = () => { dibujando = false; cursor = null; pintar(); };
    svg.addEventListener('pointerup', terminar);
    svg.addEventListener('pointercancel', terminar);
    editor.querySelector('.patron-limpiar').addEventListener('click', () => { secuencia = []; pintar(); });
    // Permite que otra parte de la página cargue un patrón guardado (ej. "14789").
    editor.establecerPatron = (valor) => {
      secuencia = String(valor || '').split('').map(Number).filter(Boolean);
      pintar();
    };
    pintar();
  }

  document.querySelectorAll('.patron-editor').forEach(iniciar);
})();
