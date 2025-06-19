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
                <button class="add-to-cart-button-wishlist mdc-button--raised"
                        data-product-id="${product.id}"
                        data-product-name="${product.name || 'Producto'}"
                        data-product-price="${product.price_revista || 0}"
                        data-product-image-url="${product.image_url || ''}">
                    <i class="fas fa-shopping-cart"></i> Añadir al Carrito
                </button>
            </div>
        `;
        return itemCard;
    }

    async function handleWishlistAddToCartClick(event) { // Changed to be an event handler
        const button = event.currentTarget;
        const productId = parseInt(button.dataset.productId);
        const productName = button.dataset.productName;
        const productPrice = parseFloat(button.dataset.productPrice);
        const productImageUrl = button.dataset.productImageUrl;
        const itemCardElement = button.closest('.wishlist-item-card'); // For potential UI changes

        const productDetails = {
            id: productId,
            name: productName,
            price_revista: productPrice,
            image_url: productImageUrl
        };

        if (!isLoggedIn()) {
            if (typeof addGuestCartItem === 'function') {
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

            if (response.status === 401) { logout(); window.location.href = 'login.html'; return; }

            const responseData = await response.json();
            if (!response.ok) {
                throw new Error(responseData.detail || 'Error al añadir el producto al carrito.');
            }

            alert(`"${productName}" añadido al carrito!`);
            if (typeof updateCartIndicator === 'function') { updateCartIndicator(); }

            if (confirm(`"${productName}" fue añadido al carrito. ¿Deseas eliminarlo de tu lista de deseos?`)) {
                await handleRemoveFromWishlist(productId);
            }
        } catch (error) {
            console.error('Error adding from wishlist to cart (logged in):', error);
            alert(error.message);
        }
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
                    handleRemoveFromWishlist(productId); // Existing function
                }
            }

            const addToCartButton = event.target.closest('.add-to-cart-button-wishlist');
            if (addToCartButton) {
                // Directly pass the event to the handler, or extract details if handler isn't an event handler
                handleWishlistAddToCartClick(event); // Pass event to extract details from button
            }
        });
    }
});
