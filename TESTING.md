# Testing Guide - KoruAnalytics Landing Page

## 🧪 Cómo Testear Localmente

### Opción 1: Abrir Directamente (MÁS RÁPIDO)
1. Navega a la carpeta del proyecto
2. Haz doble clic en `index.html`
3. Se abrirá en tu navegador por defecto

**Limitación**: No simula un servidor real, puede tener problemas con rutas absolutas.

### Opción 2: Usar Python Server (RECOMENDADO)
```bash
# En la carpeta del proyecto
cd "c:\Users\carlo\OneDrive - KoruAnalytics\Prj_Professional\koruanalytics-site"

# Iniciar servidor local
python -m http.server 8000

# Abrir en el navegador
# http://localhost:8000
```

**Ventajas**: Simula servidor real, muestra cómo funcionará en Azure.

### Opción 3: Live Server (VSCode Extension)
Si usas VSCode:
1. Instala extensión "Live Server"
2. Click derecho en `index.html`
3. "Open with Live Server"
4. Se abre en `http://127.0.0.1:5500`

**Ventajas**: Auto-reload cuando guardas cambios.

## ✅ Checklist de Testing

### Tests Visuales
- [ ] Logo aparece en navegación
- [ ] Favicon aparece en pestaña del navegador
- [ ] Todas las imágenes cargan (logo, map, dashboards)
- [ ] Colores coinciden con la paleta (#1a9bba)
- [ ] Tipografía se ve bien (DM Sans + Playfair Display)
- [ ] Año en footer muestra 2025 (o año actual)

### Tests de Navegación
- [ ] Click en "Services" lleva a sección Services
- [ ] Click en "Process" lleva a sección Process
- [ ] Click en "Work" lleva a sección Work
- [ ] Click en "About" lleva a sección About
- [ ] Click en "Get in touch" lleva a sección Contact
- [ ] Smooth scroll funciona (animación suave)
- [ ] Email link abre cliente de correo
- [ ] LinkedIn link abre en nueva pestaña

### Tests Mobile (Responsive)
1. Abre DevTools (F12)
2. Click en icono de dispositivo móvil
3. Prueba estos tamaños:
   - [ ] iPhone SE (375px) - Mobile
   - [ ] iPad (768px) - Tablet
   - [ ] Desktop (1024px+)

**Verificar en mobile**:
- [ ] Hamburger menu aparece
- [ ] Click abre menu
- [ ] Click en link cierra menu
- [ ] Texto es legible
- [ ] Imágenes no se salen del viewport
- [ ] Botones son clickeables

### Tests de Interacción
- [ ] Navbar obtiene fondo blur al hacer scroll
- [ ] Hover en botones muestra efecto
- [ ] Hover en imágenes muestra zoom sutil
- [ ] Hover en links de navegación muestra underline
- [ ] Mobile menu cierra al clickear fuera

### Tests de Performance
Abre Chrome DevTools > Lighthouse:
- [ ] Performance > 80
- [ ] Accessibility > 90
- [ ] Best Practices > 90
- [ ] SEO > 90

### Tests de Consola
Abre DevTools Console (F12):
- [ ] No hay errores en rojo
- [ ] No hay warnings importantes
- [ ] JavaScript carga correctamente

## 🌐 Testing en Diferentes Navegadores

**Esenciales**:
- [ ] Chrome/Edge (motor Chromium)
- [ ] Firefox
- [ ] Safari (si tienes Mac)

**Opcionales**:
- [ ] Mobile Safari (iPhone)
- [ ] Chrome Mobile (Android)

## 🔍 Validación HTML/CSS

### HTML Validator
1. Ve a: https://validator.w3.org/
2. Sube `index.html`
3. Verifica que no hay errores críticos

### CSS Validator
1. Ve a: https://jigsaw.w3.org/css-validator/
2. Sube `css/styles.css`
3. Verifica que no hay errores críticos

## 📱 Test Social Media Preview

### Open Graph (Facebook/LinkedIn)
1. Ve a: https://www.opengraph.xyz/
2. Ingresa: `https://www.koruanalytics.com`
3. Verifica:
   - [ ] Título correcto
   - [ ] Descripción correcta
   - [ ] Imagen og-image.png aparece

### Twitter Card
1. Ve a: https://cards-dev.twitter.com/validator
2. Ingresa URL
3. Verifica preview

## ⚡ Test de Velocidad

### PageSpeed Insights
1. Ve a: https://pagespeed.web.dev/
2. Ingresa URL (después de deploy)
3. Objetivo:
   - Mobile: > 80
   - Desktop: > 90

## 🐛 Debugging Common Issues

### Imágenes no cargan
- Verifica rutas: `img/logo.png` (relativa, no absoluta)
- Verifica nombres de archivo (case-sensitive en Linux)

### CSS no aplica
- Verifica ruta: `css/styles.css`
- Abre DevTools > Network > verifica que carga

### JavaScript no funciona
- Verifica ruta: `js/main.js`
- Abre Console > busca errores
- Verifica que script está al final del `</body>`

### Fuentes no cargan
- Verifica conexión a Google Fonts
- Abre Network > filtra por "font"

## 📝 Pre-Deploy Checklist

Antes de hacer `git push`:
- [ ] Todas las imágenes están optimizadas
- [ ] No hay `console.log()` en JavaScript
- [ ] Año en footer es dinámico
- [ ] Favicon aparece correctamente
- [ ] og-image.png existe y es correcto
- [ ] Links de contacto funcionan
- [ ] No hay errores en consola
- [ ] Testing en mobile completado
- [ ] HTML válido (sin errores críticos)

## 🚀 Ready to Deploy!

Si todos los tests pasan, estás listo para:
```bash
git add .
git commit -m "Complete landing page"
git push
```

Azure deployará automáticamente en ~2 minutos.
