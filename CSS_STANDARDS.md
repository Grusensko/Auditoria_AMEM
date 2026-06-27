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

### A. Marcado HTML Semántico
```html
<header class="site-header">
    <div class="header-container">
        <a href="/" class="site-logo">MDNTEC</a>
        
        <!-- Botón Hamburguesa con 3 líneas internas independientes -->
        <button class="menu-toggle" id="menu-toggle-btn" aria-label="Alternar menú de navegación" aria-expanded="false">
            <span class="hamburger-line"></span>
            <span class="hamburger-line"></span>
            <span class="hamburger-line"></span>
        </button>

        <!-- Navegación del sitio -->
        <nav class="nav-menu" id="site-nav">
            <ul class="nav-list">
                <li><a href="#services" class="nav-link">Servicios</a></li>
                <li><a href="#industries" class="nav-link">Industrias</a></li>
                <li><a href="#projects" class="nav-link">Proyectos</a></li>
                <li><a href="#contact" class="nav-link">Contacto</a></li>
            </ul>
        </nav>
    </div>
</header>
```

### B. Lógica de Estilos CSS (Maquetación y Animación a "X")

1. **Botón Hamburguesa (Estático y Activo):**
   El botón utiliza posicionamiento absoluto en sus líneas internas y la propiedad `transform` para lograr un cruce milimétrico y simétrico al convertirse en la "X", evitando holguras desalineadas.
2. **Navegación Móvil Desplizable (Responsive Drawer):**
   En resoluciones pequeñas, el menú de navegación se oculta a la derecha mediante `transform: translateX(100%)` y se desliza suavemente aplicando transiciones fluidas junto con un efecto difuminado de fondo (`backdrop-filter`).

```css
/* 1. Estilos del Botón de Control */
.menu-toggle {
    position: relative;
    width: 32px;
    height: 32px;
    background: transparent;
    border: none;
    cursor: pointer;
    display: none; /* Oculto en pantallas grandes */
    z-index: 1000;
}

.hamburger-line {
    position: absolute;
    left: 0;
    width: 100%;
    height: 3px;
    background-color: var(--text-primary);
    border-radius: 2px;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
                opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Distribución vertical de las tres barras */
.hamburger-line:nth-child(1) { top: 6px; }
.hamburger-line:nth-child(2) { top: 14px; }
.hamburger-line:nth-child(3) { top: 22px; }

/* ANIMACIÓN: Transformación de Hamburguesa a "X" al añadir la clase .active */
.menu-toggle.active .hamburger-line:nth-child(1) {
    /* Desplaza en Y al centro exacto (14px - 6px = 8px) y gira 45 grados */
    transform: translateY(8px) rotate(45deg);
    background-color: var(--color-blue);
}

.menu-toggle.active .hamburger-line:nth-child(2) {
    /* Desvanece y encoge la línea central */
    opacity: 0;
    transform: scaleX(0);
}

.menu-toggle.active .hamburger-line:nth-child(3) {
    /* Desplaza en Y al centro exacto (14px - 22px = -8px) y gira -45 grados */
    transform: translateY(-8px) rotate(-45deg);
    background-color: var(--color-blue);
}

/* 2. Navegación Móvil Drawer (Mobile Sidebar) */
@media (max-width: 768px) {
    .menu-toggle {
        display: block; /* Visible en móviles */
    }

    .nav-menu {
        position: fixed;
        top: 0;
        right: 0;
        width: min(320px, 80vw);
        height: 100vh;
        background-color: oklch(var(--bg-secondary) / 0.85);
        backdrop-filter: blur(12px);
        border-left: 1px solid var(--border-color);
        padding: 80px 24px 24px; /* Relleno superior para evitar solaparse con el logo/botón */
        display: flex;
        flex-direction: column;
        
        /* Desplazamiento inicial fuera de pantalla */
        transform: translateX(100%);
        transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Activación del menú lateral deslizante */
    .nav-menu.active {
        transform: translateX(0);
        box-shadow: -10px 0 30px rgba(0, 0, 0, 0.05);
    }

    .nav-list {
        flex-direction: column;
        gap: 20px;
    }
}
```

---

## 💡 10. Tips de CSS Moderno Recomendados (Buenas Prácticas)

Basado en las técnicas modernas de optimización de interfaz, se recomienda la adopción de los siguientes 5 tips de CSS modernos:

### A. Mejorar el Ajuste de Textos (`text-wrap: balance` y `text-wrap: pretty`)
Evita la aparición de palabras huérfanas en títulos o párrafos descriptivos.
* **`text-wrap: balance`:** Distribuye el texto de forma equitativa entre líneas. Ideal para cabeceras y títulos cortos (menos de 4 líneas).
* **`text-wrap: pretty`:** Optimiza la distribución del final del bloque para evitar que la última palabra quede sola. Ideal para párrafos de texto extensos.

```css
h1, h2, h3, .view-title {
    text-wrap: balance;
}

p, .kpi-subtitle {
    text-wrap: pretty;
}
```

### B. Mezclar Colores Nativamente con `color-mix()`
Permite mezclar dos colores en un espacio de color específico de manera directa sin preprocesadores. Es ideal para crear variantes transparentes o contrastadas en base a tus variables CSS:

```css
.card-item {
    /* Mezcla el color primario al 15% con fondo transparente en srgb */
    background-color: color-mix(in srgb, var(--color-blue) 15%, transparent);
}
```

### C. Uso del Selector de Relación `:has()`
Permite dar estilos a un elemento en función de si contiene a cierto descendiente o estado. Actúa como el esperado "selector de padres":

```css
/* Da estilos a una tarjeta de formulario solo si contiene un input con error */
.form-field:has(.input-error) {
    border-color: var(--color-red);
}

/* Cambia el fondo del header de la app si hay algún panel lateral abierto */
.app-header:has(~ .sidebar.active) {
    backdrop-filter: blur(10px);
}
```

### D. Propiedades Lógicas de Posicionamiento y Márgenes
Favorecen el diseño internacionalizable y comprensible en lugar de las físicas tradicionales:
* **`margin-inline: auto`** en lugar de `margin-left: auto; margin-right: auto;`.
* **`padding-block: 10px`** en lugar de `padding-top: 10px; padding-bottom: 10px;`.
* **`inset: 0`** en lugar de `top: 0; right: 0; bottom: 0; left: 0;`.

```css
.modal-overlay {
    position: fixed;
    inset: 0; /* Ocupa toda la pantalla */
    display: grid;
    place-items: center;
}
```

### E. Anidamiento Nativo (CSS Nesting)
Organiza tus estilos jerárquicamente de manera nativa sin Sass/Less, lo cual reduce la repetición de selectores y mejora la mantenibilidad:

```css
.sidebar {
    background-color: var(--bg-secondary);
    
    .menu-item {
        color: var(--text-secondary);
        
        &:hover {
            color: var(--text-primary);
        }
        
        &.active {
            color: var(--color-blue);
        }
    }
}
```

---

## 📝 11. Resumen de Buenas Prácticas CSS
* **Uso exclusivo de variables CSS (`:root`):** Todos los colores, tipografías y sombras deben mapearse a variables para facilitar cambios globales y soporte para temas (claro/oscuro).
* **Reset de Box-Model:** Siempre usar `box-sizing: border-box` en todos los elementos.
* **Scrollbars personalizadas y discretas:** Usar selectores `-webkit-scrollbar` para estilizar las barras de scroll y que no rompan la estética premium.
* **Sin `!important`:** Mantener la especificidad CSS baja y ordenada mediante el uso adecuado de selectores e nesting o metodologías como BEM si es necesario.
