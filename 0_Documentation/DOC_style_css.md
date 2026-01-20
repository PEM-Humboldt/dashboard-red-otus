# Documentación: style.css

## Información General

**Archivo:** `style.css`  
**Ubicación:** `4_Dashboard/www/css/style.css`  
**Proyecto:** Dashboard IaVH - Red OTUS Colombia  
**Autor:** Conservation International / Instituto Humboldt  
**Versión:** 2.2  
**Licencia:** Creative Commons License CC0  
**Última actualización:** 2025-12-09  

---

## Descripción

Hoja de estilos CSS personalizada para el Dashboard de Fototrampeo Wildlife Insights V2. Define la apariencia visual, componentes interactivos, responsividad y experiencia de usuario del dashboard Shiny.

---

## Paleta de Colores

### Variables CSS (`:root`)

```css
:root {
  /* Colores primarios */
  --color-primary: #2c3e50;          /* Azul oscuro - Encabezados */
  --color-secondary: #3498db;        /* Azul brillante - Acentos */
  --color-accent: #1a5490;           /* Azul profundo - Títulos */
  
  /* Colores de texto */
  --color-text-primary: #2c3e50;     /* Texto principal */
  --color-text-secondary: #7f8c8d;   /* Texto secundario */
  --color-text-light: #ecf0f1;       /* Texto sobre fondos oscuros */
  
  /* Colores de fondo */
  --color-bg-light: #ffffff;         /* Fondo claro */
  --color-bg-gray: #f8f9fa;          /* Fondo gris suave */
  --color-bg-dark: #34495e;          /* Fondo oscuro */
  
  /* Colores de estado */
  --color-success: #27ae60;          /* Verde - Éxito */
  --color-warning: #f39c12;          /* Naranja - Advertencia */
  --color-danger: #e74c3c;           /* Rojo - Error */
  --color-info: #3498db;             /* Azul - Información */
  
  /* Colores de borde */
  --border-color: #dde4e6;           /* Bordes sutiles */
  --border-color-dark: #bdc3c7;      /* Bordes destacados */
  
  /* Sombras */
  --shadow-sm: 0 2px 4px rgba(0,0,0,0.1);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  --shadow-lg: 0 8px 16px rgba(0,0,0,0.15);
  --shadow-xl: 0 12px 24px rgba(0,0,0,0.2);
  
  /* Tamaños de fuente */
  --font-size-small: 0.875em;        /* 14px */
  --font-size-base: 1em;             /* 16px */
  --font-size-large: 1.125em;        /* 18px */
  --font-size-xlarge: 1.25em;        /* 20px */
  
  /* Espaciado */
  --spacing-xs: 0.25rem;             /* 4px */
  --spacing-sm: 0.5rem;              /* 8px */
  --spacing-md: 1rem;                /* 16px */
  --spacing-lg: 1.5rem;              /* 24px */
  --spacing-xl: 2rem;                /* 32px */
  
  /* Transiciones */
  --transition-fast: 0.15s ease;
  --transition-base: 0.3s ease;
  --transition-slow: 0.5s ease;
  
  /* Radios de borde */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 50%;
}
```

---

## Estructura de Secciones

### 1. Base y Tipografía

#### Reset Global

```css
* {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-primary);
  background-color: var(--color-bg-gray);
}
```

#### Encabezados

```css
h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  line-height: 1.2;
  margin-top: 0;
}

h1 { font-size: 2.25em; }          /* 36px */
h2 { font-size: 1.875em; }         /* 30px */
h3 { font-size: 1.5em; }           /* 24px */
h4 { font-size: var(--font-size-xlarge); }  /* 20px */
h5 { font-size: var(--font-size-large); }   /* 18px */
h6 { font-size: 1em; }             /* 16px */
```

#### Enlaces y Texto

```css
a {
  color: var(--color-secondary);
  text-decoration: none;
  transition: var(--transition-fast);
}

a:hover {
  color: var(--color-accent);
  text-decoration: underline;
}

strong, b {
  font-weight: 700;
}

small {
  font-size: var(--font-size-small);
}
```

---

### 2. Cajas de Sección (Section Boxes)

#### Caja Unificada

```css
.section-box {
  background: var(--color-bg-light);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
}
```

#### Caja de Título (Centrada)

```css
.section-box-title {
  text-align: center;
  padding: var(--spacing-md);
}

/* Forzar centrado en todos los elementos hijos */
.section-box-title *,
.section-box-title *::before,
.section-box-title *::after {
  text-align: center !important;
}
```

**Uso:**
- Sección 1: Título del reporte
- Nombre dinámico del proyecto

#### Título del Reporte

```css
.report-title {
  font-size: 2.5em;
  font-weight: 700;
  color: var(--color-primary);
  margin: 0 0 var(--spacing-sm) 0;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
```

#### Subtítulo del Reporte

```css
.report-subtitle {
  font-size: 1.25em;
  color: var(--color-text-secondary);
  margin: var(--spacing-sm) 0 0 0;
  font-weight: 400;
  line-height: 1.4;
}
```

---

### 3. Componentes de Formulario

#### Selectores (Selectize)

```css
.form-control,
.selectize-input {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  transition: var(--transition-base);
}

.form-control:focus,
.selectize-input.focus {
  border-color: var(--color-secondary);
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
  outline: none;
}
```

**Sistema de z-index para prevenir overlapping:**

```css
/* Primera lista desplegable (prioridad alta) */
.form-group:first-of-type .selectize-control {
  z-index: 1002;
}

.form-group:first-of-type .selectize-dropdown {
  z-index: 1003;
}

/* Segunda lista desplegable (prioridad normal) */
.form-group:nth-of-type(2) .selectize-control {
  z-index: 1000;
}

.form-group:nth-of-type(2) .selectize-dropdown {
  z-index: 1001;
}
```

#### Dropdown Selectize

```css
.selectize-dropdown {
  border: 1px solid var(--border-color);
  border-top: none;
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
  background: var(--color-bg-light);
  box-shadow: var(--shadow-md);
  max-height: 300px;
  overflow-y: auto;
}
```

---

### 4. Botones

#### Botón Genérico

```css
button,
.btn {
  background-color: var(--color-secondary);
  color: var(--color-text-light);
  border: none;
  border-radius: var(--radius-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: var(--font-size-base);
  cursor: pointer;
  transition: var(--transition-base);
}

button:hover,
.btn:hover {
  background-color: var(--color-accent);
  box-shadow: var(--shadow-md);
}

button:active,
.btn:active {
  transform: translateY(1px);
}
```

#### Botón "Aplicar selección"

```css
.btn-apply-selection {
  background-color: var(--color-success);
  font-weight: 600;
  padding: 10px 24px;
  font-size: 1.05em;
}

.btn-apply-selection:hover {
  background-color: #229954;
}
```

#### Botón "Limpiar selección"

```css
.btn-clear-selection {
  background-color: var(--color-warning);
  color: var(--color-bg-light);
  padding: 10px 24px;
}

.btn-clear-selection:hover {
  background-color: #d68910;
}
```

#### Botones de Exportación Compactos

```css
.btn-export-compact {
  background-color: var(--color-secondary);
  color: var(--color-text-light);
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 16px;
  font-size: 0.95em;
  cursor: pointer;
  transition: var(--transition-base);
}

.btn-export-compact:hover:not(:disabled) {
  background-color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}

.btn-export-compact:disabled {
  background-color: #bdc3c7;
  cursor: not-allowed;
}
```

---

### 5. Tabla de Especies

#### Contenedor de Tabla

```css
.species-table-container {
  width: 100%;
  overflow-x: auto;
  border-radius: var(--radius-md);
  background: var(--color-bg-light);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-md);
}
```

#### Estilos de DataTables

```css
.species-table-container table.dataTable {
  width: 100% !important;
  border-collapse: collapse;
  font-size: 0.95em;
}

.species-table-container table.dataTable thead th {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 100%);
  color: var(--color-text-light);
  font-weight: 600;
  padding: 12px 16px;
  text-align: left;
  border-bottom: 2px solid var(--color-secondary);
  position: sticky;
  top: 0;
  z-index: 10;
}

.species-table-container table.dataTable tbody td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
  vertical-align: middle;
}

.species-table-container table.dataTable tbody tr:hover {
  background-color: #e8f4f8;
  cursor: pointer;
}
```

#### Estilos de Columnas Específicas

```css
/* Columna de ranking - Destacada */
.species-table-container table.dataTable tbody td:first-child {
  font-weight: 700;
  color: var(--color-accent);
  font-size: 1.1em;
}

/* Columna de especie - Cursiva para nombres científicos */
.species-table-container table.dataTable tbody td:nth-child(2) {
  font-style: italic;
}

/* Columnas numéricas - Centradas */
.species-table-container table.dataTable tbody td:nth-child(3),
.species-table-container table.dataTable tbody td:nth-child(4) {
  text-align: center;
}
```

#### Scroll Bar Personalizado

```css
.species-table-container::-webkit-scrollbar {
  height: 8px;
  width: 8px;
}

.species-table-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.species-table-container::-webkit-scrollbar-thumb {
  background: var(--color-secondary);
  border-radius: 4px;
}

.species-table-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-accent);
}
```

---

### 6. Tabla de Indicadores Consolidados

#### Diseño de Tabla

```css
.indicators-table-real {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--color-bg-light);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  font-family: 'Segoe UI', sans-serif;
  margin-top: var(--spacing-md);
}
```

#### Encabezados con Emojis

```css
.indicators-table-real th {
  background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
  color: var(--color-text-light);
  font-weight: 600;
  padding: 16px 12px;
  text-align: center;
  vertical-align: middle;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
  font-size: 0.9em;
}

/* Emojis en encabezados - Tamaño aumentado */
.indicators-table-real .emoji-icon {
  display: block;
  font-size: 1.8em;
  margin-bottom: 4px;
  line-height: 1;
}

/* Etiquetas de texto debajo de emojis */
.indicators-table-real .emoji-label {
  display: block;
  font-size: 0.75em;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
```

#### Separadores Visuales entre Grupos

```css
/* Separador después de columnas clave */
.indicators-table-real th:nth-child(3)::after,
.indicators-table-real th:nth-child(6)::after {
  content: '';
  position: absolute;
  right: 0;
  top: 10%;
  height: 80%;
  width: 2px;
  background: rgba(255, 255, 255, 0.3);
}
```

#### Celdas de Datos

```css
.indicators-table-real td {
  padding: 14px 12px;
  text-align: center;
  vertical-align: middle;
  border-right: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  background: var(--color-bg-light);
  font-size: 1em;
  font-weight: 500;
  color: var(--color-text-primary);
  transition: var(--transition-fast);
}

.indicators-table-real td:hover {
  background-color: #e8f4f8;
  color: var(--color-accent);
}
```

#### Fondos Sutiles por Grupo

```css
/* Grupo 1: Datos operacionales (Imágenes, Cámaras, Días) */
.indicators-table-real td:nth-child(-n+3) {
  background-color: rgba(52, 152, 219, 0.02);
}

/* Grupo 2: Riqueza taxonómica (Especies, Mamíferos, Aves) */
.indicators-table-real td:nth-child(n+4):nth-child(-n+6) {
  background-color: rgba(39, 174, 96, 0.02);
}

/* Grupo 3: Índices de diversidad (Hill 1, 2, 3) */
.indicators-table-real td:nth-child(n+7):nth-child(-n+9) {
  background-color: rgba(243, 156, 18, 0.02);
}
```

#### Animación de Entrada

```css
@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.indicators-table-real {
  animation: fadeInScale 0.4s ease-out;
}
```

---

### 7. Cajas de Dashboard (Boxes)

#### Caja Principal

```css
.box {
  background: var(--color-bg-light);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 0;
  margin-bottom: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

.box:hover {
  box-shadow: var(--shadow-md);
}
```

#### Encabezado de Caja

```css
.box-header {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--color-bg-gray);
}

.box-title {
  font-size: var(--font-size-xlarge);
  font-weight: 600;
  color: var(--color-accent);
  margin: 0;
}
```

#### Cuerpo de Caja

```css
.box-body {
  padding: var(--spacing-lg);
  min-height: 100px;
  overflow: visible;
}
```

#### Alturas Predefinidas

```css
.box-sm {
  min-height: 200px;
  max-height: 300px;
}

.box-md {
  min-height: 300px;
  max-height: 450px;
}

.box-lg {
  min-height: 450px;
  max-height: 600px;
}

.box-xl {
  min-height: 600px;
  max-height: 800px;
}
```

#### Excepción para Carrusel (Overflow para Flechas)

```css
.box:has(#cameraTrapImages) {
  overflow: visible;
  padding-bottom: 20px;
}

.box:has(#cameraTrapImages) .box-body {
  overflow: visible;
  padding: 20px 50px;
}
```

---

### 8. Carrusel de Imágenes (SlickR)

#### Contenedor del Carrusel

```css
.slick-slider {
  position: relative;
  display: block;
  box-sizing: border-box;
  user-select: none;
  touch-action: pan-y;
}

/* Padding para flechas laterales */
#favoriteSlider.slick-slider {
  padding: 0 50px;
}
```

#### Lista de Slides

```css
.slick-list {
  position: relative;
  overflow: hidden;
  display: block;
  margin: 0;
  padding: 0;
}

.slick-track {
  position: relative;
  display: flex;
  align-items: center;
  left: 0;
  top: 0;
}
```

#### Slides Individuales

```css
.slick-slide {
  display: flex;
  justify-content: center;
  align-items: center;
  height: auto;
  padding: 0 8px;
}

.slick-slide img {
  max-width: 100%;
  height: auto;
}
```

#### Flechas de Navegación

```css
.slick-prev,
.slick-next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  width: 40px;
  height: 40px;
  background-color: rgba(52, 152, 219, 0.8);
  border: none;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: var(--transition-base);
}

.slick-prev:before,
.slick-next:before {
  font-family: 'Arial', sans-serif;
  font-size: 20px;
  color: var(--color-text-light);
  line-height: 1;
}

.slick-prev:hover:before,
.slick-next:hover:before {
  color: #ffffff;
}

.slick-prev {
  left: -10px;
}

.slick-next {
  right: -10px;
}
```

#### Configuración Específica para 5 Imágenes

```css
#favoriteSlider .slick-slide {
  margin: 0 10px;
}

#favoriteSlider .slick-slide img {
  width: 100%;
  height: 180px;
  object-fit: cover;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);
}

#favoriteSlider .slick-slide img:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-lg);
}
```

#### Puntos de Navegación

```css
#favoriteSlider .slick-dots {
  display: none;
}

#favoriteSlider .slick-dots li button:before {
  color: var(--color-secondary);
  font-size: 12px;
}

#favoriteSlider .slick-dots li.slick-active button:before {
  color: var(--color-accent);
}
```

---

### 9. Gráficos (Plotly)

#### Contenedor de Gráficos Plotly

```css
.plotly {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: transparent;
  border: none;
}
```

#### Gráfico de Actividad Circadiana

```css
#activityPattern {
  height: 450px;
  width: 100%;
}

#activityPattern .plotly.html-widget {
  height: 100% !important;
}

#activityPattern .js-plotly-plot .plotly svg {
  height: 100% !important;
}
```

#### Barra de Herramientas Plotly

```css
.plotly .modebar {
  background: rgba(255, 255, 255, 0.9);
  border-radius: var(--radius-sm);
  padding: 4px;
}

.plotly .modebar-btn {
  background-color: transparent;
  border: none;
}

.plotly .modebar-btn:hover {
  background-color: rgba(52, 152, 219, 0.1);
}
```

#### Tooltips de Plotly

```css
.plotly .hoverlayer .hovertext {
  background-color: rgba(44, 62, 80, 0.9) !important;
  color: var(--color-text-light) !important;
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  font-size: var(--font-size-small);
}
```

#### Leyenda de Plotly

```css
.plotly .legend {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid var(--border-color);
}

.plotly text {
  font-family: 'Segoe UI', sans-serif;
}
```

---

### 10. Mapas (Leaflet)

#### Contenedor de Mapa

```css
.leaflet-container {
  width: 100%;
  height: 450px;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-color);
  background: #f8f9fa;
}

.box-lg .leaflet-container {
  height: 100%;
}
```

#### Popups de Leaflet

```css
.leaflet-popup-content-wrapper {
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

.leaflet-popup-content {
  font-size: var(--font-size-small);
}
```

#### Leyenda de Mapa

```css
.info.legend {
  background: rgba(255, 255, 255, 0.95);
  padding: 10px;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
}
```

---

### 11. Pie de Página

#### Logos Institucionales

```css
.footer-logos-img {
  width: 100%;
  max-width: 1200px;
  height: auto;
  display: block;
  margin: 0 auto;
  border-radius: var(--radius-md);
}

.footer-logos-box {
  background: var(--color-bg-light);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  box-shadow: var(--shadow-sm);
}
```

---

### 12. Responsividad

#### Tablets (768px - 1024px)

```css
@media (max-width: 1024px) {
  /* Reducir padding */
  .section-box {
    padding: var(--spacing-md);
  }
  
  /* Título más pequeño */
  .report-title {
    font-size: 2em;
  }
  
  /* Tabla de especies con scroll horizontal */
  .species-table-container {
    overflow-x: scroll;
  }
  
  /* Gráficos con altura reducida */
  .plotly,
  .leaflet-container {
    min-height: 350px;
  }
  
  /* Carrusel: 3 imágenes */
  #favoriteSlider .slick-slide img {
    height: 150px;
  }
}
```

#### Móviles (max-width: 768px)

```css
@media (max-width: 768px) {
  /* Tipografía reducida */
  html, body {
    font-size: 14px;
  }
  
  .report-title {
    font-size: 1.75em;
  }
  
  /* Indicadores apilados verticalmente */
  .indicators-table-real {
    font-size: 0.85em;
  }
  
  .indicators-table-real th,
  .indicators-table-real td {
    padding: 8px 6px;
  }
  
  /* Emojis más pequeños */
  .indicators-table-real .emoji-icon {
    font-size: 1.4em;
  }
  
  /* Carrusel: 2 imágenes */
  #favoriteSlider .slick-slide img {
    height: 120px;
  }
  
  /* Botones de ancho completo */
  .btn-apply-selection,
  .btn-clear-selection {
    width: 100%;
    margin-bottom: var(--spacing-sm);
  }
}
```

#### Móviles Pequeños (max-width: 480px)

```css
@media (max-width: 480px) {
  /* Tipografía mínima */
  html, body {
    font-size: 12px;
  }
  
  .report-title {
    font-size: 1.5em;
  }
  
  /* Tabla con scroll */
  .species-table-container table.dataTable {
    font-size: 0.8em;
  }
  
  /* Indicadores muy compactos */
  .indicators-table-real {
    font-size: 0.75em;
  }
  
  .indicators-table-real .emoji-icon {
    font-size: 1.2em;
  }
  
  /* Carrusel: 1 imagen */
  #favoriteSlider .slick-slide img {
    height: 200px;
  }
  
  /* Mapas y gráficos más pequeños */
  .plotly,
  .leaflet-container {
    min-height: 280px;
  }
}
```

#### Landscape Móviles (max-width: 768px, landscape)

```css
@media (max-width: 768px) and (orientation: landscape) {
  /* Tabla horizontal optimizada */
  .indicators-table-real {
    max-height: 60vh;
    overflow-y: auto;
  }
  
  /* Carrusel con altura reducida */
  #favoriteSlider .slick-slide img {
    height: 100px;
  }
  
  /* Gráficos compactos */
  .plotly,
  .leaflet-container {
    min-height: 250px;
  }
}
```

#### Pantallas Grandes (min-width: 1440px)

```css
@media (min-width: 1440px) {
  /* Limitar ancho máximo */
  .content-wrapper {
    max-width: 1400px;
    margin: 0 auto;
  }
  
  /* Tabla con ancho optimizado */
  .indicators-table-real {
    max-width: 1200px;
    margin: var(--spacing-md) auto;
  }
  
  /* Títulos más grandes */
  .report-title {
    font-size: 3em;
  }
  
  /* Carrusel: mantener 5 imágenes */
  #favoriteSlider .slick-slide img {
    height: 220px;
  }
}
```

---

## Clases de Utilidad

### Alineación de Texto

```css
.text-center { text-align: center; }
.text-right { text-align: right; }
.text-left { text-align: left; }
```

### Visibilidad

```css
.hidden { display: none !important; }
```

### Clearfix

```css
.clearfix::after {
  content: "";
  display: table;
  clear: both;
}
```

### Solo para Lectores de Pantalla

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

---

## Buenas Prácticas Aplicadas

### 1. Variables CSS

✅ **Centralización de valores**
- Todos los colores, tamaños y espaciados definidos en `:root`
- Facilita mantenimiento y consistencia
- Permite tematización fácil

### 2. Nomenclatura BEM

✅ **Clases descriptivas**
```css
.section-box
.section-box-title
.section-box-filters
```

✅ **Modificadores**
```css
.box-sm
.box-md
.box-lg
.box-xl
```

### 3. Mobile-First (Parcial)

✅ **Media queries en orden ascendente**
```css
/* Base: móvil */
@media (max-width: 768px) { }
@media (max-width: 1024px) { }
@media (min-width: 1440px) { }
```

### 4. Accesibilidad

✅ **Contraste de colores**
- Ratio mínimo 4.5:1 (WCAG AA)
- Texto oscuro sobre fondo claro

✅ **Focus states**
```css
.form-control:focus {
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
  outline: none;
}
```

✅ **Clase `.sr-only` para lectores de pantalla**

### 5. Rendimiento

✅ **Transiciones GPU-aceleradas**
```css
transform: translateY(1px);
transform: scale(1.05);
```

✅ **Suavizado de fuentes**
```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
```

### 6. Compatibilidad Cross-Browser

✅ **Prefijos de vendor**
```css
-webkit-font-smoothing: antialiased;
-moz-osx-font-smoothing: grayscale;
```

✅ **Fallbacks de fuentes**
```css
font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
```

---

## Componentes Destacados

### Tabla de Indicadores con Emojis

**Innovación:** Uso de emojis como iconografía visual en encabezados de tabla.

**Ventajas:**
- ✅ Universal (no requiere cargar iconos externos)
- ✅ Accesible (soporte nativo en navegadores)
- ✅ Responsive (escala automáticamente)

**Implementación:**
```html
<th>
  <span class="emoji-icon">🗂️</span>
  <span class="emoji-label">Imágenes</span>
</th>
```

### Carrusel con Overflow Controlado

**Problema:** Flechas de navegación recortadas por `overflow: hidden`.

**Solución:**
```css
.box:has(#cameraTrapImages) {
  overflow: visible;
  padding-bottom: 20px;
}

.box:has(#cameraTrapImages) .box-body {
  overflow: visible;
  padding: 20px 50px;
}
```

### Gradientes en Encabezados

**Efecto visual profesional:**
```css
background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
```

### Animaciones Sutiles

**Entrada de elementos:**
```css
@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
```

---

## Historial de Versiones

### v2.2 (2025-12-09)
- ✅ **Fixed:** Overflow de carrusel para visibilidad de flechas
- ✅ **Improved:** Responsividad en móviles
- ✅ **Added:** Animaciones de entrada

### v2.1 (2025-11-15)
- ✅ **Added:** Tabla de indicadores consolidados
- ✅ **Improved:** Emojis en encabezados
- ✅ **Fixed:** Separadores visuales entre grupos

### v2.0 (2025-10-01)
- ✅ **Refactor:** Migración a variables CSS
- ✅ **Added:** Sistema de z-index para selectores
- ✅ **Improved:** Accesibilidad y contraste

### v1.x (2020-2024)
- Versiones anteriores con estilos inline y clases custom

---

## Guía de Personalización

### Cambiar Paleta de Colores

**Editar variables en `:root`:**

```css
:root {
  /* Tema alternativo: Verde */
  --color-primary: #27ae60;
  --color-secondary: #2ecc71;
  --color-accent: #229954;
}
```

### Ajustar Espaciado

```css
:root {
  /* Espaciado más generoso */
  --spacing-md: 1.5rem;
  --spacing-lg: 2rem;
  --spacing-xl: 3rem;
}
```

### Cambiar Fuente

```css
html, body {
  font-family: 'Inter', 'Lato', 'Open Sans', sans-serif;
}
```

**Cargar fuente de Google Fonts:**

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
```

---

## Créditos

**Diseño y desarrollo:**
- Conservation International (2020)
- Instituto Humboldt (2025)

**Inspiración:**
- Material Design (Google)
- Flat UI Colors
- Bootstrap 5

---

## Licencia

Creative Commons License CC0 (Public Domain)

---

**Última actualización:** 2025-12-09
