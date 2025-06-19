const API_BASE_URL = ''; // Assuming API is served from the same origin, or set appropriately

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
            localStorage.setItem('accessToken', data.access_token);
            console.log('Login successful, token stored.');
            updateAuthUI(); // Update UI first
            window.location.href = 'my_profile.html'; // Then redirect (or to dashboard: index.html)
            return true;
        } else {
            throw new Error('Token no recibido del servidor.');
        }
    } catch (error) {
        console.error('Error in login function:', error);
        // alert(error.message); // Handled by login form typically
        return false; // Indicate failure
    }
}

function logout() {
    localStorage.removeItem('accessToken');
    console.log('Logged out, token removed.');
    updateAuthUI(); // Update UI after removing token
    // Redirection is handled by the event listener in DOMContentLoaded for the logout button,
    // or should be handled by the calling code if logout() is invoked programmatically elsewhere.
}

function getToken() {
    return localStorage.getItem('accessToken');
}

function isLoggedIn() {
    const token = getToken();
    return !!token;
}

function updateAuthUI() {
    const loginLink = document.getElementById('nav-login-link');
    const profileLink = document.getElementById('nav-profile-link');
    const logoutButton = document.getElementById('nav-logout-button');
    const userGreeting = document.getElementById('user-greeting');
    const adminClientsLink = document.getElementById('nav-admin-clients-link');
    const wishlistLink = document.getElementById('nav-wishlist-link'); // Added wishlist link

    if (isLoggedIn()) {
        if (loginLink) loginLink.style.display = 'none';
        if (profileLink) profileLink.style.display = 'inline';
        if (wishlistLink) wishlistLink.style.display = 'inline'; // Show wishlist link
        if (logoutButton) logoutButton.style.display = 'inline-block';
        if (userGreeting) {
            userGreeting.style.display = 'inline';
            // TODO: Fetch actual user data to display name/email.
            // For now, a generic greeting or leave it empty until data is fetched.
            // Example: userGreeting.textContent = 'Bienvenido!';
            // Placeholder, real data fetch needed for user's name/email
        }
        // Future: Add logic for adminClientsLink visibility based on user role
        // if (adminClientsLink && userHasAdminRole()) { // userHasAdminRole() would check token claims or user data
        //     adminClientsLink.style.display = 'inline';
        // } else if (adminClientsLink) {
        //     adminClientsLink.style.display = 'none';
        // }

    } else {
        if (loginLink) loginLink.style.display = 'inline';
        if (profileLink) profileLink.style.display = 'none';
        if (wishlistLink) wishlistLink.style.display = 'none'; // Hide wishlist link
        if (logoutButton) logoutButton.style.display = 'none';
        if (userGreeting) {
            userGreeting.style.display = 'none';
            userGreeting.textContent = ''; // Clear greeting
        }
        // Future: Hide adminClientsLink if not logged in
        // if (adminClientsLink) adminClientsLink.style.display = 'none';
        // (Note: adminClientsLink visibility is not managed by login state here, but by role later)
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateAuthUI(); // Call on every page load to set initial UI state

    const logoutButton = document.getElementById('nav-logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            logout(); // Call the logout function from auth.js
            // updateAuthUI(); // Called inside logout() already
            window.location.href = 'login.html'; // Redirect after logout
        });
    }
});
