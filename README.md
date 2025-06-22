# Showroom Natura OjitOs

## Descripción General del Proyecto

"Showroom Natura OjitOs" es una aplicación web diseñada para la gestión integral de un showroom de productos cosméticos. Permite administrar el catálogo de productos visibles para clientes, gestionar el inventario base, clientes (usuarios), ventas, y personalizar la apariencia y comportamiento del sitio.

La aplicación cuenta con distintos roles de usuario (clientes, vendedores y administradores) con diferentes niveles de acceso y funcionalidades. Los clientes pueden navegar el catálogo, gestionar su perfil, carrito de compras, lista de deseos y ver su historial de compras y canjes de puntos. Los administradores tienen control total sobre todos los módulos, incluyendo la configuración del sitio, gestión de usuarios, productos, categorías, tags, catálogo y procesamiento de ventas y canjes.

### Funcionalidades Principales Implementadas:

*   **Autenticación y Roles:** Sistema de login con JWT. Roles de Administrador (superuser), Vendedor (`is_seller`), y Cliente. Creación de admin por defecto al inicio.
*   **Gestión de Configuración del Sitio (Admin):** Personalización de nombre, información de contacto, logo, colores de marca, enlaces a redes sociales, dirección y parámetros básicos del sistema.
*   **Gestión de Productos (Admin):** CRUD completo para productos del inventario, incluyendo múltiples precios (revista, showroom, feria calculados), gestión de stock (actual y crítico) e imágenes.
*   **Gestión de Categorías (Admin):** CRUD completo para categorías de productos. Asignación de una categoría a productos.
*   **Gestión de Tags (Admin):** CRUD completo para tags. Asignación de múltiples tags a productos (relación muchos-a-muchos).
*   **Gestión de Clientes (Admin y Cliente):**
    *   Admin: Listar, filtrar y editar perfiles de clientes (nivel, datos de contacto, imagen). Ver historial de compras y canjes.
    *   Cliente: Ver y editar su propio perfil (datos de contacto, imagen).
*   **Gestión de Catálogo (Admin):** Permite crear una vista curada de productos para clientes, con posibilidad de sobrescribir precio, imagen y marcar como "agotado" específicamente para el catálogo.
*   **Wishlist (Cliente):** Funcionalidad completa para añadir, ver y eliminar productos de una lista de deseos personal.
*   **Carrito de Compras (Cliente e Invitado):**
    *   Gestión de carrito para usuarios logueados (persistente en BD) y para invitados (en `localStorage`).
    *   Fusión de carrito de invitado al carrito del backend al iniciar sesión.
    *   Funcionalidades: añadir, ver, actualizar cantidad, eliminar item, vaciar carrito.
*   **Sistema de Puntos (Regalos):**
    *   Clientes acumulan puntos con ventas cobradas.
    *   Admin configura productos como "Regalos" canjeables (con costo en puntos y stock de canje).
    *   Clientes pueden ver regalos y solicitar canjes.
    *   Admin gestiona solicitudes de canje (aprobar/rechazar/entregar), lo que afecta puntos del cliente y stock de regalos.
    *   Clientes pueden ver el estado de sus solicitudes y sus puntos disponibles.
*   **Gestión de Ventas (Backend Completo, Frontend Admin Pendiente):**
    *   CRUD de ventas con items detallados (producto, cantidad, precio de venta, subtotal).
    *   Cálculo y almacenamiento de total de venta, descuentos, puntos ganados.
    *   Gestión de estados de venta (`SaleStatusEnum`).
    *   **Gestión de Stock:** Verificación y decremento de stock al crear la venta, y reversión de stock al cancelar la venta.
*   **Dashboard (Backend Básico):** Endpoints que ahora se conectan a datos reales de ventas para mostrar conteos/sumas según estados (ej. Ventas Entregadas, A Cobrar), con lógica de visualización para admin (global) y cliente (propias).
*   **Modo Oscuro:** Toggle para cambiar entre tema claro y oscuro en el frontend.

## Tecnologías Utilizadas

### Backend
*   **Lenguaje:** Python 3.x
*   **Framework API:** FastAPI
*   **ORM y Validación de Datos:** SQLModel (combina SQLAlchemy y Pydantic)
*   **Base de Datos:** SQLite (integrada, archivo `showroom_natura.db` en la carpeta `backend`)
*   **Autenticación:** JWT (JSON Web Tokens) con `python-jose[cryptography]` para generación/validación y `passlib[bcrypt]` para hashing de contraseñas.
*   **Servidor ASGI:** Uvicorn

### Frontend
*   **Lenguajes Base:** HTML5, CSS3, JavaScript (ES6+)
*   **Diseño y Estilos:**
    *   Se utilizan principios de Material Design. Se enlaza una librería CDN para colores dinámicos de Material Design 3 (`material-dynamic-colors`).
    *   Estilos personalizados en `frontend/css/style.css` con variables CSS para temas (claro/oscuro).
*   **Tipografía:** Comfortaa (cargada desde Google Fonts).
*   **Iconos:** FontAwesome (cargada desde CDN).
*   **Interacción con API:** JavaScript nativo (`fetch` API).
*   **Almacenamiento Local:** `localStorage` para el token de autenticación, información del usuario, y carrito de invitado.

### Entorno de Desarrollo (Ejemplo)
*   **Sistema Operativo:** Windows 11 (desarrollado pensando en compatibilidad general)
*   **Editor de Código:** Visual Studio Code
*   **Gestión de Entorno Python:** `venv`
*   **Control de Versiones:** Git (implícito)

## Configuración y Ejecución del Proyecto en Windows

Sigue estos pasos para configurar y ejecutar la aplicación en un entorno Windows.

### Requisitos Previos

*   **Python:** Asegúrate de tener Python 3.8 o superior instalado. Puedes descargarlo desde [python.org](https://www.python.org/). Durante la instalación, marca la opción "Add Python to PATH".
*   **Git:** (Opcional) Si vas a clonar el repositorio. Puedes descargarlo desde [git-scm.com](https://git-scm.com/).
*   **Navegador Web:** Cualquier navegador moderno (Chrome, Firefox, Edge).

### Pasos para el Backend

1.  **Obtener el Código:**
    *   Clona el repositorio: `git clone <url_del_repositorio>`
    *   O descarga y descomprime el archivo ZIP del proyecto.
    *   Navega en la terminal a la carpeta raíz del proyecto, y luego a la subcarpeta `backend`.

2.  **Crear y Activar Entorno Virtual:**
    *   Abre una terminal (Command Prompt, PowerShell, o Git Bash) en la carpeta `backend`.
    *   Crea el entorno virtual: `python -m venv .venv`
    *   Activa el entorno virtual: `.venv\Scripts\activate`
        *   (Si usas Git Bash, el comando podría ser: `source .venv/Scripts/activate`)

3.  **Instalar Dependencias:**
    *   Con el entorno virtual activado, ejecuta:
        ```bash
        pip install fastapi uvicorn sqlalchemy sqlmodel "python-jose[cryptography]" "passlib[bcrypt]" python-multipart "jinja2" "aiofiles"
        ```
        *(Nota: Jinja2 y aiofiles son dependencias comunes de FastAPI para plantillas y archivos estáticos, aunque no las estemos usando explícitamente para servir el frontend en este setup, Uvicorn o FastAPI podrían requerirlas transitivamente o para funcionalidades completas. Se incluyen por completitud).*

4.  **Ejecutar la Aplicación Backend:**
    *   Desde la carpeta `backend` (con el entorno virtual activado), ejecuta:
        ```bash
        uvicorn main:app --reload
        ```
    *   Esto iniciará el servidor de desarrollo de FastAPI. Verás mensajes en la consola indicando que la aplicación está corriendo, usualmente en `http://127.0.0.1:8000`.
    *   **Importante:** La primera vez que ejecutes el backend:
        *   Se creará automáticamente la base de datos `showroom_natura.db` en la carpeta `backend`.
        *   Se creará la configuración por defecto del sitio.
        *   Se creará un **usuario administrador por defecto** si no existe ningún otro superusuario. Las credenciales se mostrarán en la consola del servidor. Usualmente serán:
            *   **Email:** `admin@example.com`
            *   **Contraseña:** `adminpass`
            *   (¡Recuerda cambiar esta contraseña en un entorno real!).

### Pasos para el Frontend

1.  **Configurar URL de la API:**
    *   Abre el archivo `frontend/js/auth.js` en un editor de texto.
    *   Localiza la constante `API_BASE_URL`.
    *   Si estás abriendo los archivos HTML directamente desde tu sistema de archivos (ej. `file:///C:/path/to/frontend/index.html`), debes establecer esta constante a la URL completa de tu backend:
        ```javascript
        const API_BASE_URL = 'http://127.0.0.1:8000';
        ```
    *   Si en el futuro sirves el frontend desde un servidor web (ej. Live Server de VS Code en un puerto diferente, o Nginx), y el backend está en `http://127.0.0.1:8000`, también necesitarás la URL completa debido a la política de Same-Origin (CORS ya está configurado en el backend para permitir `*`, pero las URLs base explícitas son más claras para `fetch`).
    *   Si sirvieras frontend y backend desde el mismo dominio y puerto (ej. usando FastAPI para servir los archivos estáticos del frontend), entonces `API_BASE_URL = '';` sería correcto. **Para la prueba local abriendo archivos HTML directamente, usa la URL completa.**

2.  **Abrir Archivos HTML:**
    *   Navega a la carpeta `frontend`.
    *   Abre cualquiera de los siguientes archivos HTML directamente en tu navegador web (ej. haciendo doble clic):
        *   `login.html` (para iniciar sesión)
        *   `catalog.html` (para ver el catálogo público)
        *   `index.html` (Dashboard, que mostrará datos si estás logueado y el backend funciona)
    *   Una vez logueado como admin o cliente, podrás navegar a las otras secciones a través de los enlaces en el header.

¡Con esto, la aplicación debería estar funcionando localmente!

## Perfiles de Usuario y Pruebas

La aplicación soporta tres roles principales: Administrador, Vendedor y Cliente.

### 1. Usuario Administrador (Superuser)

*   **Acceso/Creación:**
    *   Al iniciar el backend por primera vez (`uvicorn main:app --reload`), se crea automáticamente un superusuario administrador por defecto si no existe ninguno. Las credenciales se mostrarán en la consola del servidor:
        *   **Email:** `admin@example.com`
        *   **Contraseña:** `adminpass`
    *   Inicia sesión usando estas credenciales en `frontend/login.html`.
*   **Funcionalidades Clave a Probar:**
    *   **Navegación:** Deberías ver todos los enlaces de administración en el header (Admin Clientes, Admin Config, Admin Tags, Admin Categorías, Admin Catálogo, Admin Canjes) además de los enlaces de usuario (Mi Wishlist, Mi Carrito, Mi Perfil, Logout).
    *   **Dashboard (`index.html`):** Visualizar estadísticas globales de ventas (ej. Ventas Entregadas, A Cobrar, etc., basadas en todos los datos del sistema).
    *   **Gestión de Productos (`products.html`):**
        *   Crear, editar y eliminar productos del inventario.
        *   Asignar/modificar múltiples tags (separados por comas, ej. "frutal, oferta") a un producto.
        *   Asignar/modificar la categoría de un producto usando el menú desplegable.
        *   Probar los filtros de la tabla de productos (búsqueda, categoría, stock bajo).
        *   Verificar la alerta visual de stock crítico.
        *   Probar la subida de imágenes para productos.
        *   (Como admin logueado) Probar añadir productos a tu wishlist y carrito desde esta tabla (para probar los botones).
    *   **Gestión de Clientes (`admin_clients.html`):**
        *   Listar y filtrar clientes (por ID, estado, nivel).
        *   Editar el perfil de un cliente (apodo, WhatsApp, género, nivel de cliente: Plata/Diamante).
        *   Subir/eliminar imagen de perfil para un cliente.
        *   Acceder al historial de compras de un cliente a través del botón "Ver Historial".
    *   **Configuración del Sitio (`admin_config.html`):**
        *   Modificar y guardar todos los parámetros: Nombre del sitio, información de contacto, colores de marca (primario, secundario, acento), enlaces a redes sociales, dirección del showroom, parámetros de sistema (puntos por unidad monetaria, % descuento showroom).
        *   Subir un nuevo logo para el sitio.
    *   **Gestión de Tags (`admin_tags.html`):**
        *   Crear nuevos tags globales.
        *   Editar nombres de tags existentes.
        *   Eliminar tags (esto los desvinculará de los productos).
    *   **Gestión de Categorías (`admin_categories.html`):**
        *   Crear nuevas categorías con nombre y descripción.
        *   Editar categorías existentes.
        *   Eliminar categorías (esto desvinculará los productos, estableciendo su `category_id` a `null`).
    *   **Gestión de Catálogo (`admin_catalog.html`):**
        *   Añadir productos del inventario al catálogo público.
        *   Establecer precios, imágenes, y texto promocional específicos para el catálogo (sobrescribiendo los del producto base si se desea).
        *   Marcar entradas del catálogo como "Visible" u "Oculto".
        *   Marcar entradas del catálogo como "Agotado (Catálogo)" (independiente del stock real del inventario).
        *   Gestionar el orden de visualización.
        *   Editar y eliminar entradas del catálogo.
    *   **Gestión de Solicitudes de Canje (`admin_redemptions.html`):**
        *   Listar y filtrar todas las solicitudes de canje de puntos.
        *   Ver el detalle de una solicitud.
        *   **Aprobar** una solicitud pendiente (verificar que los puntos del cliente y el stock del regalo se descuenten correctamente).
        *   **Rechazar** una solicitud pendiente.
        *   **Marcar como Entregada** una solicitud aprobada.
        *   Añadir notas administrativas a las solicitudes.
    *   **Creación de Nuevos Usuarios (vía API):**
        *   Usando una herramienta de API (como Postman, o la interfaz `/docs` de FastAPI), un admin puede crear nuevos usuarios enviando un POST a `/users/` con el token de admin.
        *   En el payload, puede especificar `email`, `full_name`, `password`, y también `is_superuser: true` (para crear otro admin) o `is_seller: true` (para crear un vendedor). Si ambos son `false` o no se especifican, se crea un cliente.

### 2. Usuario Vendedor (Rol `is_seller=True`, `is_superuser=False`)

*   **Creación:**
    *   Debe ser creado por un Usuario Administrador. El administrador debe enviar un POST a `/users/` (usando su token de admin) con el payload incluyendo `email`, `full_name`, `password`, y `is_seller: true`.
*   **Login:**
    *   Usar `frontend/login.html` con el email y contraseña definidos por el admin.
*   **Funcionalidades Clave a Probar:**
    *   **Navegación:** Debería ver los enlaces de usuario (Mi Wishlist, Mi Carrito, Mi Perfil, Canjear Puntos, Logout) pero **NO** los enlaces "Admin *".
    *   **Dashboard (`index.html`):** Debería ver sus propias estadísticas de ventas si la lógica de "no superuser" en los endpoints del dashboard se aplica a vendedores que también son `user_id` en ventas. (Actualmente, si un vendedor crea una venta para un cliente, el `user_id` de la venta es el del cliente. Si el vendedor es también un cliente y tiene sus propias ventas, las vería. Se necesita clarificar si un vendedor tiene un "dashboard de vendedor").
        *   **Nota:** El rol `is_seller` actualmente no otorga permisos especiales en el backend más allá de identificar al usuario como vendedor. No hay endpoints específicos protegidos para "solo vendedores" ni una UI de admin para vendedores.
    *   **Creación de Clientes:**
        *   **Pendiente de Implementación:** El plan original indica "Los usuarios vendedores y el admin pueden crear los usuarios de los clientes". El endpoint `POST /users/` actualmente solo permite a `is_superuser` crear usuarios. Esto necesitaría un ajuste en el backend para que un `current_creator` con `is_seller=True` pueda crear usuarios que *no* sean `is_superuser` ni `is_seller`.
    *   **Otras Funcionalidades:** Debería poder usar todas las funcionalidades de cliente (catálogo, perfil, wishlist, carrito, historial de compras/canjes).

### 3. Usuario Cliente (Rol `is_seller=False`, `is_superuser=False`)

*   **Creación:**
    *   Debe ser creado por un Usuario Administrador (o un Vendedor, una vez que se implemente ese permiso). El creador enviará un POST a `/users/` con el payload del cliente (email, full_name, password) asegurándose que `is_superuser` e `is_seller` sean `false` o no se incluyan (usarán default `False`).
    *   **Importante:** Los clientes no pueden auto-registrarse.
*   **Login:**
    *   Usar `frontend/login.html` con el email y contraseña proporcionados por el admin/vendedor.
*   **Funcionalidades Clave a Probar:**
    *   **Navegación:** Solo enlaces de usuario/públicos visibles (Catálogo, Mi Wishlist, Mi Carrito, Canjear Puntos, Mi Perfil, Logout/Login). No enlaces "Admin *".
    *   **Catálogo Público (`catalog.html`):**
        *   Ver productos del catálogo.
        *   Ver alertas de stock ("AGOTADO (CATÁLOGO)", "¡Pocas unidades!").
        *   Añadir productos a la wishlist (si está logueado).
        *   Añadir productos al carrito (como invitado si cierra sesión, o como logueado).
    *   **Carrito de Invitado y Fusión:**
        *   Añadir items al carrito sin estar logueado.
        *   Ver el carrito de invitado en `my_cart.html`.
        *   Iniciar sesión. Verificar que el carrito de invitado se fusione con el del backend.
    *   **Mi Wishlist (`my_wishlist.html`):**
        *   Ver su lista de deseos.
        *   Eliminar items.
        *   Añadir items al carrito desde la wishlist (y opcionalmente eliminarlos de la wishlist).
    *   **Mi Carrito (`my_cart.html`):**
        *   Ver items del carrito (fusionado o solo de backend).
        *   Modificar cantidades.
        *   Eliminar items.
        *   Vaciar carrito.
        *   Ver total. Botón "Continuar Compra" (actualmente placeholder) o "Iniciar Sesión para Continuar".
    *   **Mi Perfil (`my_profile.html`):**
        *   Ver sus datos (nombre, email, apodo, WhatsApp, género, nivel de cliente, puntos disponibles).
        *   Editar apodo, WhatsApp, género.
        *   Cambiar/eliminar su imagen de perfil.
        *   Ver su historial de solicitudes de canje y sus estados.
        *   Ver su historial de compras (enlace a `admin_client_history.html?user_id=X`).
    *   **Canjear Puntos (`redeem_gifts.html`):**
        *   Ver sus puntos disponibles.
        *   Ver regalos activos y con stock de canje.
        *   Verificar que los botones "Canjear" estén deshabilitados si no tiene puntos o no hay stock.
        *   Enviar una solicitud de canje. Verificar que aparezca en "Mis Solicitudes de Canje" en estado "Pendiente".
    *   **Dashboard (`index.html`):** Ver sus propias estadísticas de ventas (si aplica la lógica de no-superuser).
