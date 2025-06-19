// API_BASE_URL, getToken, logout, isLoggedIn are assumed from auth.js

document.addEventListener('DOMContentLoaded', () => {
    // Page protection is handled by inline script in HTML
    // updateAuthUI() is called by auth.js's own DOMContentLoaded.

    const wishlistItemsContainer = document.getElementById('wishlist-items-container');
    const emptyWishlistMessage = document.getElementById('empty-wishlist-message');

    function renderWishlistItem(wishlistItem) {
        const product = wishlistItem.product; // ProductRead object
        if (!product) {
            console.error("Wishlist item missing product data:", wishlistItem);
            return null;
        }

        const itemCard = document.createElement('div');
        itemCard.classList.add('product-card', 'wishlist-item-card');
        itemCard.dataset.productId = product.id;

        // Use textContent for safety where appropriate, or ensure data is sanitized if using innerHTML broadly.
        // For simple display like this, template literal into innerHTML is common.
        itemCard.innerHTML = `
            <img src="${product.image_url || 'images/avatar_placeholder.png'}" alt="${product.name}" class="product-image">
            <div class="product-info">
                <h3 class="product-name">${product.name || 'Nombre no disponible'}</h3>
                <p class="product-price">S/. ${(product.price_revista || 0).toFixed(2)}</p>
            </div>
            <div class="product-actions">
                <button class="remove-from-wishlist-button mdc-button--outlined" data-product-id="${product.id}">
                    <i class="fas fa-trash-alt"></i> Eliminar
                </button>
                <button class="add-to-cart-button-wishlist mdc-button--raised" data-product-id="${product.id}" disabled title="Funcionalidad no implementada">
                    <i class="fas fa-shopping-cart"></i> Añadir al Carrito
                </button>
            </div>
        `;
        return itemCard;
    }

    async function handleRemoveFromWishlist(productId) {
        if (!confirm('¿Estás seguro de que deseas eliminar este producto de tu lista de deseos?')) return;

        const token = getToken();
        if (!token) {
            alert("Debes iniciar sesión para modificar tu lista de deseos.");
            logout(); // Ensure clean state
            window.location.href = 'login.html';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/me/wishlist/${productId}/`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                logout();
                window.location.href = 'login.html';
                return;
            }

            if (response.status === 204) { // Successfully deleted
                alert('Producto eliminado de tu lista de deseos.');
                const itemCardToRemove = wishlistItemsContainer.querySelector(`.wishlist-item-card[data-product-id="${productId}"]`);
                if (itemCardToRemove) {
                    itemCardToRemove.remove();
                }
                if (wishlistItemsContainer.children.length === 0) {
                    if (emptyWishlistMessage) emptyWishlistMessage.style.display = 'block';
                }
            } else { // Other errors (e.g., 404 if already removed, or 500)
                const errorData = await response.json().catch(() => ({ detail: 'Error desconocido.' }));
                throw new Error(errorData.detail || 'Error al eliminar el producto de la wishlist.');
            }
        } catch (error) {
            console.error('Error removing from wishlist:', error);
            alert(error.message);
        }
    }

    async function loadWishlistItems() {
        const token = getToken();
        if (!token) {
            // This should be caught by page protection earlier, but as a safeguard
            return;
        }

        if (!wishlistItemsContainer || !emptyWishlistMessage) {
            console.error("Wishlist container or empty message element not found.");
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/me/wishlist/`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) {
                logout();
                window.location.href = 'login.html';
                return;
            }
            if (!response.ok) {
                const errData = await response.json().catch(() => ({detail: 'Error al cargar la lista de deseos.'}));
                throw new Error(errData.detail || 'Error al cargar la lista de deseos.');
            }

            const wishlistItems = await response.json(); // List[WishlistItemRead]

            wishlistItemsContainer.innerHTML = ''; // Clear previous items
            if (wishlistItems.length === 0) {
                emptyWishlistMessage.style.display = 'block';
            } else {
                emptyWishlistMessage.style.display = 'none';
                wishlistItems.forEach(item => {
                    const itemCard = renderWishlistItem(item);
                    if (itemCard) {
                        wishlistItemsContainer.appendChild(itemCard);
                    }
                });
            }
        } catch (error) {
            console.error('Error loading wishlist items:', error);
            emptyWishlistMessage.textContent = `Error al cargar tu lista de deseos: ${error.message}`;
            emptyWishlistMessage.style.display = 'block';
            emptyWishlistMessage.style.color = 'var(--error-color)'; // Use error color
        }
    }

    // Initial load
    if (isLoggedIn()) { // Ensure user is logged in before attempting to load
        loadWishlistItems();
    }

    // Event delegation for remove buttons
    if (wishlistItemsContainer) {
        wishlistItemsContainer.addEventListener('click', (event) => {
            const removeButton = event.target.closest('.remove-from-wishlist-button');
            if (removeButton) {
                const productId = removeButton.dataset.productId;
                if (productId) {
                    handleRemoveFromWishlist(productId);
                }
            }

            const addToCartButton = event.target.closest('.add-to-cart-button-wishlist');
            if (addToCartButton) {
                const productId = addToCartButton.dataset.productId;
                console.log(`Add to cart button clicked for product ID: ${productId} (functionality pending)`);
                alert("Funcionalidad 'Añadir al Carrito' aún no implementada.");
            }
        });
    }
});
