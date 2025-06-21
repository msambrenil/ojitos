const catalogItemsContainer = document.getElementById('catalog-items-container');
const noCatalogItemsMessage = document.getElementById('no-catalog-items-message');

// Assumed from auth.js: API_BASE_URL, getToken(), logout(), isLoggedIn(), updateCartIndicator
// Assumed from cart_guest.js: addGuestCartItem
// Assumed from wishlist_buttons.js: renderWishlistButton
const PLACEHOLDER_IMAGE_CATALOG = 'images/avatar_placeholder.png'; // Or a more product-oriented placeholder

function renderCatalogProduct(entryData) {
    const product = entryData.product; // This is ProductRead
    if (!product) return null;

    const card = document.createElement('div');
    card.classList.add('product-card', 'catalog-item-card');
    card.dataset.productId = product.id;
    card.dataset.entryId = entryData.id;

    let stockAlertHTML = '';
    let addToCartDisabled = false;

    if (entryData.is_sold_out_in_catalog) {
        card.classList.add('product-sold-out');
        stockAlertHTML = `<p class="stock-alert sold-out-label">AGOTADO (CATÁLOGO)</p>`;
        addToCartDisabled = true;
    } else if (product.stock_actual !== null && product.stock_critico !== null && product.stock_actual <= product.stock_critico && product.stock_critico > 0) {
        card.classList.add('product-low-stock');
        stockAlertHTML = `<p class="stock-alert low-stock-label">¡Pocas unidades!</p>`;
    }

    card.innerHTML = `
        <div class="stock-alerts-container">${stockAlertHTML}</div>
        <img src="${entryData.effective_image_url || PLACEHOLDER_IMAGE_CATALOG}" alt="${product.name}" class="product-image">
        <div class="product-info">
            <h3 class="product-name">${product.name}</h3>
            <p class="product-price">S/. ${entryData.effective_price.toFixed(2)}</p>
            ${entryData.promo_text ? `<p class="promo-text">${entryData.promo_text}</p>` : ''}
            <!-- <p class="product-description-short">${product.description ? product.description.substring(0,50)+'...' : ''}</p> -->
        </div>
        <div class="product-actions catalog-actions">
            <div class="wishlist-button-placeholder"></div>
            <button class="add-to-cart-catalog-button mdc-button--raised"
                    data-product-id="${product.id}"
                    data-product-name="${product.name || 'Producto'}"
                    data-product-price="${entryData.effective_price}"
                    data-product-image-url="${entryData.effective_image_url || ''}"
                    ${addToCartDisabled ? 'disabled' : ''}>
                <i class="fas fa-shopping-cart"></i> Añadir al Carrito
            </button>
        </div>
    `;

    const wishlistButtonContainer = card.querySelector('.wishlist-button-placeholder');
    if (wishlistButtonContainer && typeof renderWishlistButton === 'function') {
        renderWishlistButton(product.id, wishlistButtonContainer);
    } else if (typeof renderWishlistButton !== 'function') {
        console.warn("renderWishlistButton function not found. Ensure wishlist_buttons.js is loaded.");
    }

    if (catalogItemsContainer) { // Check if container exists
        catalogItemsContainer.appendChild(card);
    } else {
        console.error("catalogItemsContainer not found in the DOM.");
    }
}

async function handleCatalogAddToCartClick(event) {
    const button = event.currentTarget;
    const productId = parseInt(button.dataset.productId);
    const productName = button.dataset.productName;
    const productPrice = parseFloat(button.dataset.productPrice);
    const productImageUrl = button.dataset.productImageUrl;

    if (!productId) return;

    const productDetails = {
        id: productId,
        name: productName,
        price_revista: productPrice, // cart_guest.js expects price_revista for guest cart.
                                     // For catalog, effective_price is the actual price to be used.
        image_url: productImageUrl
    };

    if (!isLoggedIn()) { // From auth.js
        if (typeof addGuestCartItem === 'function') { // From cart_guest.js
            addGuestCartItem(productDetails, 1); // productDetails (using effective_price as price_revista), quantity
            alert(`"${productName}" añadido al carrito (invitado)!`);
        } else {
            console.warn("addGuestCartItem function not found. Ensure cart_guest.js is loaded.");
            alert("Error: Funcionalidad de carrito para invitados no disponible.");
        }
    } else { // Logged in
        const token = getToken(); // From auth.js
        try {
            const response = await fetch(`${API_BASE_URL}/api/me/cart/items/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ product_id: productId, quantity: 1 })
            });
            if (response.status === 401) { logout(); window.location.href = 'login.html'; return; } // From auth.js
            const responseData = await response.json();
            if (!response.ok) { throw new Error(responseData.detail || 'Error al añadir producto al carrito.'); }
            alert(`"${productName}" añadido al carrito!`);
        } catch (error) {
            console.error('Error adding to cart (logged in):', error);
            alert(error.message);
        }
    }
    if (typeof updateCartIndicator === 'function') { updateCartIndicator(); } // From auth.js
}

async function loadCatalogProducts() {
    if (!catalogItemsContainer) {
        console.log("Catalog items container not found on this page. Skipping catalog load.");
        if (noCatalogItemsMessage) noCatalogItemsMessage.style.display = 'none'; // Hide if no container
        return;
    }
    try {
        const response = await fetch(`${API_BASE_URL}/api/catalog/entries/?limit=50`); // Public endpoint
        if (!response.ok) {
            const errText = await response.text();
            let errDetail = 'No se pudo cargar el catálogo.';
            try {
                const errJson = JSON.parse(errText);
                errDetail = errJson?.detail || errDetail;
            } catch (e) { /* Use errText or default */ errDetail = response.statusText || errDetail; }
            throw new Error(errDetail);
        }
        const entries = await response.json();

        catalogItemsContainer.innerHTML = '';
        if (entries.length === 0) {
            if (noCatalogItemsMessage) noCatalogItemsMessage.style.display = 'block';
        } else {
            if (noCatalogItemsMessage) noCatalogItemsMessage.style.display = 'none';
            entries.forEach(entry => renderCatalogProduct(entry));
        }
    } catch (error) {
        console.error("Error loading catalog products:", error);
        if (catalogItemsContainer) catalogItemsContainer.innerHTML = `<p class="error-message" style="text-align:center; padding: 20px;">${error.message}</p>`;
        if (noCatalogItemsMessage) noCatalogItemsMessage.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // auth.js handles its own UI updates on DOMContentLoaded
    loadCatalogProducts();

    if (catalogItemsContainer) { // Ensure container exists before adding listener
        catalogItemsContainer.addEventListener('click', (event) => {
            const addToCartButton = event.target.closest('.add-to-cart-catalog-button');
            if (addToCartButton && !addToCartButton.disabled) {
                handleCatalogAddToCartClick({ currentTarget: addToCartButton });
            }
        });
    } else {
        console.warn("Catalog items container not found, Add to Cart delegation not set up.");
    }
});
