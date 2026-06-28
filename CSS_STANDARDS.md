# Estándares de Layout y CSS Moderno: CSS Grid, Fluid Layouts y Container Queries

Este documento define la guía de diseño técnico, patrones y estándares de CSS para construir layouts premium, adaptables y modernos, sin depender de breakpoints rígidos basados en la pantalla completa ni de alturas fijas en píxeles.

---

## 📐 1. Estructura de Layout Principal (Grid Global)

Para aplicaciones tipo panel o dashboard, se prefiere estructurar la interfaz general utilizando una CSS Grid en lugar de Flexbox o floats. Esto permite que el sidebar, el header y el área de contenido se organicen de forma nativa en un plano bidimensional, garantizando que el contenido se estire de forma fluida para ocupar el 100% del espacio disponible sin desbordamientos inesperados.

### Patrón Recomendado: Grid de Tres Áreas
La pantalla completa se define con alturas en unidades de viewport (`vh`) y anchos de viewport (`vw`), distribuyendo el espacio mediante áreas nombradas (`grid-template-areas`):

```css
.app-layout {
    display: grid;
    grid-template-columns: clamp(240px, 20vw, 300px) 1fr;
    grid-template-rows: auto 1fr;
    grid-template-areas:
        "sidebar header"
        "sidebar content";
    height: 100vh;
    width: 100vw;
    overflow: hidden;
}

.layout-sidebar {
    grid-area: sidebar;
    height: 100%;
    overflow-y: auto;
}

.layout-header {
    grid-area: header;
}

.layout-content {
    grid-area: content;
    height: 100%;
    overflow-y: auto; /* O hidden si las subsecciones manejan sus propios scrolls */
}
```

---

## 👥 2. Layout Maestro/Detalle con Grid y Alturas Fluidas

El patrón Maestro/Detalle (listado de control a la izquierda, detalles extensos a la derecha) debe usar CSS Grid para un control preciso de la distribución de espacio.

### Reglas Clave:
1. **Sin alturas fijas en píxeles (`px`):** Las columnas se estiran verticalmente al 100% del contenedor padre (`height: 100%`).
2. **Columnas Fluidas:** Se utiliza `clamp()` para el panel maestro para asegurar que nunca sea demasiado pequeño ni demasiado grande.
3. **Scrolls Independientes:** El contenedor maestro y el de detalle tienen su propio scroll (`overflow-y: auto`), lo que permite que el usuario navegue en la lista sin perder de vista la cabecera general de la aplicación.

```css
.master-detail-layout {
    display: grid;
    grid-template-columns: clamp(260px, 28vw, 360px) 1fr;
    gap: clamp(16px, 2vw, 24px);
    height: 100%;
    overflow: hidden;
}

.layout-master {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden; /* Evita que el contenedor crezca más allá de la grid */
}

.master-list-wrapper {
    flex-grow: 1;
    overflow-y: auto; /* Scroll exclusivo para la lista */
}

.layout-detail {
    height: 100%;
    overflow-y: auto; /* Scroll exclusivo para la ficha de detalle */
}
```

---

## 📱 3. Responsividad Sin Breakpoints de Pantalla (Media Queries)

En interfaces de usuario modulares, diseñar basándose en el tamaño de la pantalla (`@media`) causa problemas cuando los componentes se reutilizan en diferentes contextos (ej. paneles laterales, modales o layouts de varias columnas).

### A. Container Queries (`@container`)
Permiten que un componente modifique su layout basándose únicamente en el espacio disponible en su contenedor directo.

1. **Definir el Contenedor:** El elemento padre debe registrarse como un contexto de contenedor.
2. **Aplicar la Query:** Modificar la disposición del hijo cuando el contenedor sea más angosto que un límite determinado.

```css
/* 1. Registrar el contenedor */
.view-pane {
    container-type: inline-size;
    container-name: view-container;
}

/* 2. Adaptar el Maestro/Detalle según el ancho de la vista */
@container view-container (max-width: 850px) {
    .master-detail-layout {
        grid-template-columns: 1fr;
        grid-template-rows: auto 1fr;
        overflow-y: auto;
    }
    
    .layout-master, 
    .layout-detail {
        height: auto;
        overflow: visible;
    }
}
```

### B. Valores Fluidos con `clamp()`
Para tipografías, márgenes y paddings, se prefiere el uso de `clamp()` en lugar de múltiples declaraciones `@media`. Esto asegura una escala fluida en cualquier resolución con una sola línea de código.

```css
/* Sintaxis: clamp(VALOR_MINIMO, VALOR_FLUIDO, VALOR_MAXIMO) */
.view-pane {
    padding: clamp(15px, 2.5vw, 30px);
}

.view-title {
    font-size: clamp(1.25rem, 2vw + 1rem, 1.85rem);
}
```

---

## 🚀 4. Layout Breakouts (Estructuración de Contenido)

Para el diseño de contenido y dashboards dentro de un panel, la técnica de **Layout Breakouts** permite que los elementos se posicionen en una cuadrícula central estable por defecto, pero permitiendo que ciertos elementos (como gráficos de ancho completo o banners de alerta) sobresalgan de la columna central de forma elegante sin romper la estructura.

### Estructura de la Grid de Breakout:
Definimos una cuadrícula de 5 columnas basada en variables CSS configurables:

```css
.layout-breakout {
    --padding-inline: clamp(16px, 3vw, 32px);
    --content-max-width: 1200px;
    --breakout-size: 80px;

    display: grid;
    grid-template-columns:
        [full-width-start] minmax(var(--padding-inline), 1fr)
        [breakout-start] minmax(0, var(--breakout-size))
        [content-start] min(100% - (var(--padding-inline) * 2), var(--content-max-width)) [content-end]
        minmax(0, var(--breakout-size)) [breakout-end]
        minmax(var(--padding-inline), 1fr) [full-width-end];
}

/* Todos los hijos directos van a la columna central por defecto */
.layout-breakout > * {
    grid-column: content;
}

/* Bloques tipo Popout/Breakout (sobresalen un poco a los lados) */
.layout-breakout > .breakout {
    grid-column: breakout;
}

/* Bloques de ancho completo (de borde a borde de la pantalla) */
.layout-breakout > .full-width {
    grid-column: full-width;
}
```

---

## 🗂️ 5. Alineación Perfecta de Tarjetas con `subgrid`

Cuando se colocan múltiples tarjetas (cards) una al lado de la otra (por ejemplo, en cuadrículas o carruseles horizontales), es común que el contenido de cada una (cabeceras, descripciones, botones) tenga longitudes variables. Para evitar el uso de alturas fijas en píxeles que rompan el diseño o que las secciones internas queden desalineadas verticalmente, se debe utilizar `grid-template-rows: subgrid` o `grid-template-columns: subgrid`.

Esto permite que cada tarjeta hija herede y se sincronice con la definición de la cuadrícula del contenedor padre, haciendo que los elementos internos (como títulos, imágenes o botones de todas las tarjetas de una misma fila) se alineen perfectamente al centavo de forma horizontal.

### Patrón Recomendado para Tarjetas en Fila (Grid / Carruseles)
El contenedor padre define la cuadrícula general y las filas dedicadas a cada sección interna de la tarjeta. El elemento tarjeta (hijo directo) adopta estas filas heredándolas con `subgrid`:

```css
/* 1. Contenedor de Tarjetas (Fila o Carrusel) */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    /* Cada tarjeta en la fila ocupará exactamente 4 filas de la grid */
    grid-auto-rows: auto;
    gap: 20px;
}

/* 2. La Tarjeta individual abarca las filas y activa subgrid */
.card-item {
    display: grid;
    /* Indicamos que la tarjeta se extienda a lo largo de 4 filas de la cuadrícula padre */
    grid-row: span 4;
    /* Heredamos las definiciones de fila del padre para alinearlas entre tarjetas */
    grid-template-rows: subgrid;
    background-color: var(--bg-card);
    border-radius: 12px;
    border: 1px solid var(--border-color);
    padding: 20px;
}

/* 3. Componentes internos mapeados a sus respectivas subfilas */
.card-item .card-media       { grid-row: 1; }
.card-item .card-title       { grid-row: 2; }
.card-item .card-description { grid-row: 3; }
.card-item .card-footer      { grid-row: 4; }
```

---

## 🎨 6. Paletas de Colores Accesibles y Consistentes con `oklch()`

Para lograr diseños premium, interfaces consistentes y contraste accesible (WCAG), se prefiere el uso del modelo de color **OKLCH** (`oklch(L C H)`) en lugar de Hex, RGB o HSL clásicos.

### Definición de Paletas en Variables CSS
Utilizaremos variables CSS para almacenar las coordenadas OKLCH y luego declararemos los colores finales usando esas variables. Esto permite generar estados dinámicos (como hover) modificando únicamente una propiedad:

```css
:root {
    --color-primary-l: 0.55;
    --color-primary-c: 0.22;
    --color-primary-h: 250;
    
    --color-primary: oklch(var(--color-primary-l) var(--color-primary-c) var(--color-primary-h));
    --color-primary-hover: oklch(calc(var(--color-primary-l) + 0.08) var(--color-primary-c) var(--color-primary-h));
    --color-primary-active: oklch(calc(var(--color-primary-l) - 0.06) var(--color-primary-c) var(--color-primary-h));
}
```

---

## 🌀 7. Transiciones de Navegación Fluidas (View Transitions API)

Para lograr transiciones premium entre pantallas o páginas de forma nativa y fluida sin depender de pesadas librerías de JavaScript, se debe utilizar la directiva de la API de **View Transitions** para habilitar transiciones entre documentos (cross-document transitions) soportadas por los navegadores modernos.

### Regla de Configuración
Se prefiere declarar de forma global la directiva en la hoja de estilos:

```css
@view-transition {
    navigation: auto;
}
```

---

## 🏷️ 8. Etiquetas Flotantes en Formularios con CSS Puro (Floating Labels)

Para lograr formularios premium, minimalistas y limpios, se debe implementar el patrón de **Etiquetas Flotantes (Floating Labels)** en los inputs utilizando únicamente selectores de CSS moderno (`:placeholder-shown` y `:focus-within`), eliminando cualquier lógica de JavaScript.

### Implementación Recomendada
```html
<div class="form-field">
    <input type="text" id="user-email" class="form-input" placeholder=" " required autocomplete="email">
    <label for="user-email" class="form-label">Correo Electrónico</label>
</div>
```

```css
.form-field {
    position: relative;
    margin-bottom: 20px;
    width: 100%;
}

.form-input {
    width: 100%;
    padding: 18px 16px 6px;
    font-size: 14px;
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-radius: 10px;
    outline: none;
    color: var(--text-primary);
    transition: border-color 0.2s, box-shadow 0.2s;
}

.form-label {
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-muted);
    font-size: 14px;
    font-weight: 500;
    pointer-events: none;
    transition: all 0.2s ease-in-out;
}

.form-input:focus ~ .form-label,
.form-input:not(:placeholder-shown) ~ .form-label {
    top: 12px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--color-blue);
    transform: translateY(0);
}
```

---

## 🍔 9. Menú de Navegación Responsive y Botón Hamburguesa Animado

Para lograr una navegación fluida en dispositivos móviles, se debe utilizar una estructura limpia de menú de navegación en el header con un botón de control hamburguesa que realice una transición visual premium convirtiéndose en una "X" cuando el menú esté activo.

---

## 💡 10. Tips de CSS Moderno Recomendados (Buenas Prácticas)

Basado en las técnicas modernas de optimización de interfaz, se recomienda la adopción de los siguientes 5 tips de CSS modernos:

### A. Mejorar el Ajuste de Textos (`text-wrap: balance` y `text-wrap: pretty`)
Evita la aparición de palabras huérfanas en títulos o párrafos descriptivos.

### B. Mezclar Colores Nativamente con `color-mix()`
Permite mezclar dos colores en un espacio de color específico de manera directa sin preprocesadores.

### C. Uso del Selector de Relación `:has()`
Permite dar estilos a un elemento en función de si contiene a cierto descendiente o estado.

### D. Propiedades Lógicas de Posicionamiento y Márgenes
Favorecen el diseño internacionalizable y comprensible en lugar de las físicas tradicionales.

### E. Anidamiento Nativo (CSS Nesting)
Organiza tus estilos jerárquicamente de manera nativa sin Sass/Less.

---

## 📏 11. Reglas Generales de Maquetación y Medidas

Para asegurar la coherencia del diseño, accesibilidad y facilidad de mantenimiento del proyecto, el desarrollo de estilos debe cumplir con las siguientes restricciones fundamentales:

### A. Unidad de Medida Preferida: `rem`
* **Estándar:** Se utilizará la unidad **`rem`** como la medida preferida para fuentes, márgenes, rellenos (padding) y dimensionamiento de contenedores.
* **Excepción:** Se reservan los píxeles (`px`) exclusivamente para bordes delgados (ej. `1px solid var(--border-color)`) o sombras muy específicas, y porcentajes (`%`) o fracciones (`fr`) para divisiones de cuadrículas.
* **Propósito:** Mantener la consistencia con la escala de accesibilidad del navegador del usuario (si el usuario cambia el tamaño base de letra, toda la interfaz se escalará proporcionalmente de forma automática).

```css
.card-item {
    padding: 1.5rem;      /* ~24px */
    margin-bottom: 1rem;  /* ~16px */
    border-radius: 0.5rem; /* ~8px */
}
```

### B. Uso Preferente de CSS Grid sobre Flexbox
* **Grid primero:** Se prioriza el uso de **CSS Grid** para el diseño estructural (tanto bidimensional como unidimensional) para forzar una alineación geométrica fluida.
* **Cuándo usar Flexbox:** Se permite y recomienda usar **Flexbox** en situaciones puntuales de distribución lineal simple y unidimensional:
  * Elementos inline pequeños agrupados (ej. badges en fila, botones alineados en el pie de tarjeta).
  * Centrado de iconos dentro de un círculo o botón.
  * Barras de herramientas simples.

### C. Prohibición de Etiquetas `<br />` para Maquetación
* **Regla estricta:** **Queda terminantemente prohibido utilizar etiquetas `<br />`** (saltos de línea) en el HTML con el fin de generar espaciado, márgenes verticales o acomodar elementos.
* **Buenas prácticas:** Todo control de distancia, saltos, y espaciado vertical u horizontal debe ser manejado de forma exclusiva en CSS utilizando márgenes (`margin-bottom`), paddings o la propiedad `gap` de Grid/Flexbox.

```html
<!-- INCORRECTO -->
<div class="card-title">Título</div>
<br />
<div class="card-desc">Descripción</div>

<!-- CORRECTO -->
<div class="card-title" style="margin-bottom: 0.75rem;">Título</div>
<div class="card-desc">Descripción</div>
```

---

## 📝 12. Resumen de Buenas Prácticas CSS
* **Uso exclusivo de variables CSS (`:root`):** Todos los colores, tipografías y sombras deben mapearse a variables para facilitar cambios globales y soporte para temas (claro/oscuro).
* **Reset de Box-Model:** Siempre usar `box-sizing: border-box` en todos los elementos.
* **Scrollbars personalizadas y discretas:** Usar selectores `-webkit-scrollbar` para estilizar las barras de scroll y que no rompan la estética premium.
* **Sin `!important`:** Mantener la especificidad CSS baja y ordenada mediante el uso adecuado de selectores e nesting o metodologías como BEM si es necesario.
