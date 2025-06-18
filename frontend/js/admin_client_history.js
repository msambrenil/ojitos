// API_BASE_URL and auth functions (getToken, logout) are assumed to be globally available from auth.js

document.addEventListener('DOMContentLoaded', () => {
    // Page protection (isLoggedIn check) is in the HTML inline script.
    // updateAuthUI() is called by auth.js's own DOMContentLoaded.

    const clientNameSpan = document.getElementById('history-client-name');
    const clientEmailSpan = document.getElementById('history-client-email');
    const pageMainTitle = document.getElementById('page-main-title');
    const salesHistoryTableBody = document.getElementById('sales-history-table-body');

    async function loadClientAndSalesHistory(userId) {
        const token = getToken();
        if (!token) {
            console.warn("No token found, redirecting from loadClientAndSalesHistory (safeguard).");
            window.location.href = 'login.html';
            return;
        }

        let clientName = 'Cliente'; // Default
        let clientEmail = 'N/A';

        try {
            // 1. Attempt to Fetch Client Details (might fail for non-admin viewing own)
            const clientResponse = await fetch(`${API_BASE_URL}/api/admin/client-profiles/${userId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (clientResponse.ok) {
                const userData = await clientResponse.json(); // UserReadWithClientProfile
                clientName = userData.full_name || 'Cliente';
                clientEmail = userData.email || 'N/A';
            } else if (clientResponse.status === 401 || clientResponse.status === 403) {
                // Non-admin trying to access admin route for their own profile.
                // Try fetching from /api/me/profile if IDs match (more robust for future)
                // For now, just log and use defaults, or try to get current user's email from token payload
                // For simplicity, if admin endpoint fails, we'll use generic titles.
                // A better approach would be to check if userId matches loggedInUserId (from token or /me/profile)
                // and then fetch from /api/me/profile for name and email.
                console.warn(`Admin client details fetch failed (${clientResponse.status}). User might be viewing their own history.`);
                // Attempt to get current user's details if it's their own profile
                // This requires knowing the current logged-in user's ID.
                // For now, we'll just use the defaults set above if this specific admin call fails.
                // A more robust solution would fetch from /api/me/profile to get the current user's details
                // and compare IDs to decide if this is "my profile" context.
            } else {
                // Other non-auth error from admin route
                console.warn(`Error fetching client details via admin route: ${clientResponse.statusText}`);
            }
        } catch (e) {
            console.warn('Exception fetching client details via admin route:', e);
        }

        // Update client info display with fetched or default data
        if (clientNameSpan) clientNameSpan.textContent = clientName;
        if (clientEmailSpan) clientEmailSpan.textContent = clientEmail;
        const dynamicTitle = `Historial de Compras de ${clientName}`;
        if (pageMainTitle) pageMainTitle.textContent = dynamicTitle;
        document.title = `${dynamicTitle} - Showroom Natura OjitOs`;


        // 2. Fetch Sales History (this endpoint should work for both admin and user for their own sales)
        try {
            const salesResponse = await fetch(`${API_BASE_URL}/api/users/${userId}/sales/?limit=200`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (salesResponse.status === 401 || salesResponse.status === 403) {
                logout();
                window.location.href = 'login.html';
                return;
            }
            if (!salesResponse.ok) {
                const errData = await salesResponse.json().catch(() => ({detail: `Error al cargar historial de ventas (status: ${salesResponse.status})`}));
                throw new Error(errData.detail || `Error al cargar historial de ventas: ${salesResponse.statusText}`);
            }
            const salesHistory = await salesResponse.json();

            if (salesHistoryTableBody) {
                salesHistoryTableBody.innerHTML = '';
                if (salesHistory.length === 0) {
                    const row = salesHistoryTableBody.insertRow();
                    const cell = row.insertCell();
                    cell.colSpan = 4;
                    cell.textContent = 'Este cliente no tiene historial de compras.';
                    cell.style.textAlign = 'center';
                } else {
                    salesHistory.forEach(sale => {
                        const row = salesHistoryTableBody.insertRow();
                        row.insertCell().textContent = sale.id;
                        row.insertCell().textContent = new Date(sale.sale_date).toLocaleDateString('es-ES', {
                            year: 'numeric', month: 'long', day: 'numeric',
                            hour: '2-digit', minute: '2-digit', second: '2-digit'
                        });
                        row.insertCell().textContent = `S/. ${sale.total_amount.toFixed(2)}`;
                        row.insertCell().textContent = sale.status;
                    });
                }
            }
        } catch (salesError) { // Catch errors specifically from sales fetch or processing
            console.error('Error loading sales history:', salesError);
            const salesErrorMessage = `Error al cargar historial de compras: ${salesError.message}.`;
            if (salesHistoryTableBody) {
                salesHistoryTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--error-color);">${salesErrorMessage}</td></tr>`;
            } else {
                // If client details loaded but sales failed, update main title or use an alert
                if (pageMainTitle) pageMainTitle.textContent = salesErrorMessage;
                else alert(salesErrorMessage);
            }
            // Optionally update document title for sales error specifically
            document.title = "Error Cargando Historial de Compras - Showroom Natura OjitOs";
        }

        // Adjust "Volver" button based on referrer
        const backButton = document.querySelector('.page-actions a[href="admin_clients.html"]');
        if (backButton) {
            if (document.referrer.includes('my_profile.html')) {
                backButton.textContent = 'Volver a Mi Perfil';
                backButton.href = 'my_profile.html';
            }
        }
    }

    const params = new URLSearchParams(window.location.search);
    const userId = params.get('user_id');

    if (userId && !isNaN(parseInt(userId))) {
        loadClientAndSalesHistory(parseInt(userId));
    } else {
        console.error('User ID no encontrado o inválido en la URL.');
        const errorMsg = 'ID de usuario no proporcionado o inválido.';
        if (salesHistoryTableBody) {
             salesHistoryTableBody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--error-color);">${errorMsg}</td></tr>`;
        }
        if (pageMainTitle) pageMainTitle.textContent = "Error: Usuario no especificado";
        if (clientNameSpan) clientNameSpan.textContent = 'Error';
        if (clientEmailSpan) clientEmailSpan.textContent = 'Error';
        document.title = "Error - Usuario no especificado - Showroom Natura OjitOs";
    }
});
