# Vue Download Page

Página de una sola vista hecha con Vue + Vite.

## Ejecutar localmente

```bash
npm install
npm run dev
```

## Cambiar el archivo descargable

1. Coloca tu archivo dentro de `public/`.
2. Abre `src/App.vue`.
3. Cambia:

```js
const fileName = 'archivo-demo.txt'
```

por ejemplo a:

```js
const fileName = 'mi-archivo.zip'
```

## Desplegar gratis con GitHub Pages

1. Crea un repositorio en GitHub.
2. Sube todo este proyecto.
3. En GitHub abre:
   `Settings > Pages`
4. En **Build and deployment > Source**, selecciona:
   `GitHub Actions`
5. Haz push a la rama `main`.
6. El workflow `.github/workflows/deploy.yml` compilará y publicará la web automáticamente.

No necesitas pagar hosting.
