// API_BASE_URL, getToken, logout, isLoggedIn, updateCartIndicator, getGuestCart, updateGuestCartItemQuantity, removeGuestCartItem, clearGuestCart
// are assumed to be globally available from auth.js and cart_guest.js

document.addEventListener('DOMContentLoaded', () => {
    // Page protection was removed from HTML, logic here will display appropriate cart.
    // auth.js handles global auth UI updates including initial cart indicator.

    const cartItemsContainer = document.getElementById('cart-items-container');
    const emptyCartMessage = document.getElementById('empty-cart-message');
    const cartTotalPriceSpan = document.getElementById('cart-total-price');
    const clearCartButton = document.getElementById('clear-cart-button');
    const checkoutButton = document.getElementById('checkout-button');

    function renderCartItem(itemData, isGuest = false) {
        const productId = isGuest ? itemData.productId : itemData.product.id;
        const name = isGuest ? itemData.name : itemData.product.name;
        const unitPrice = isGuest ? (itemData.price || 0) : (itemData.price_at_addition !== null ? itemData.price_at_addition : (itemData.product?.price_revista || 0));
        const imageUrl = isGuest ? itemData.imageUrl : itemData.product?.image_url;
        const quantity = itemData.quantity;

        if (productId === undefined || productId === null) { // More robust check
            console.error("Item data missing product ID:", itemData);
            return null;
        }

        const itemCard = document.createElement('div');
        itemCard.classList.add('cart-item-card');
        itemCard.dataset.productId = productId;
        if (!isGuest && itemData.id) { // Logged-in cart items have their own ID
            itemCard.dataset.itemId = itemData.id;
        }

        const itemSubtotal = unitPrice * quantity;

        itemCard.innerHTML = `
            <img src="${imageUrl || 'images/avatar_placeholder.png'}" alt="${name || 'Producto'}" class="cart-item-image">
            <div class="cart-item-details">
                <h3 class="cart-item-name">${name || 'Producto Desconocido'}</h3>
                <p class="cart-item-price">Precio Unitario: S/. ${unitPrice.toFixed(2)}</p>
                <div class="cart-item-quantity">
                    <label for="qty-${productId}">Cantidad:</label>
                    <input type="number" id="qty-${productId}" class="quantity-input" value="${quantity}" min="1" data-product-id="${productId}">
                </div>
                <p class="cart-item-subtotal">Subtotal: S/. ${itemSubtotal.toFixed(2)}</p>
            </div>
            <div class="cart-item-actions">
                <button class="remove-from-cart-button mdc-button--icon" data-product-id="${productId}" aria-label="Eliminar item">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        `;
        return itemCard;
    }

    // For Logged-in User (API interactions)
    async function updateLoggedInCartItemQuantity(productId, newQuantity) {
        const token = getToken();
        if (!token) { alert("Sesión expirada."); logout(); window.location.href = 'login.html'; return false; }

        try {
            const response = await fetch(`${API_BASE_URL}/api/me/cart/items/${productId}/`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ quantity: newQuantity })
            });
            if (response.status === 401) { logout(); window.location.href = 'login.html'; return false; }
            if (!response.ok) {
                const err = await response.json().catch(() => ({detail: 'Error al actualizar cantidad.'}));
                throw new Error(err.detail);
            }
            await loadCartDetails();
            if (typeof updateCartIndicator === 'function') updateCartIndicator();
            return true;
        } catch (error) { console.error("Update quantity error (logged in):", error); alert(error.message); await loadCartDetails(); return false; }
    }

    async function handleLoggedInRemoveCartItem(productId) {
        if (!confirm('¿Eliminar este producto del carrito?')) return;
        const token = getToken();
        if (!token) { alert("Sesión expirada."); logout(); window.location.href = 'login.html'; return; }
        try {
            const response = await fetch(`${API_BASE_URL}/api/me/cart/items/${productId}/`, {
                method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.status === 401) { logout(); window.location.href = 'login.html'; return; }
            if (!response.ok && response.status !== 204) {
                const err = await response.json().catch(() => ({detail: 'Error al eliminar item.'}));
                throw new Error(err.detail);
            }
            await loadCartDetails();
            if (typeof updateCartIndicator === 'function') updateCartIndicator();
        } catch (error) { console.error("Remove item error (logged in):", error); alert(error.message); await loadCartDetails(); }
    }

    async function handleLoggedInClearCart() {
        if (!confirm('¿Vaciar todo el carrito? Esta acción no se puede deshacer.')) return;
        const token = getToken();
        if (!token) { alert("Sesión expirada."); logout(); window.location.href = 'login.html'; return; }
        try {
            const response = await fetch(`${API_BASE_URL}/api/me/cart/`, {
                method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.status === 401) { logout(); window.location.href = 'login.html'; return; }
            if (!response.ok && response.status !== 204) {
                const err = await response.json().catch(() => ({detail: 'Error al vaciar carrito.'}));
                throw new Error(err.detail);
            }
            await loadCartDetails();
            if (typeof updateCartIndicator === 'function') updateCartIndicator();
        } catch (error) { console.error("Clear cart error (logged in):", error); alert(error.message); await loadCartDetails(); }
    }

    // Main function to load cart details (handles both guest and logged-in)
    async function loadCartDetails() {
        if (!cartItemsContainer || !emptyCartMessage || !cartTotalPriceSpan || !checkoutButton) {
            console.error("One or more critical cart display elements are missing.");
            return;
        }
        cartItemsContainer.innerHTML = '';
        emptyCartMessage.style.display = 'none';
        let calculatedTotal = 0;

        if (isLoggedIn()) {
            const token = getToken();
            if (!token) { // Should not happen if isLoggedIn is true, but as a safeguard
                logout(); window.location.href = 'login.html'; return;
            }
            try {
                const response = await fetch(`${API_BASE_URL}/api/me/cart/`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (response.status === 401) { logout(); window.location.href = 'login.html'; return; }
                if (!response.ok) {
                    const err = await response.json().catch(() => ({detail: 'Error al cargar el carrito.'}));
                    throw new Error(err.detail);
                }
                const cart = await response.json(); // CartRead

                if (cart.items && cart.items.length > 0) {
                    cart.items.forEach(item => {
                        const itemCard = renderCartItem(item, false); // isGuest = false
                        if (itemCard) cartItemsContainer.appendChild(itemCard);
                    });
                } else {
                    emptyCartMessage.style.display = 'block';
                }
                cartTotalPriceSpan.textContent = `S/. ${(cart.total_cart_price || 0).toFixed(2)}`;
                checkoutButton.disabled = !(cart.items && cart.items.length > 0);
                checkoutButton.textContent = 'Continuar Compra';
                checkoutButton.onclick = () => alert('Proceso de checkout no implementado.');
            } catch (error) {
                console.error("Load cart error (logged in):", error);
                cartItemsContainer.innerHTML = `<p class="error-message" style="text-align:center;">${error.message}</p>`;
                emptyCartMessage.style.display = 'none';
                cartTotalPriceSpan.textContent = 'S/. 0.00';
                checkoutButton.disabled = true;
            }
        } else { // Guest user
            if (typeof getGuestCart === 'function') {
                const guestCartItems = getGuestCart();
                if (guestCartItems.length > 0) {
                    guestCartItems.forEach(item => {
                        const itemCard = renderCartItem(item, true); // isGuest = true
                        if (itemCard) cartItemsContainer.appendChild(itemCard);
                        calculatedTotal += (item.price || 0) * item.quantity;
                    });
                } else {
                    emptyCartMessage.style.display = 'block';
                }
                cartTotalPriceSpan.textContent = `S/. ${calculatedTotal.toFixed(2)}`;
                checkoutButton.disabled = !(guestCartItems.length > 0);
                checkoutButton.textContent = 'Iniciar Sesión para Continuar';
                checkoutButton.onclick = () => window.location.href = 'login.html';
            } else {
                console.error("getGuestCart function is not available.");
                emptyCartMessage.textContent = "Error al cargar carrito de invitado (funciones no disponibles).";
                emptyCartMessage.style.display = 'block';
                checkoutButton.disabled = true;
            }
        }
    }

    // Initial load
    loadCartDetails();

    // Event Listeners
    if (cartItemsContainer) {
        cartItemsContainer.addEventListener('change', async (event) => {
            if (event.target.classList.contains('quantity-input')) {
                const productId = parseInt(event.target.dataset.productId);
                const newQuantity = parseInt(event.target.value, 10);

                if (!productId || isNaN(newQuantity)) return; // Basic validation

                if (isLoggedIn()) {
                    if (newQuantity > 0) {
                        await updateLoggedInCartItemQuantity(productId, newQuantity);
                    } else {
                        await handleLoggedInRemoveCartItem(productId);
                    }
                } else { // Guest
                    if (typeof updateGuestCartItemQuantity === 'function') {
                        updateGuestCartItemQuantity(productId, newQuantity); // This handles removal if quantity <= 0
                        await loadCartDetails(); // Refresh guest cart view
                        if (typeof updateCartIndicator === 'function') updateCartIndicator();
                    }
                }
            }
        });

        cartItemsContainer.addEventListener('click', async (event) => {
            const removeButton = event.target.closest('.remove-from-cart-button');
            if (removeButton) {
                const productId = parseInt(removeButton.dataset.productId);
                if (!productId) return;

                if (isLoggedIn()) {
                    await handleLoggedInRemoveCartItem(productId);
                } else { // Guest
                    if (typeof removeGuestCartItem === 'function') {
                        removeGuestCartItem(productId);
                        await loadCartDetails(); // Refresh guest cart view
                        if (typeof updateCartIndicator === 'function') updateCartIndicator();
                    }
                }
            }
        });
    }

    if (clearCartButton) {
        clearCartButton.addEventListener('click', async () => {
            if (isLoggedIn()) {
                await handleLoggedInClearCart();
            } else { // Guest
                if (typeof clearGuestCart === 'function') {
                    clearGuestCart();
                    await loadCartDetails(); // Refresh guest cart view
                    if (typeof updateCartIndicator === 'function') updateCartIndicator();
                }
            }
        });
    }

    // Checkout button behavior is set within loadCartDetails
});
