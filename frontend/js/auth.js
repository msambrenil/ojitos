const API_BASE_URL = ''; // Assuming API is served from the same origin, or set appropriately
const USER_INFO_KEY = 'currentUserInfo';

function getCurrentUserInfo() {
    try {
        const userInfoJson = localStorage.getItem(USER_INFO_KEY);
        return userInfoJson ? JSON.parse(userInfoJson) : null;
    } catch (error) {
        console.error("Error parsing current user info from localStorage:", error);
        localStorage.removeItem(USER_INFO_KEY); // Clear corrupted data
        return null;
    }
}

async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'username': email, // Backend /token endpoint expects 'username' for email
                'password': password
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Error desconocido durante el login.' }));
            console.error('Login failed:', errorData.detail);
            throw new Error(errorData.detail || 'Error al iniciar sesión.');
        }

        const data = await response.json(); // Expects { access_token: "...", token_type: "bearer" }
        if (data.access_token) {
            // Cart Merge Logic
            if (typeof getGuestCart === 'function' && typeof clearGuestCart === 'function' && typeof mergeCarts === 'function') {
                const guestCartItems = getGuestCart(); // From cart_guest.js
                if (guestCartItems && guestCartItems.length > 0) {
                    console.log("Guest cart found, attempting merge with backend...");
                    const mergeSuccessful = await mergeCarts(guestCartItems, data.access_token); // mergeCarts is in auth.js
                    if (mergeSuccessful) {
                        console.log("Guest cart merged (or attempted) with backend cart.");
                    } else {
                        console.warn("Guest cart merge encountered issues or was aborted due to auth error. Some items might not have been merged.");
                        // If merge failed due to auth, logout() would have been called in mergeCarts,
                        // and this part of login() might not even be reached if redirection occurs.
                        // If it returns false for other reasons, token is still set below.
                    }
                    // Clear local guest cart AFTER attempting merge, regardless of partial success,
                    // to prevent re-merging or leaving items locally if user intended them to be merged.
                    // If merge was aborted by logout in mergeCarts, this clear might not run if redirection happens first.
                    clearGuestCart(); // From cart_guest.js
                    console.log("Local guest cart cleared after merge attempt.");
                } else {
                    console.log("No guest cart items to merge.");
                }
            } else {
                console.warn("Guest cart functions (getGuestCart, clearGuestCart) or mergeCarts not available. Skipping cart merge.");
            }
            // End of Cart Merge Logic

            // Fetch user details to get is_superuser flag
            try {
                const profileResponse = await fetch(`${API_BASE_URL}/api/me/profile/`, {
                    headers: { 'Authorization': `Bearer ${data.access_token}` }
                });
                if (profileResponse.ok) {
                    const userProfileData = await profileResponse.json();
                    const userInfoToStore = {
                        email: userProfileData.email,
                        fullName: userProfileData.full_name,
                        isSuperuser: userProfileData.is_superuser
                    };
                    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfoToStore));
                    console.log("User info (including role) stored in localStorage.");
                } else {
                    console.warn("Could not fetch user profile after login to determine role.");
                    localStorage.removeItem(USER_INFO_KEY);
                }
            } catch (error) {
                console.error("Error fetching user profile after login:", error);
                localStorage.removeItem(USER_INFO_KEY);
            }

            localStorage.setItem('accessToken', data.access_token);
            console.log('Login successful, token stored.');
            updateAuthUI();
            window.location.href = 'my_profile.html';
            return true;
        } else {
            throw new Error('Token no recibido del servidor.');
        }
    } catch (error) {
        console.error('Error in login function:', error);
        return false;
    }
}

function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem(USER_INFO_KEY); // Remove user info on logout
    console.log('Logged out, token and user info removed.');
    updateAuthUI();
}

function getToken() {
    return localStorage.getItem('accessToken');
}

function isLoggedIn() {
    const token = getToken();
    return !!token;
}

async function mergeCarts(guestCartItems, token) {
    if (!guestCartItems || guestCartItems.length === 0) {
        console.log("No guest cart items to merge.");
        return true; // Nothing to do, considered success for the merge operation
    }

    console.log("Starting cart merge process for items:", guestCartItems);
    let allMergedSuccessfully = true;

    for (const item of guestCartItems) {
        if (item.productId === undefined || item.quantity === undefined) { // Check for undefined specifically
            console.warn("Skipping invalid guest cart item (missing productId or quantity):", item);
            continue;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/me/cart/items/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    product_id: item.productId, // Ensure this matches CartItemCreate schema
                    quantity: item.quantity
                })
            });

            if (response.status === 401) {
                console.error("Authentication error during cart merge. This should not happen if token was just obtained. Logging out.");
                logout(); // This will also update UI and redirect
                allMergedSuccessfully = false;
                return false; // Stop merge process immediately
            }

            if (!response.ok) {
                // Try to get error detail, but don't let it crash if parsing fails
                let errorDetail = `HTTP status ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (e) { /* ignore parsing error, use status text */ }

                console.error(`Failed to merge item (ID: ${item.productId}): ${errorDetail}`);
                allMergedSuccessfully = false; // Mark as not entirely successful but continue with other items
            } else {
                console.log(`Successfully merged item (ID: ${item.productId}), quantity: ${item.quantity}`);
            }
        } catch (error) {
            console.error(`Network or other error merging item (ID: ${item.productId}):`, error);
            allMergedSuccessfully = false;
        }
    }

    if (allMergedSuccessfully) {
        console.log("Cart merge completed successfully.");
    } else {
        console.warn("Cart merge completed with some errors. Check console for details.");
    }
    return allMergedSuccessfully;
}

function updateAuthUI() {
    const loginLink = document.getElementById('nav-login-link');
    const profileLink = document.getElementById('nav-profile-link');
    const logoutButton = document.getElementById('nav-logout-button');
    const userGreeting = document.getElementById('user-greeting');
    const adminClientsLink = document.getElementById('nav-admin-clients-link');
    const adminConfigLink = document.getElementById('nav-admin-config-link');
    const adminTagsLink = document.getElementById('nav-admin-tags-link');
    const adminCategoriesLink = document.getElementById('nav-admin-categories-link');
    const adminCatalogLink = document.getElementById('nav-admin-catalog-link');
    const navProductsLink = document.getElementById('nav-products-link'); // For "Gestión de Productos"
    const wishlistLink = document.getElementById('nav-wishlist-link');
    const navCartLink = document.getElementById('nav-cart-link');

    const currentUserInfo = getCurrentUserInfo(); // Get stored user info

    if (isLoggedIn()) {
        if (loginLink) loginLink.style.display = 'none';
        if (profileLink) profileLink.style.display = 'inline';
        if (wishlistLink) wishlistLink.style.display = 'inline';
        if (navCartLink) navCartLink.style.display = 'inline';
        if (logoutButton) logoutButton.style.display = 'inline-block';

        if (currentUserInfo && userGreeting) {
            userGreeting.textContent = `Hola, ${currentUserInfo.fullName || currentUserInfo.email}!`;
            userGreeting.style.display = 'inline';
        } else if (userGreeting) { // Fallback if no info, but should be rare if login fetches it
            userGreeting.textContent = 'Hola!';
            userGreeting.style.display = 'inline';
        }

        if (currentUserInfo && currentUserInfo.isSuperuser) {
            if (adminClientsLink) adminClientsLink.style.display = 'inline';
            if (adminConfigLink) adminConfigLink.style.display = 'inline';
            if (adminTagsLink) adminTagsLink.style.display = 'inline';
            if (adminCategoriesLink) adminCategoriesLink.style.display = 'inline';
            if (adminCatalogLink) adminCatalogLink.style.display = 'inline';
            if (navProductsLink) navProductsLink.style.display = 'inline'; // Show "Gestión de Productos" for admin
        } else {
            // Not a superuser, or user info not available
            if (adminClientsLink) adminClientsLink.style.display = 'none';
            if (adminConfigLink) adminConfigLink.style.display = 'none';
            if (adminTagsLink) adminTagsLink.style.display = 'none';
            if (adminCategoriesLink) adminCategoriesLink.style.display = 'none';
            if (adminCatalogLink) adminCatalogLink.style.display = 'none';
            if (navProductsLink) navProductsLink.style.display = 'none'; // Hide "Gestión de Productos"
        }

    } else { // Not logged in
        if (loginLink) loginLink.style.display = 'inline';
        if (profileLink) profileLink.style.display = 'none';
        if (wishlistLink) wishlistLink.style.display = 'none';
        if (navCartLink) navCartLink.style.display = 'none';
        if (logoutButton) logoutButton.style.display = 'none';
        if (userGreeting) {
            userGreeting.style.display = 'none';
            userGreeting.textContent = '';
        }
        // Hide all admin links if not logged in
        if (adminClientsLink) adminClientsLink.style.display = 'none';
        if (adminConfigLink) adminConfigLink.style.display = 'none';
        if (adminTagsLink) adminTagsLink.style.display = 'none';
        if (adminCategoriesLink) adminCategoriesLink.style.display = 'none';
        if (adminCatalogLink) adminCatalogLink.style.display = 'none';
        if (navProductsLink) navProductsLink.style.display = 'none'; // Hide "Gestión de Productos"
    }
    updateCartIndicator();
}

async function updateCartIndicator() {
    const navCartLink = document.getElementById('nav-cart-link');
    const cartItemCountSpan = document.getElementById('cart-item-count');

    if (!navCartLink || !cartItemCountSpan) {
        return; // Elements not present on this page (e.g. if some pages have different headers)
    }

    if (isLoggedIn()) {
        const token = getToken();
        try {
            const response = await fetch(`${API_BASE_URL}/api/me/cart/`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const cart = await response.json(); // CartRead
                let totalQuantity = 0;
                if (cart && cart.items) {
                    cart.items.forEach(item => {
                        totalQuantity += item.quantity;
                    });
                }
                cartItemCountSpan.textContent = totalQuantity;
                navCartLink.style.display = 'inline'; // Ensure link is visible
            } else if (response.status === 401) {
                logout(); // This will call updateAuthUI which calls updateCartIndicator again
                          // The second call will hit the 'else' block below.
            } else {
                console.warn('Could not fetch cart for indicator:', response.status);
                navCartLink.style.display = 'inline'; // Still show link
                cartItemCountSpan.textContent = '0'; // Or '!' for error
            }
        } catch (error) {
            console.error('Error updating cart indicator:', error);
            navCartLink.style.display = 'inline'; // Still show link
            cartItemCountSpan.textContent = '0'; // Or '!' for error
        }
    } else { // Not logged in - GUEST CART LOGIC
        if (typeof getGuestCart === 'function') { // from cart_guest.js
            const guestCartItems = getGuestCart();
            let totalQuantity = 0;
            if (guestCartItems && guestCartItems.length > 0) {
                guestCartItems.forEach(item => {
                    totalQuantity += item.quantity;
                });
            }

            if (cartItemCountSpan) cartItemCountSpan.textContent = totalQuantity;

            // Show cart link for guests only if cart is not empty.
            if (navCartLink) {
                navCartLink.style.display = totalQuantity > 0 ? 'inline' : 'none';
            }
        } else {
            // Fallback if cart_guest.js or getGuestCart isn't loaded/available
            if (cartItemCountSpan) cartItemCountSpan.textContent = '0';
            if (navCartLink) navCartLink.style.display = 'none';
            // console.warn("getGuestCart function not found for guest cart indicator. Ensure cart_guest.js is loaded before auth.js.");
            // Warning removed as per plan to adjust script order in HTML next.
        }
    }
}


document.addEventListener('DOMContentLoaded', () => {
    updateAuthUI(); // This will now also trigger updateCartIndicator

    const logoutButtonElement = document.getElementById('nav-logout-button'); // Renamed to avoid conflict
    if (logoutButtonElement) {
        logoutButtonElement.addEventListener('click', () => {
            logout();
            // updateAuthUI(); // Called by logout()
            window.location.href = 'login.html';
        });
    }
});
