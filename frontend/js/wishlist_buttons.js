// frontend/js/wishlist_buttons.js

// Assumes API_BASE_URL, getToken, logout, isLoggedIn are global from auth.js
// Assumes FontAwesome icons are available for heart icons via CSS.

async function renderWishlistButton(productId, containerElement) {
    if (!isLoggedIn()) {
        containerElement.innerHTML = '-';
        return;
    }

    const token = getToken();
    if (!token) { // Should be caught by isLoggedIn, but double check
        containerElement.innerHTML = '-';
        return;
    }

    let isInWishlist = false;

    // Check initial status
    try {
        const checkResponse = await fetch(`${API_BASE_URL}/api/me/wishlist/check/${productId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (checkResponse.ok) {
            const checkData = await checkResponse.json();
            isInWishlist = checkData.in_wishlist;
        } else if (checkResponse.status === 401) {
            // Potentially logout and redirect if token is invalid for this check
            // For now, just log it and button will appear as 'not in wishlist'.
            console.warn(`Auth error checking wishlist status for product ${productId}.`);
            // logout(); window.location.href = 'login.html'; return; // More aggressive
        } else {
            console.warn(`Could not check wishlist status for product ${productId} (status: ${checkResponse.status}).`);
        }
    } catch (error) {
        console.warn(`Exception checking wishlist status for product ${productId}:`, error);
    }

    const button = document.createElement('button');
    button.classList.add('wishlist-toggle-button');
    button.dataset.productId = productId;
    button.innerHTML = `<i class="fas fa-heart"></i>`; // Default empty heart (styled by CSS)

    if (isInWishlist) {
        button.classList.add('in-wishlist');
    }

    button.addEventListener('click', handleWishlistButtonClick);
    containerElement.innerHTML = '';
    containerElement.appendChild(button);
}

async function handleWishlistButtonClick(event) {
    const button = event.currentTarget;
    const productId = button.dataset.productId;
    const token = getToken();

    if (!token) {
        alert('Por favor, inicia sesión para añadir a tu wishlist.');
        // Optionally redirect to login or do nothing
        return;
    }

    const isInWishlist = button.classList.contains('in-wishlist');
    const method = isInWishlist ? 'DELETE' : 'POST';
    let url = `${API_BASE_URL}/api/me/wishlist/`;
    let body = null;
    let headers = {
        'Authorization': `Bearer ${token}`
    };

    if (method === 'POST') {
        // URL is already correct for POST
        body = JSON.stringify({ product_id: parseInt(productId) });
        headers['Content-Type'] = 'application/json';
    } else { // DELETE
        url = `${API_BASE_URL}/api/me/wishlist/${productId}/`;
    }

    try {
        const response = await fetch(url, {
            method: method,
            headers: headers,
            body: body
        });

        if (response.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }

        if (!response.ok && response.status !== 204) { // 204 is success for DELETE with no content
            const errorData = await response.json().catch(() => ({})); // Try to parse error
            throw new Error(errorData.detail || `Error al actualizar wishlist (${response.status})`);
        }

        // Toggle button state
        button.classList.toggle('in-wishlist');

        // Optional: update icon if using different classes for filled/empty, e.g., far vs fas for FontAwesome
        // if (button.classList.contains('in-wishlist')) {
        //     button.innerHTML = `<i class="fas fa-heart"></i>`; // Solid heart
        // } else {
        //     button.innerHTML = `<i class="far fa-heart"></i>`; // Regular heart (requires FAR to be loaded)
        // }
        // For now, CSS handles the visual change based on .in-wishlist class on the existing .fas.fa-heart

    } catch (error) {
        console.error('Error handling wishlist button click:', error);
        alert(error.message);
        // Optionally revert button state if API call failed
        // button.classList.toggle('in-wishlist'); // Revert if there was an error after optimistic toggle
    }
}
