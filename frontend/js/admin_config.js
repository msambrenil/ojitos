// Element References
const configForm = document.getElementById('site-config-form');
// Brand
const siteNameInput = document.getElementById('config-site-name');
const contactEmailInput = document.getElementById('config-contact-email');
const contactPhoneInput = document.getElementById('config-contact-phone');
const colorPrimaryInput = document.getElementById('config-color-primary');
const colorSecondaryInput = document.getElementById('config-color-secondary');
const colorAccentInput = document.getElementById('config-color-accent');
// Logo
const logoUploadInput = document.getElementById('config-logo-upload');
const logoPreviewImg = document.getElementById('config-logo-preview');
// Social
const instagramUrlInput = document.getElementById('config-social-instagram');
const tiktokUrlInput = document.getElementById('config-social-tiktok');
const whatsappUrlInput = document.getElementById('config-social-whatsapp');
const fairUrlInput = document.getElementById('config-online-fair');
// Address
const addressTextarea = document.getElementById('config-showroom-address');
// System Params
const pointsPerUnitInput = document.getElementById('config-points-per-unit');
const discountPercentageInput = document.getElementById('config-showroom-discount');
// Messages
const errorMessageDiv = document.getElementById('config-error-message');
const successMessageDiv = document.getElementById('config-success-message');

const LOGO_PLACEHOLDER = 'images/logo_placeholder.png'; // Define placeholder path

// --- Utility Functions ---
function displayMessage(element, message, isError = false) {
    if (!element) return;
    element.textContent = message;
    element.className = isError ? 'error-message' : 'success-message';
    element.style.display = 'block';
    setTimeout(() => { element.style.display = 'none'; }, 5000); // Hide after 5s
}

// --- Core Logic ---
async function loadSiteConfiguration() {
    try {
        // API_BASE_URL should be globally available (e.g., from auth.js or a config script)
        const response = await fetch(`${API_BASE_URL}/api/configuration/`);
        if (!response.ok) {
            if (response.status === 404) { // Config not yet created, use defaults (already in HTML values)
                console.warn('Site configuration not found on server. Using form defaults.');
                if (logoPreviewImg) logoPreviewImg.src = LOGO_PLACEHOLDER;
                // No error message needed, admin can just save to create the first config.
                return;
            }
            throw new Error('No se pudo cargar la configuración del sitio.');
        }
        const config = await response.json();

        if (siteNameInput) siteNameInput.value = config.site_name || '';
        if (contactEmailInput) contactEmailInput.value = config.contact_email || '';
        if (contactPhoneInput) contactPhoneInput.value = config.contact_phone || '';
        if (colorPrimaryInput) colorPrimaryInput.value = config.color_primary || '#000000';
        if (colorSecondaryInput) colorSecondaryInput.value = config.color_secondary || '#000000';
        if (colorAccentInput) colorAccentInput.value = config.color_accent || '#000000';

        if (logoPreviewImg) {
            logoPreviewImg.src = config.logo_url ? `${API_BASE_URL}${config.logo_url}` : LOGO_PLACEHOLDER;
        }

        if (instagramUrlInput) instagramUrlInput.value = config.social_instagram_url || '';
        if (tiktokUrlInput) tiktokUrlInput.value = config.social_tiktok_url || '';
        if (whatsappUrlInput) whatsappUrlInput.value = config.social_whatsapp_url || '';
        if (fairUrlInput) fairUrlInput.value = config.online_fair_url || '';
        if (addressTextarea) addressTextarea.value = config.showroom_address || '';

        if (pointsPerUnitInput) pointsPerUnitInput.value = config.system_param_points_per_currency_unit !== null ? config.system_param_points_per_currency_unit.toString() : '';
        if (discountPercentageInput) discountPercentageInput.value = config.system_param_default_showroom_discount_percentage !== null ? config.system_param_default_showroom_discount_percentage.toString() : '';

    } catch (error) {
        console.error("Error loading site configuration:", error);
        displayMessage(errorMessageDiv, error.message || 'Error al cargar configuración.', true);
    }
}

function handleLogoInputChange() {
    if (logoUploadInput.files && logoUploadInput.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            if (logoPreviewImg) logoPreviewImg.src = e.target.result;
        }
        reader.readAsDataURL(logoUploadInput.files[0]);
    } else {
        // If no file is selected, should we revert to saved logo or placeholder?
        // For now, let's keep the current preview (which might be the newly selected one or old one)
        // Or, better, reload the currently saved one if user clears selection.
        // This function is primarily for *previewing* a new selection.
        // If a file is selected and then "cleared" from file input, this event might not fire consistently.
        // The `loadSiteConfiguration` will always load the current server logo.
    }
}

async function handleSaveConfiguration(event) {
    event.preventDefault();
    const token = getToken(); // Assumed from auth.js

    if (!token) {
        displayMessage(errorMessageDiv, 'No autenticado. Por favor, inicie sesión.', true);
        // Optional: redirect to login
        // window.location.href = 'login.html';
        return;
    }

    if (errorMessageDiv) errorMessageDiv.style.display = 'none';
    if (successMessageDiv) successMessageDiv.style.display = 'none';

    // Step 1: Upload Logo if a new one is selected
    let newLogoUploaded = false;
    if (logoUploadInput.files && logoUploadInput.files[0]) {
        const logoFormData = new FormData();
        logoFormData.append('logo_file', logoUploadInput.files[0]); // Match FastAPI parameter name
        try {
            const logoResponse = await fetch(`${API_BASE_URL}/api/configuration/upload-logo`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: logoFormData
            });

            if (logoResponse.status === 401 || logoResponse.status === 403) {
                if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
                return;
            }
            const logoResult = await logoResponse.json();
            if (!logoResponse.ok) throw new Error(logoResult.detail || 'Error al subir el logo.');

            console.log("Logo uploaded successfully. Path (from response):", logoResult.logo_url);
            newLogoUploaded = true;
            // The new logo_url is saved by the backend. loadSiteConfiguration will fetch it.
        } catch (error) {
            console.error("Error uploading logo:", error);
            displayMessage(errorMessageDiv, `Error al subir logo: ${error.message}`, true);
            return; // Stop if logo upload fails
        }
    }

    // Step 2: Prepare and save other configuration data
    // Ensure values are correctly parsed (numbers) or null if empty and field is Optional[float/int]
    const pointsPerUnit = pointsPerUnitInput.value ? parseFloat(pointsPerUnitInput.value) : null;
    const discountPercentage = discountPercentageInput.value ? parseInt(discountPercentageInput.value, 10) : null;

    const configDataForUpdate = {
        site_name: siteNameInput.value || null, // Send null if empty, backend uses default if applicable
        contact_email: contactEmailInput.value || null,
        contact_phone: contactPhoneInput.value || null,
        color_primary: colorPrimaryInput.value, // Color inputs always have a value
        color_secondary: colorSecondaryInput.value,
        color_accent: colorAccentInput.value,
        social_instagram_url: instagramUrlInput.value || null,
        social_tiktok_url: tiktokUrlInput.value || null,
        social_whatsapp_url: whatsappUrlInput.value || null,
        online_fair_url: fairUrlInput.value || null,
        showroom_address: addressTextarea.value || null,
        system_param_points_per_currency_unit: pointsPerUnit,
        system_param_default_showroom_discount_percentage: discountPercentage,
    };

    try {
        const configResponse = await fetch(`${API_BASE_URL}/api/configuration/`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(configDataForUpdate)
        });

        if (configResponse.status === 401 || configResponse.status === 403) {
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }
        const configResult = await configResponse.json();
        if (!configResponse.ok) throw new Error(configResult.detail || 'Error al guardar la configuración.');

        displayMessage(successMessageDiv, '¡Configuración guardada exitosamente!');
        // Reload all config, including potentially new logo_url if logo was changed (even if text data save failed, logo might be new)
        await loadSiteConfiguration();

        // Optional: Trigger global config update for live preview (e.g., theme colors, site name)
        if (typeof fetchAndApplySiteConfiguration === 'function') {
            fetchAndApplySiteConfiguration();
        }

    } catch (error) {
        console.error("Error saving configuration data:", error);
        displayMessage(errorMessageDiv, `Error al guardar datos: ${error.message}`, true);
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    // Basic page protection is in HTML (isLoggedIn). Admin role for saving is checked by backend.
    // auth.js should handle visibility of #nav-admin-config-link based on superuser status.

    if (typeof loadSiteConfiguration === 'function') {
        loadSiteConfiguration();
    }

    if (configForm) {
        configForm.addEventListener('submit', handleSaveConfiguration);
    }

    if (logoUploadInput) {
        logoUploadInput.addEventListener('change', handleLogoInputChange);
    }
});

console.log("admin_config.js parsed and event listeners should be set up if elements exist.");
