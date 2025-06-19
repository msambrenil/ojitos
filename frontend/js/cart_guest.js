// frontend/js/cart_guest.js

const GUEST_CART_KEY = 'guestCart';

// Assumes updateCartIndicator() from auth.js is globally available.
// This means auth.js must be loaded before cart_guest.js in HTML.

function getGuestCart() {
    try {
        const cartJson = localStorage.getItem(GUEST_CART_KEY);
        return cartJson ? JSON.parse(cartJson) : [];
    } catch (error) {
        console.error("Error parsing guest cart from localStorage:", error);
        return []; // Return empty array on error
    }
}

function saveGuestCart(cartItems) {
    try {
        localStorage.setItem(GUEST_CART_KEY, JSON.stringify(cartItems));
    } catch (error) {
        console.error("Error saving guest cart to localStorage:", error);
        // Potentially alert user if storage is full or unavailable
    }
}

function addGuestCartItem(productDetails, quantityToAdd = 1) {
    if (!productDetails || productDetails.id === undefined) {
        console.error("Product details (especially ID) are required to add to guest cart.");
        alert("No se pudo añadir el producto al carrito de invitado (faltan detalles).");
        return;
    }
    if (quantityToAdd <= 0) {
        console.warn("Quantity to add must be positive.");
        alert("La cantidad para añadir debe ser positiva.");
        return;
    }

    let cartItems = getGuestCart();
    const existingItemIndex = cartItems.findIndex(item => item.productId === productDetails.id);

    if (existingItemIndex > -1) {
        cartItems[existingItemIndex].quantity += quantityToAdd;
    } else {
        cartItems.push({
            productId: productDetails.id,
            name: productDetails.name || 'Producto Desconocido',
            price: productDetails.price_revista !== undefined ? productDetails.price_revista : 0,
            imageUrl: productDetails.image_url || null,
            quantity: quantityToAdd
        });
    }
    saveGuestCart(cartItems);
    if (typeof updateCartIndicator === 'function') {
        updateCartIndicator();
    }
}

function updateGuestCartItemQuantity(productId, newQuantity) {
    let cartItems = getGuestCart();
    const itemIndex = cartItems.findIndex(item => item.productId === productId);

    if (itemIndex > -1) {
        if (newQuantity > 0) {
            cartItems[itemIndex].quantity = newQuantity;
        } else { // Quantity <= 0, remove item
            cartItems.splice(itemIndex, 1);
        }
        saveGuestCart(cartItems);
        if (typeof updateCartIndicator === 'function') {
            updateCartIndicator();
        }
    } else {
        console.warn(`Product ID ${productId} not found in guest cart for quantity update.`);
    }
}

function removeGuestCartItem(productId) {
    let cartItems = getGuestCart();
    const updatedCartItems = cartItems.filter(item => item.productId !== productId);

    if (updatedCartItems.length < cartItems.length) { // Item was actually removed
        saveGuestCart(updatedCartItems);
        if (typeof updateCartIndicator === 'function') {
            updateCartIndicator();
        }
    } else {
        console.warn(`Product ID ${productId} not found in guest cart for removal.`);
    }
}

function clearGuestCart() {
    localStorage.removeItem(GUEST_CART_KEY);
    if (typeof updateCartIndicator === 'function') {
        updateCartIndicator(); // To reset count to 0
    }
    console.log("Guest cart cleared from localStorage.");
}

// Optional: Export functions if modules are used later
// export { getGuestCart, saveGuestCart, addGuestCartItem, updateGuestCartItemQuantity, removeGuestCartItem, clearGuestCart };
