<script setup>
const fileName = 'archivo-demo.txt'

function downloadFile() {
  const link = document.createElement('a')
  link.href = `./${fileName}`
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
}
</script>

<template>
  <main class="page-shell">
    <div class="glow glow-one"></div>
    <div class="glow glow-two"></div>

    <nav class="navbar">
      <div class="brand">
        <div class="brand-icon">D</div>
        <span>Download Center</span>
      </div>

      <span class="status">
        <span class="status-dot"></span>
        Disponible
      </span>
    </nav>

    <section class="hero">
      <div class="badge">DESCARGA SEGURA Y DIRECTA</div>

      <h1>
        Tu Adobe CS6 está
        <span>listo para descargar.</span>
      </h1>

      <p class="subtitle">
        Una aplicación para los mejores de diseño.
        Presiona el botón para iniciar la descarga.
      </p>

      <div class="download-card">
        <div class="file-icon">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"
            />
            <path d="M14 2v6h6" />
          </svg>
        </div>

        <div class="file-info">
          <span class="file-label">Archivo disponible</span>
          <strong>{{ fileName }}</strong>
          <small>Descarga directa desde GitHub Pages</small>
        </div>

        <button class="download-button" @click="downloadFile">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 3v12" />
            <path d="m7 10 5 5 5-5" />
            <path d="M5 21h14" />
          </svg>
          Descargar
        </button>
      </div>

      <div class="features">
        <div class="feature">
          <div class="feature-icon">✓</div>
          <div>
            <strong>Sin publicidad</strong>
            <span>Experiencia limpia</span>
          </div>
        </div>

        <div class="feature">
          <div class="feature-icon">↯</div>
          <div>
            <strong>Descarga directa</strong>
            <span>Un solo clic</span>
          </div>
        </div>

        <div class="feature">
          <div class="feature-icon">∞</div>
          <div>
            <strong>Hosting gratis</strong>
            <span>GitHub Pages</span>
          </div>
        </div>
      </div>
    </section>

    <footer>
      <span>© 2026 Download Center</span>
      <span>Hecho con Vue</span>
    </footer>
  </main>
</template>
