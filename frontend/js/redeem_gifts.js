let currentUserAvailablePoints = 0;

const userAvailablePointsSpan = document.getElementById('user-available-points-gifts');
const giftItemsContainer = document.getElementById('gift-items-container');
const noGiftsMessage = document.getElementById('no-gifts-message');

// Assumed from auth.js: API_BASE_URL, getToken(), logout(), isLoggedIn()

function displayRedeemMessage(message, isError = false, duration = 4000) {
    if (isError) {
        console.error("Redeem Page Error:", message);
        alert(`Error: ${message}`);
    } else {
        console.log("Redeem Page Success:", message);
        alert(message);
    }
}

function renderGiftItem(giftItem, userPoints) {
    const product = giftItem.product;
    if (!product) return null;

    const card = document.createElement('div');
    card.classList.add('product-card', 'gift-item-card');
    card.dataset.giftItemId = giftItem.id;
    card.dataset.pointsRequired = giftItem.points_required;
    card.dataset.giftName = product.name;

    let canRedeem = true;
    let redeemButtonText = '<i class="fas fa-gift"></i> Canjear Regalo';
    let reasonDisabled = '';

    if (!giftItem.is_active_as_gift) {
         canRedeem = false;
         reasonDisabled = '(No disponible)';
         card.classList.add('product-unavailable'); // General class for not active or no stock
    } else if (giftItem.stock_available_for_redeem <= 0) {
        canRedeem = false;
        reasonDisabled = '(Agotado para canje)';
        card.classList.add('product-sold-out');
    } else if (userPoints < giftItem.points_required) {
        canRedeem = false;
        reasonDisabled = '(Puntos insuficientes)';
    }

    card.innerHTML = `
        <img src="${product.image_url || 'images/avatar_placeholder.png'}" alt="${product.name}" class="product-image">
        <div class="product-info">
            <h3 class="product-name">${product.name}</h3>
            <p class="gift-points-required">Puntos Necesarios: <span style="font-weight:bold;">${giftItem.points_required}</span></p>
            <p class="gift-stock-available">Disponibles para canje: <span style="font-weight:bold;">${giftItem.stock_available_for_redeem}</span></p>
        </div>
        <div class="product-actions">
            <button class="redeem-gift-button mdc-button--raised"
                    data-gift-item-id="${giftItem.id}"
                    data-points-required="${giftItem.points_required}"
                    data-gift-name="${product.name}"
                    ${!canRedeem ? 'disabled title="' + reasonDisabled + '"' : ''}>
                ${redeemButtonText} ${reasonDisabled}
            </button>
        </div>
    `;
    return card;
}

async function handleRedeemRequest(event) {
    const button = event.currentTarget;
    const giftItemId = parseInt(button.dataset.giftItemId);
    const pointsRequired = parseInt(button.dataset.pointsRequired);
    const giftName = button.dataset.giftName;

    if (!confirm(`¿Canjear "${giftName}" por ${pointsRequired} puntos? Esta acción enviará una solicitud para aprobación.`)) return;

    const token = getToken();
    if (!token) {
        displayRedeemMessage("Debes iniciar sesión para canjear regalos.", true);
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/me/redeem/requests/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ gift_item_id: giftItemId })
        });

        if (response.status === 401 || response.status === 403) {
            logout();
            window.location.href = 'login.html';
            return;
        }

        const result = await response.json();
        if (!response.ok) {
            throw new Error(result.detail || 'Error al enviar la solicitud de canje.');
        }

        displayRedeemMessage(`Solicitud para canjear "${giftName}" enviada. Será revisada por un administrador.`, false);
        button.textContent = 'Solicitud Enviada';
        button.disabled = true;
        // Points are not deducted here, but upon admin approval.
        // Could refresh available gifts if stock might have changed and we want immediate feedback,
        // but current plan is admin handles stock deduction on approval.
        // loadUserPointsAndAvailableGifts(); // Potentially reload to reflect any immediate changes if any
    } catch (error) {
        console.error("Error requesting redemption:", error);
        displayRedeemMessage(error.message, true);
    }
}

async function loadUserPointsAndAvailableGifts() {
    const token = getToken();
    if (!token) {
        // This case should be handled by the inline script in HTML that redirects to login.
        // If it's reached, it's a fallback.
        console.warn("No token found; user should have been redirected.");
        if (userAvailablePointsSpan) userAvailablePointsSpan.textContent = 'N/A';
        if (giftItemsContainer) giftItemsContainer.innerHTML = '<p>Por favor, inicia sesión para ver los regalos.</p>';
        if (noGiftsMessage) noGiftsMessage.style.display = 'none';
        return;
    }

    // 1. Fetch User Points
    try {
        const profileResponse = await fetch(`${API_BASE_URL}/api/me/profile/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (profileResponse.status === 401) { logout(); window.location.href = 'login.html'; return; }
        if (!profileResponse.ok) throw new Error('No se pudieron cargar tus puntos.');
        const userData = await profileResponse.json();
        currentUserAvailablePoints = userData.client_profile?.available_points || 0;
        if (userAvailablePointsSpan) userAvailablePointsSpan.textContent = currentUserAvailablePoints.toString();
    } catch (error) {
        console.error("Error fetching user points:", error);
        if (userAvailablePointsSpan) userAvailablePointsSpan.textContent = 'Error';
        // Proceed to load gifts even if points display fails, as they might still be viewable.
    }

    // 2. Fetch Active Gift Items
    if (!giftItemsContainer) {
        console.error("Gift items container not found in DOM.");
        return;
    }
    try {
        const giftsResponse = await fetch(`${API_BASE_URL}/api/admin/gift-items/?is_active=true&limit=100`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {} // Admin endpoint, but GET might be open to auth users
        });
        if (giftsResponse.status === 401 || giftsResponse.status === 403) {
            // If GET /api/admin/gift-items/ is strictly admin, this page won't work for normal users.
            // This implies a public endpoint for gifts might be needed if admin one is too restrictive.
            // For now, assuming authenticated users can at least GET from this admin endpoint.
            console.warn("Authorization error fetching gift items. This might require admin rights or a public gift endpoint.");
            logout(); window.location.href = 'login.html'; return;
        }
        if (!giftsResponse.ok) throw new Error('No se pudieron cargar los regalos disponibles.');

        const giftItems = await giftsResponse.json();

        giftItemsContainer.innerHTML = '';
        if (giftItems.length === 0) {
            if (noGiftsMessage) noGiftsMessage.style.display = 'block';
        } else {
            if (noGiftsMessage) noGiftsMessage.style.display = 'none';
            giftItems.forEach(gift => {
                const giftCard = renderGiftItem(gift, currentUserAvailablePoints);
                if (giftCard) giftItemsContainer.appendChild(giftCard);
            });
        }
    } catch (error) {
        console.error("Error loading available gifts:", error);
        giftItemsContainer.innerHTML = `<p class="error-message" style="text-align:center; padding:20px;">${error.message}</p>`;
        if (noGiftsMessage) noGiftsMessage.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Page protection redirect is handled by inline script in HTML.
    // auth.js handles its own UI updates (like nav links) via its DOMContentLoaded.

    if (typeof loadUserPointsAndAvailableGifts === 'function') {
        loadUserPointsAndAvailableGifts();
    }

    if (giftItemsContainer) {
        giftItemsContainer.addEventListener('click', (event) => {
            const redeemButton = event.target.closest('.redeem-gift-button');
            if (redeemButton && !redeemButton.disabled) {
                // Pass an object that mimics event.currentTarget for dataset access
                handleRedeemRequest({ currentTarget: redeemButton });
            }
        });
    }
});
