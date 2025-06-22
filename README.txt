# Showroom Natura OjitOs - Web App

## Descripción General del Proyecto

"Showroom Natura OjitOs" es una aplicación web responsiva diseñada para la gestión integral de productos cosméticos, clientes, ventas y un catálogo público. La aplicación tiene como objetivo facilitar la administración del negocio y mejorar la experiencia de compra de los clientes.

## Tecnologías Utilizadas

-   **Backend**:
    -   Python 3.10+
    -   FastAPI: Framework web moderno y de alto rendimiento.
    -   SQLModel: Para la interacción con la base de datos, combinando SQLAlchemy y Pydantic.
    -   SQLite: Base de datos relacional ligera basada en archivos.
    -   Uvicorn: Servidor ASGI para FastAPI.
    -   Passlib[bcrypt]: Para el hashing de contraseñas.
    -   Python-JOSE[cryptography]: Para la generación y validación de JWT.
-   **Frontend**:
    -   HTML5
    -   CSS3
    -   JavaScript (ECMAScript 6+)
    -   Material Design 3: Principios de diseño (integración inicial mediante CDN para colores dinámicos y se espera una integración más profunda).
    -   Comfortaa: Tipografía principal.
    -   FontAwesome: Para iconos.
-   **Entorno de Desarrollo**:
    -   Visual Studio Code
    -   Windows 11 (Compatible con otros OS para ejecución)

## Configuración y Ejecución

### Backend

1.  **Clonar el Repositorio**:
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_CARPETA_REPOSITORIO>/backend
    ```

2.  **Crear y Activar Entorno Virtual**:
    (Se recomienda Python 3.10 o superior)
    ```bash
    python -m venv venv
    # En Windows
    .\venv\Scripts\activate
    # En macOS/Linux
    # source venv/bin/activate
    ```

3.  **Instalar Dependencias**:
    Asegúrate de que el archivo `requirements.txt` esté presente en la carpeta `backend`.
    ```bash
    pip install -r requirements.txt
    ```

4.  **Iniciar el Servidor Backend**:
    Desde la carpeta `backend`, ejecuta:
    ```bash
    uvicorn main:app --reload
    ```
    La API estará disponible en `http://127.0.0.1:8000`. La documentación interactiva de la API (Swagger UI) se encontrará en `http://127.0.0.1:8000/docs`.

    **Usuario Administrador por Defecto**:
    Al iniciar el backend por primera vez, se crea un usuario administrador si no existe:
    -   Email: `admin@example.com`
    -   Contraseña: `adminpass`

### Frontend

El frontend consiste en archivos HTML, CSS y JavaScript estáticos ubicados en la carpeta `frontend`.

1.  **Acceder a la Aplicación**:
    Simplemente abre los archivos HTML (por ejemplo, `index.html`, `login.html`, etc.) directamente en tu navegador web.
    Alternativamente, puedes servir la carpeta `frontend` utilizando cualquier servidor HTTP simple. Por ejemplo, con Python:
    ```bash
    # Desde la carpeta raíz del proyecto
    cd frontend
    python -m http.server 8080
    ```
    Luego, accede a `http://localhost:8080` en tu navegador.

    **Nota**: Para que el frontend se comunique correctamente con el backend, asegúrate de que el servidor backend esté corriendo (generalmente en `http://127.0.0.1:8000`). Las URLs de la API en el frontend están configuradas para apuntar a esa dirección.

## Módulos Principales Implementados

1.  **Autenticación y Roles**:
    -   Login de usuarios con email y contraseña (JWT).
    -   Roles: Administrador (`is_superuser`), Vendedor (`is_seller`), Cliente.
    -   Creación de usuarios (admin).
    -   Middleware de protección de rutas.

2.  **Gestión de Perfil de Cliente**:
    -   Los clientes pueden ver y actualizar su información de perfil (nickname, WhatsApp, género).
    -   Los clientes pueden subir/eliminar su foto de perfil.
    -   Los administradores pueden ver y gestionar perfiles de clientes, incluyendo su nivel.

3.  **Gestión de Inventario de Productos (Admin)**:
    -   CRUD completo para productos (nombre, descripción, precios, stock).
    -   Subida de imágenes de productos.
    -   Manejo de stock crítico.
    -   Asignación de tags y categoría a productos.

4.  **Gestión de Tags (Admin)**:
    -   CRUD global para tags.
    -   Los tags se pueden crear dinámicamente al asignarlos a un producto.

5.  **Gestión de Categorías (Admin)**:
    -   CRUD global para categorías.
    -   Los productos se asignan a una categoría mediante un ID.

6.  **Configuración del Sitio (Admin)**:
    -   Gestión de nombre del sitio, información de contacto, logo, colores del tema, enlaces a redes sociales, dirección.
    -   Parámetros del sistema como puntos por moneda y descuento por defecto.

7.  **Wishlist (Cliente)**:
    -   Los clientes pueden añadir/eliminar productos a/de su lista de deseos.
    -   Página dedicada para ver la wishlist.

8.  **Carrito de Compras**:
    -   Funcionalidad de carrito para invitados (usando `localStorage`).
    -   Carrito persistente para clientes logueados (guardado en backend).
    -   Fusión automática del carrito de invitado al backend al iniciar sesión.
    -   Gestión de cantidades, eliminación de ítems, vaciado del carrito.

9.  **Sistema de Puntos**:
    -   Los clientes ganan puntos con las compras (cuando la venta es "COBRADO").
    -   Administración de "Regalos Canjeables" (productos designados como regalos con un costo en puntos y stock para canje).
    -   Los clientes pueden solicitar el canje de regalos usando sus puntos.
    -   Los administradores gestionan las solicitudes de canje (aprobar, rechazar, marcar como entregado), lo cual afecta el stock del regalo y los puntos del cliente.

10. **Gestión de Ventas (Backend Admin CRUD)**:
    -   Creación de ventas por administradores, asociando productos y cliente.
    -   Cálculo automático de totales, descuentos y puntos ganados.
    -   Actualización del stock de productos al crear/cancelar ventas.
    -   Actualización de los puntos del cliente cuando la venta se marca como "COBRADO".
    -   Listado y filtrado de ventas. Los clientes pueden ver sus propias ventas.

11. **Catálogo Público**:
    -   Página visible para todos los usuarios (logueados o no).
    -   Muestra productos designados como "entradas de catálogo" por el administrador.
    -   Permite precios y imágenes específicas para el catálogo, diferentes del producto base.
    -   Indicadores de disponibilidad ("Agotado en catálogo", "Pocas unidades").
    -   Botones para añadir a wishlist o carrito.

12. **Dashboard Básico**:
    -   Tarjetas con estadísticas clave (ej. total de ventas, ventas por estado).
    -   Vista adaptada para administradores (global) y clientes (sus propios datos).

## Funcionalidades Pendientes / Próximos Pasos (Ejemplos)

-   Frontend completo para la Gestión de Ventas (Admin).
-   Notificaciones en la aplicación (ej. para canjes aprobados, poco stock).
-   Mejoras avanzadas de UI/UX (alertas toast, sidebars, etc.).
-   Herramientas de análisis y reportes (exportar datos).
-   Internacionalización y localización.
-   Tests unitarios y de integración.

---
*Este README fue generado y será actualizado por el asistente IA Jules.*
