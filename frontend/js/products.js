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


const filterNameInput = document.getElementById('filter-name');
const filterCategoryInput = document.getElementById('filter-category');
const applyFiltersButton = document.getElementById('apply-filters-button');
const clearFiltersButton = document.getElementById('clear-filters-button');

// Fetch and Display Products (Modified to add Edit button listener and filters)
async function fetchAndDisplayProducts(filters = {}) {
    if (!productTableBody) {
        console.error("Product table body not found!");
        return;
    }

    const params = new URLSearchParams();
    if (filters.name) params.append('name', filters.name); // Backend needs to support 'name'
    if (filters.category) params.append('category', filters.category);
    // params.append('skip', '0'); // Reset pagination on filter, or manage it more complexly
    // params.append('limit', '100'); // Or your default limit
    // For now, backend default pagination (if any) will apply or it returns all.
    // The existing backend GET /api/products/ has skip/limit but not name filter yet.

    const queryString = params.toString();
    const apiUrl = `/api/products/${queryString ? '?' + queryString : ''}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const products = await response.json();

        productTableBody.innerHTML = '';

        products.forEach(product => {
            const row = productTableBody.insertRow();

            if (product.stock_actual <= product.stock_critico && product.stock_critico > 0) {
                row.classList.add('stock-alert-critical');
            }

            const imageCell = row.insertCell();
            const img = document.createElement('img');
            img.src = product.image_url ? product.image_url : 'https://via.placeholder.com/60x60.png?text=No+Image';
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

            // Wishlist cell - New
            const wishlistCell = row.insertCell();
            if (typeof renderWishlistButton === 'function') {
                renderWishlistButton(product.id, wishlistCell);
            } else {
                wishlistCell.textContent = 'N/A'; // Fallback if function not loaded
            }

            const actionsCell = row.insertCell();
            const editButton = document.createElement('button');
            editButton.classList.add('edit-product-button');
            editButton.textContent = 'Editar';
            editButton.dataset.id = product.id;
            editButton.addEventListener('click', () => openModalForEdit(product.id));
            actionsCell.appendChild(editButton);

            const deleteButton = document.createElement('button');
            deleteButton.classList.add('delete-product-button');
            deleteButton.textContent = 'Eliminar';
            deleteButton.dataset.id = product.id;
            deleteButton.addEventListener('click', () => handleDeleteProduct(product.id, product.name));
            actionsCell.appendChild(deleteButton);

            // Add to Cart button for admin product table
            const addToCartBtnAdmin = document.createElement('button');
            addToCartBtnAdmin.classList.add('admin-add-to-cart-button', 'mdc-button', 'mdc-button--outlined');
            addToCartBtnAdmin.textContent = 'Al Carrito';
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
            // Adjusted colspan to 10 due to new Wishlist column
            productTableBody.innerHTML = '<tr><td colspan="10">Error al cargar productos. Ver consola para más detalles.</td></tr>';
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


// Event Listeners for Filters
if (applyFiltersButton) {
    applyFiltersButton.addEventListener('click', () => {
        const filters = {
            name: filterNameInput ? filterNameInput.value.trim() : '',
            category: filterCategoryInput ? filterCategoryInput.value.trim() : ''
        };
        fetchAndDisplayProducts(filters);
    });
}

if (clearFiltersButton) {
    clearFiltersButton.addEventListener('click', () => {
        if(filterNameInput) filterNameInput.value = '';
        if(filterCategoryInput) filterCategoryInput.value = '';
        fetchAndDisplayProducts(); // Call with no filters
    });
}


// Handle Delete Product
async function handleDeleteProduct(productId, productName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar el producto "${productName}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/products/${productId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Error desconocido al eliminar el producto.' }));
            throw new Error(errorData.detail || `Error ${response.status} al eliminar el producto.`);
        }

        // const result = await response.json(); // Contains {message: "..."}
        alert(`Producto "${productName}" eliminado con éxito.`);
        fetchAndDisplayProducts(); // Refresh the product list

    } catch (error) {
        console.error('Error deleting product:', error);
        alert(`Error al eliminar: ${error.message}`);
    }
}


// Load products when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log("products.js DOMContentLoaded");
    fetchAndDisplayProducts();
});
