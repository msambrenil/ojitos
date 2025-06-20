// DOM Elements
const productModal = document.getElementById('product-form-section');
const productForm = document.getElementById('product-form');
const modalTitle = document.getElementById('modal-title');
const productIdField = document.getElementById('form-product-id');
const productNameField = document.getElementById('form-product-name');
const productDescriptionField = document.getElementById('form-product-description');
const productCategoryField = document.getElementById('form-product-category');
const productTagsField = document.getElementById('form-product-tags');
const productPriceRevistaField = document.getElementById('form-product-price-revista');
const productStockActualField = document.getElementById('form-product-stock-actual');
const productStockCriticoField = document.getElementById('form-product-stock-critico');
const productImageField = document.getElementById('form-product-image');
const currentImagePreview = document.getElementById('current-image-preview');

const addNewProductButton = document.getElementById('add-new-product-button');
const cancelProductButton = document.getElementById('cancel-product-button');
const modalCloseButton = document.getElementById('modal-close-button'); // New ID from HTML
const productTableBody = document.getElementById('product-table-body');


// Modal Control Functions
function openProductModal() {
    if(productModal) productModal.style.display = 'block';
}

function closeProductModal() {
    if(productModal) productModal.style.display = 'none';
    if(productForm) productForm.reset();
    if(currentImagePreview) currentImagePreview.innerHTML = '';
    if(productIdField) productIdField.value = ''; // Clear product ID on close
}

// Event Listeners for Modal Control
if (addNewProductButton) {
    addNewProductButton.addEventListener('click', openModalForCreate);
}
if (cancelProductButton) {
    cancelProductButton.addEventListener('click', closeProductModal);
}
if (modalCloseButton) {
    modalCloseButton.addEventListener('click', closeProductModal);
}
// Close modal if clicked outside of modal-content
if (productModal) {
    productModal.addEventListener('click', (event) => {
        if (event.target === productModal) {
            closeProductModal();
        }
    });
}

// Prepare Modal for Create
function openModalForCreate() {
    if(modalTitle) modalTitle.textContent = "Añadir Nuevo Producto";
    if(productForm) productForm.reset();
    if(productIdField) productIdField.value = '';
    if(currentImagePreview) currentImagePreview.innerHTML = '<p>No hay imagen seleccionada.</p>';
    openProductModal();
}

// Prepare Modal for Edit
async function openModalForEdit(productId) {
    if(modalTitle) modalTitle.textContent = "Editar Producto";
    if(productForm) productForm.reset(); // Reset form first

    try {
        const response = await fetch(`/api/products/${productId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch product. Status: ${response.status}`);
        }
        const product = await response.json();

        if(productIdField) productIdField.value = product.id;
        if(productNameField) productNameField.value = product.name || '';
        if(productDescriptionField) productDescriptionField.value = product.description || '';
        if(productCategoryField) productCategoryField.value = product.category || '';
        if(productTagsField) productTagsField.value = product.tags || '';
        if(productPriceRevistaField) productPriceRevistaField.value = product.price_revista !== null ? product.price_revista.toString() : '';
        // price_showroom and price_feria are not directly editable in this form, they are derived.
        if(productStockActualField) productStockActualField.value = product.stock_actual !== null ? product.stock_actual.toString() : '';
        if(productStockCriticoField) productStockCriticoField.value = product.stock_critico !== null ? product.stock_critico.toString() : '';

        if(currentImagePreview) {
            currentImagePreview.innerHTML = product.image_url
                ? `<p>Imagen actual:</p><img src="${product.image_url}" alt="Current Image" style="max-width: 100px; max-height: 70px; border-radius: 4px; border: 1px solid #ccc;" />`
                : '<p>No hay imagen actual.</p>';
        }
        // Note: productImageField (type file) cannot be programmatically set for security reasons.
        // User must re-select image if they want to change it.

        openProductModal();
    } catch (error) {
        console.error("Error opening edit modal:", error);
        alert("No se pudieron cargar los datos del producto. " + error.message);
    }
}

// Handle Form Submission (Create/Update)
async function handleFormSubmit(event) {
    event.preventDefault();
    if (!productForm) return;

    const formData = new FormData(productForm);
    const currentProductId = productIdField ? productIdField.value : null;

    let method = 'POST';
    let url = '/api/products/';

    if (currentProductId) {
        method = 'PUT';
        url = `/api/products/${currentProductId}`;
    }

    // If it's a PUT request and the image field is empty,
    // we remove 'image' from formData so backend doesn't try to process an empty file
    // and potentially clear the existing image if that's not the intent.
    // The backend is set up to only update image_url if a new image is provided OR if image_url is explicitly set to null.
    // If user doesn't select a new file for PUT, 'image' field in FormData will be present but its file list empty.
    // The backend's `image: Optional[UploadFile] = File(None)` should handle this.
    // If `productImageField.files.length === 0 && currentProductId` -> this means no new file selected for an update.

    try {
        const response = await fetch(url, {
            method: method,
            body: formData,
            // Headers are not typically needed for FormData, browser sets multipart/form-data
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Error desconocido al guardar el producto.' }));
            throw new Error(errorData.detail || `Error ${response.status} al guardar el producto.`);
        }

        // const result = await response.json(); // Product data returned from backend
        closeProductModal();
        fetchAndDisplayProducts(); // Refresh the product list
    } catch (error) {
        console.error('Error saving product:', error);
        alert(`Error al guardar: ${error.message}`);
    }
}

if (productForm) {
    productForm.addEventListener('submit', handleFormSubmit);
}


// References to new filter elements
const productSearchInput = document.getElementById('product-search');
const productCategoryFilterInput = document.getElementById('product-category-filter');
const productLowStockFilterCheckbox = document.getElementById('product-low-stock-filter');
const applyProductFiltersButton = document.getElementById('apply-product-filters-button'); // Will be used later
const clearProductFiltersButton = document.getElementById('clear-product-filters-button'); // Will be used later

// Fetch and Display Products (Modified for new filters and auth)
async function fetchAndDisplayProducts(filters = {}) {
    if (!productTableBody) {
        console.error("Product table body not found!");
        return;
    }

    const params = new URLSearchParams();
    if (filters.searchTerm) params.append('search_term', filters.searchTerm);
    if (filters.category) params.append('category', filters.category);
    if (filters.lowStock) params.append('low_stock', 'true'); // Send 'true' as a string

    params.append('skip', '0');
    params.append('limit', '100');

    const queryString = params.toString();
    // API_BASE_URL should be defined globally (e.g. in auth.js)
    const apiUrl = `${API_BASE_URL}/api/products/${queryString ? '?' + queryString : ''}`;
    const token = getToken(); // Assuming getToken() is available from auth.js

    if (!token) {
        console.warn("No token found. User might not be logged in. Attempting to redirect to login.");
        if (typeof logout === 'function') logout();
        else window.location.href = 'login.html'; // Fallback if logout function not available
        return;
    }

    try {
        const response = await fetch(apiUrl, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401 || response.status === 403) {
            console.error("Authorization error fetching products. Logging out.");
            if (typeof logout === 'function') logout();
            else window.location.href = 'login.html';
            return;
        }
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `HTTP error! status: ${response.status}` }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        const products = await response.json();
        productTableBody.innerHTML = '';

        if (products.length === 0) {
            productTableBody.innerHTML = '<tr><td colspan="10">No se encontraron productos con los filtros aplicados.</td></tr>';
            return;
        }

        products.forEach(product => {
            const row = productTableBody.insertRow();

            if (product.stock_actual <= product.stock_critico && product.stock_critico > 0) {
                row.classList.add('stock-alert-critical');
            }

            const imageCell = row.insertCell();
            const img = document.createElement('img');
            // Prepend API_BASE_URL if image_url is a relative path from backend root
            img.src = product.image_url ? (product.image_url.startsWith('http') ? product.image_url : `${API_BASE_URL}${product.image_url}`) : 'https://via.placeholder.com/60x60.png?text=No+Image';
            img.alt = product.name;
            img.classList.add('product-image-thumbnail');
            imageCell.appendChild(img);

            row.insertCell().textContent = product.name;
            row.insertCell().textContent = product.category || '-';
            row.insertCell().textContent = product.price_revista.toFixed(2);
            row.insertCell().textContent = (product.price_showroom !== null ? product.price_showroom.toFixed(2) : '-');
            row.insertCell().textContent = (product.price_feria !== null ? product.price_feria.toFixed(2) : '-');
            row.insertCell().textContent = product.stock_actual;
            row.insertCell().textContent = product.stock_critico || '-';

            const wishlistCell = row.insertCell();
            if (typeof renderWishlistButton === 'function') {
                renderWishlistButton(product.id, wishlistCell);
            } else {
                wishlistCell.textContent = 'N/A';
            }

            const actionsCell = row.insertCell();
            const editButton = document.createElement('button');
            editButton.classList.add('edit-product-button', 'mdc-button', 'mdc-button--outlined', 'mdc-button--dense');
            editButton.innerHTML = '<span class="mdc-button__ripple"></span><span class="mdc-button__label">Editar</span>';
            editButton.dataset.id = product.id;
            editButton.addEventListener('click', () => openModalForEdit(product.id));
            actionsCell.appendChild(editButton);

            const deleteButton = document.createElement('button');
            deleteButton.classList.add('delete-product-button', 'mdc-button', 'mdc-button--outlined', 'mdc-button--dense', 'mdc-button--danger');
            deleteButton.innerHTML = '<span class="mdc-button__ripple"></span><span class="mdc-button__label">Eliminar</span>';
            deleteButton.dataset.id = product.id;
            deleteButton.addEventListener('click', () => handleDeleteProduct(product.id, product.name));
            actionsCell.appendChild(deleteButton);

            const addToCartBtnAdmin = document.createElement('button');
            addToCartBtnAdmin.classList.add('admin-add-to-cart-button', 'mdc-button', 'mdc-button--raised', 'mdc-button--dense');
            addToCartBtnAdmin.innerHTML = '<span class="mdc-button__ripple"></span><span class="mdc-button__icon" aria-hidden="true"><i class="fas fa-cart-plus"></i></span> <span class="mdc-button__label">Al Carrito</span>';
            addToCartBtnAdmin.dataset.productId = product.id;
            addToCartBtnAdmin.dataset.productName = product.name;
            addToCartBtnAdmin.dataset.productPrice = product.price_revista;
            addToCartBtnAdmin.dataset.productImageUrl = product.image_url || '';
            addToCartBtnAdmin.addEventListener('click', handleAddToCartClick);
            actionsCell.appendChild(addToCartBtnAdmin);
        });

    } catch (error) {
        console.error("Error fetching products:", error);
        if (productTableBody) {
            productTableBody.innerHTML = `<tr><td colspan="10">Error al cargar productos: ${error.message}. Ver consola para más detalles.</td></tr>`;
        }
    }
}

// Add this function in products.js
async function handleAddToCartClick(event) {
    const button = event.currentTarget;
    const productId = parseInt(button.dataset.productId);
    const productName = button.dataset.productName || "Producto";
    const productPrice = parseFloat(button.dataset.productPrice);
    const productImageUrl = button.dataset.productImageUrl;

    if (typeof isLoggedIn !== 'function' || !isLoggedIn()) {
        if (typeof addGuestCartItem === 'function') {
            const productDetails = {
                id: productId,
                name: productName,
                price_revista: productPrice,
                image_url: productImageUrl
            };
            addGuestCartItem(productDetails, 1);
            alert(`"${productName}" añadido al carrito (invitado)!`);
            if (typeof updateCartIndicator === 'function') updateCartIndicator();
        } else {
            alert("Error: Funcionalidad de carrito de invitado no disponible. Por favor, inicia sesión.");
            window.location.href = 'login.html';
        }
        return;
    }

    // Logged-in user logic
    const token = getToken();
    try {
        const response = await fetch(`${API_BASE_URL}/api/me/cart/items/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ product_id: productId, quantity: 1 })
        });

        if (response.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }

        const responseData = await response.json();
        if (!response.ok) {
            throw new Error(responseData.detail || 'Error al añadir el producto al carrito.');
        }

        alert(`"${productName}" añadido al carrito!`);
        if (typeof updateCartIndicator === 'function') {
            updateCartIndicator();
        }
    } catch (error) {
        console.error('Error adding to cart (logged in):', error);
        alert(error.message);
    }
}


// Event Listeners for New Filters
if (applyProductFiltersButton) {
    applyProductFiltersButton.addEventListener('click', () => {
        const filters = {
            searchTerm: productSearchInput.value.trim(),
            category: productCategoryFilterInput.value.trim(),
            lowStock: productLowStockFilterCheckbox.checked
        };
        fetchAndDisplayProducts(filters);
    });
}

if (clearProductFiltersButton) {
    clearProductFiltersButton.addEventListener('click', () => {
        if(productSearchInput) productSearchInput.value = '';
        if(productCategoryFilterInput) productCategoryFilterInput.value = '';
        if(productLowStockFilterCheckbox) productLowStockFilterCheckbox.checked = false;
        fetchAndDisplayProducts(); // Call with no filters to reset
    });
}


// Handle Delete Product (Ensure Authorization if backend requires it for DELETE)
async function handleDeleteProduct(productId, productName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar el producto "${productName}"?`)) {
        return;
    }
    const token = getToken(); // Get token for authenticated request
    if (!token) {
        alert("No estás autenticado. Por favor, inicia sesión.");
        if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/products/${productId}`, { // Use API_BASE_URL
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.status === 401 || response.status === 403) {
            alert("No autorizado para eliminar este producto. Serás deslogueado.");
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Error desconocido al eliminar el producto.' }));
            throw new Error(errorData.detail || `Error ${response.status} al eliminar el producto.`);
        }

        alert(`Producto "${productName}" eliminado con éxito.`);
        fetchAndDisplayProducts(); // Refresh the product list

    } catch (error) {
        console.error('Error deleting product:', error);
        alert(`Error al eliminar: ${error.message}`);
    }
}


// Load products when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log("products.js DOMContentLoaded. Checking auth state.");
    // Page protection: Ensure user is logged in AND is admin to view this page.
    // This is a basic check. Robust protection should be on the backend.
    if (typeof isLoggedIn === 'function' && isLoggedIn()) {
        // Assuming an isAdmin function or similar check is available from auth.js
        // For now, if logged in, try to fetch. Backend will enforce admin role.
        console.log("User is logged in. Fetching products.");
        fetchAndDisplayProducts(); // Initial fetch with no filters
    } else {
        console.log("User not logged in or auth functions not available. Redirecting to login.");
        // Redirect to login if not authenticated
        // Ensure auth.js is loaded and has already checked token validity by this point.
        // If direct navigation to products.html, auth.js might not have finished.
        // Better to rely on auth.js to redirect if needed, or have a global auth check.
        // For now, if fetch fails due to 401/403, it will handle logout/redirect.
        // If getToken() is null, fetchAndDisplayProducts will redirect.
         fetchAndDisplayProducts(); // Attempt fetch; it will handle token absence.
    }
});
