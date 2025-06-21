const catalogEntriesTableBody = document.getElementById('catalog-entries-table-body');
const noCatalogEntriesMessage = document.getElementById('no-catalog-entries-message');
const addToCatalogButton = document.getElementById('add-to-catalog-button');

const catalogEntryModal = document.getElementById('catalog-entry-modal');
const catalogEntryModalCloseButton = document.getElementById('catalog-entry-modal-close-button');
const catalogEntryModalCancelButton = document.getElementById('catalog-entry-modal-cancel-button');
const catalogEntryModalTitle = document.getElementById('catalog-entry-modal-title');
const catalogEntryForm = document.getElementById('catalog-entry-form');
const formEntryIdInput = document.getElementById('form-entry-id');

// New element references for form fields
const formEntryProductIdSelect = document.getElementById('form-entry-product-id');
const selectedProductPreviewDiv = document.getElementById('selected-product-preview');
const previewProductName = document.getElementById('preview-product-name');
const previewProductPrice = document.getElementById('preview-product-price');
const previewProductImage = document.getElementById('preview-product-image');

const formCatalogPriceInput = document.getElementById('form-entry-catalog-price');
const formCatalogImageUrlInput = document.getElementById('form-entry-catalog-image-url');
const formPromoTextInput = document.getElementById('form-entry-promo-text');
const formIsVisibleCheckbox = document.getElementById('form-entry-is-visible');
const formIsSoldOutCheckbox = document.getElementById('form-entry-is-sold-out');
const formDisplayOrderInput = document.getElementById('form-entry-display-order');
const catalogEntryErrorMessageDiv = document.getElementById('catalog-entry-error-message');

// Global variable for inventory products cache
let availableInventoryProducts = [];
const LOGO_PLACEHOLDER = 'images/avatar_placeholder.png'; // Define a placeholder

// displayMessage helper for form-specific messages
function displayMessage(element, message, isError = false, duration = 0) {
    if (!element) return;
    element.textContent = message;
    element.className = isError ? 'error-message' : 'success-message'; // Ensure style.css has .success-message
    element.style.display = 'block';
    if (duration > 0) {
        setTimeout(() => { element.style.display = 'none'; }, duration);
    }
}

async function handleDeleteCatalogEntry(entryId, productName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar la entrada del catálogo para el producto "${productName}" (ID de Entrada: ${entryId})? Esto no eliminará el producto del inventario, solo su aparición en el catálogo.`)) {
        return;
    }

    const token = getToken();
    const currentUserInfo = getCurrentUserInfo(); // Defined in auth.js
    if (!isLoggedIn() || !token || !currentUserInfo?.isSuperuser) {
        displayAdminCatalogMessage("Acceso denegado o sesión inválida.", true);
        // Consider logout(); window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/catalog/entries/${entryId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401 || response.status === 403) {
            logout(); // from auth.js
            window.location.href = 'login.html';
            return;
        }

        if (response.status === 204) { // Successfully deleted
            displayAdminCatalogMessage(`Entrada del catálogo para "${productName}" eliminada exitosamente.`, false);
            loadCatalogEntries(); // Refresh the table
        } else if (response.status === 404) {
            displayAdminCatalogMessage(`Error: Entrada de catálogo no encontrada (ID: ${entryId}). Ya pudo haber sido eliminada.`, true);
            loadCatalogEntries(); // Refresh table in case it was already removed
        }
        else {
            const errorData = await response.json().catch(() => ({})); // Try to get error detail
            throw new Error(errorData.detail || `Error al eliminar la entrada del catálogo (${response.status}).`);
        }
    } catch (error) {
        console.error("Error deleting catalog entry:", error);
        displayAdminCatalogMessage(error.message, true);
    }
}

// General page message (could be improved to use a dedicated div)
function displayAdminCatalogMessage(message, isError = false, duration = 3000) {
    if (isError) {
        console.error(message);
        // Potentially update a general page message div here
        if (catalogEntryErrorMessageDiv && catalogEntryModal.style.display === 'none') { // Show in form error div if modal is closed
             displayMessage(catalogEntryErrorMessageDiv, message, true);
        } else if (!catalogEntryModal.style.display || catalogEntryModal.style.display === 'none') {
            alert(`Error: ${message}`); // Fallback
        }
    } else {
        console.log(message);
        // Potentially update a general page message div here for success
         if (catalogEntryErrorMessageDiv && catalogEntryModal.style.display === 'none') {
             displayMessage(catalogEntryErrorMessageDiv, message, false);
        } else if (!catalogEntryModal.style.display || catalogEntryModal.style.display === 'none') {
            alert(`Success: ${message}`); // Fallback
        }
    }
}

async function populateProductDropdown() {
    if (!formEntryProductIdSelect) return;
    const token = getToken();
    try {
        // Use admin endpoint for products to get all details if needed, or a simpler one if available
        const response = await fetch(`${API_BASE_URL}/api/products/?limit=2000&is_admin_view=true`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });
        if (!response.ok) throw new Error("No se pudieron cargar los productos para el dropdown.");

        availableInventoryProducts = await response.json();

        while (formEntryProductIdSelect.options.length > 1) formEntryProductIdSelect.remove(1);

        availableInventoryProducts.forEach(product => {
            const option = document.createElement('option');
            option.value = product.id;
            option.textContent = `${product.name} (ID: ${product.id}, Stock: ${product.stock_actual !== null ? product.stock_actual : 'N/A'})`;
            formEntryProductIdSelect.appendChild(option);
        });
    } catch (error) {
        console.error("Error populating product dropdown:", error);
        displayMessage(catalogEntryErrorMessageDiv, error.message, true); // Show error in modal if open
    }
}

async function openCatalogEntryModal(entryId = null) {
    if (catalogEntryForm) catalogEntryForm.reset();
    if (formEntryIdInput) formEntryIdInput.value = entryId || '';
    if (selectedProductPreviewDiv) selectedProductPreviewDiv.style.display = 'none';
    if (catalogEntryErrorMessageDiv) catalogEntryErrorMessageDiv.style.display = 'none';

    // Ensure dropdown is populated
    if (availableInventoryProducts.length === 0) {
        await populateProductDropdown();
    }

    if (!entryId) { // Creating new
        if (catalogEntryModalTitle) catalogEntryModalTitle.textContent = 'Añadir Producto al Catálogo';
        if (formEntryProductIdSelect) {
            formEntryProductIdSelect.disabled = false;
            formEntryProductIdSelect.value = "";
        }
        if(formIsVisibleCheckbox) formIsVisibleCheckbox.checked = true;
        if(formIsSoldOutCheckbox) formIsSoldOutCheckbox.checked = false;
        if(formDisplayOrderInput) formDisplayOrderInput.value = "0";
        if(formCatalogPriceInput) formCatalogPriceInput.value = "";
        if(formCatalogImageUrlInput) formCatalogImageUrlInput.value = "";
        if(formPromoTextInput) formPromoTextInput.value = "";

    } else { // Editing existing
        if (catalogEntryModalTitle) catalogEntryModalTitle.textContent = `Editar Entrada de Catálogo (ID: ${entryId})`;
        const token = getToken();
        try {
            const response = await fetch(`${API_BASE_URL}/api/admin/catalog/entries/${entryId}`, {
                 headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                logout(); // Potentially session expired or auth issue
                window.location.href = 'login.html';
                throw new Error("No se pudo cargar la entrada del catálogo para editar.");
            }
            const entry = await response.json();

            if (formEntryProductIdSelect) {
                formEntryProductIdSelect.value = entry.product.id; // product_id is nested in product object from API
                formEntryProductIdSelect.disabled = true;
                const changeEvent = new Event('change'); // Trigger preview
                formEntryProductIdSelect.dispatchEvent(changeEvent);
            }
            if (formCatalogPriceInput) formCatalogPriceInput.value = entry.catalog_price !== null && entry.catalog_price !== undefined ? entry.catalog_price : '';
            if (formCatalogImageUrlInput) formCatalogImageUrlInput.value = entry.catalog_image_url || '';
            if (formPromoTextInput) formPromoTextInput.value = entry.promo_text || '';
            if (formIsVisibleCheckbox) formIsVisibleCheckbox.checked = entry.is_visible_in_catalog;
            if (formIsSoldOutCheckbox) formIsSoldOutCheckbox.checked = entry.is_sold_out_in_catalog;
            if (formDisplayOrderInput) formDisplayOrderInput.value = entry.display_order;

        } catch (error) {
            console.error("Error fetching catalog entry for edit:", error);
            displayMessage(catalogEntryErrorMessageDiv, error.message, true);
            if (catalogEntryModal) catalogEntryModal.style.display = 'block'; // Keep modal open to show error
            return; // Don't fully open if fetch failed
        }
    }
    if (catalogEntryModal) catalogEntryModal.style.display = 'block';
}

function closeCatalogEntryModal() {
    if (catalogEntryModal) catalogEntryModal.style.display = 'none';
    if (catalogEntryForm) catalogEntryForm.reset();
    if (catalogEntryErrorMessageDiv) catalogEntryErrorMessageDiv.style.display = 'none';
    if (formEntryProductIdSelect) formEntryProductIdSelect.disabled = false; // Re-enable for next time
}

async function handleCatalogEntryFormSubmit(event) {
    event.preventDefault();
    const token = getToken();
    const currentUserInfo = getCurrentUserInfo();
    if (!isLoggedIn() || !token || !currentUserInfo?.isSuperuser) {
        displayMessage(catalogEntryErrorMessageDiv, "Acceso denegado. Debe ser superusuario.", true, 5000);
        setTimeout(() => { logout(); window.location.href = 'login.html'; }, 2000);
        return;
    }

    const entryId = formEntryIdInput.value;
    const isEditing = !!entryId;

    const selectedProductId = formEntryProductIdSelect.value;
    if (!isEditing && !selectedProductId) {
        displayMessage(catalogEntryErrorMessageDiv, "Debe seleccionar un producto del inventario.", true);
        return;
    }

    const data = {
        catalog_price: formCatalogPriceInput.value !== "" ? parseFloat(formCatalogPriceInput.value) : null,
        catalog_image_url: formCatalogImageUrlInput.value.trim() || null,
        promo_text: formPromoTextInput.value.trim() || null,
        is_visible_in_catalog: formIsVisibleCheckbox.checked,
        is_sold_out_in_catalog: formIsSoldOutCheckbox.checked,
        display_order: formDisplayOrderInput.value !== "" ? parseInt(formDisplayOrderInput.value) : 0,
    };

    if (!isEditing) {
        data.product_id = parseInt(selectedProductId);
    }

    // Handle null for empty strings that should be null numbers
    if (data.catalog_price === '') data.catalog_price = null;


    const method = isEditing ? 'PUT' : 'POST';
    const url = isEditing ? `${API_BASE_URL}/api/admin/catalog/entries/${entryId}` : `${API_BASE_URL}/api/admin/catalog/entries/`;

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(data)
        });

        const resultText = await response.text(); // Read text first to avoid JSON parse error on empty/non-JSON response
        let result;
        try {
            result = JSON.parse(resultText);
        } catch (e) {
            // If parsing failed, and response not ok, use text as error detail
            if (!response.ok) {
                 throw new Error(resultText || `Error HTTP ${response.status} al ${isEditing ? 'actualizar' : 'crear'} la entrada.`);
            }
            // If parsing failed but response IS ok (e.g. 204 No Content), then consider it success
            result = { detail: `Entrada de catálogo ${isEditing ? 'actualizada' : 'creada'} exitosamente (respuesta vacía).` };
        }

        if (!response.ok) {
            // Prefer detail from JSON result if available
            throw new Error(result.detail || `Error HTTP ${response.status} al ${isEditing ? 'actualizar' : 'crear'} la entrada.`);
        }

        displayAdminCatalogMessage(`Entrada de catálogo ${isEditing ? 'actualizada' : 'creada'} exitosamente.`, false);
        closeCatalogEntryModal();
        loadCatalogEntries();
    } catch (error) {
        console.error("Error saving catalog entry:", error);
        displayMessage(catalogEntryErrorMessageDiv, error.message, true);
    }
}


async function loadCatalogEntries() {
    const token = getToken();
    if (!isLoggedIn() || !token) { logout(); window.location.href = 'login.html'; return; }
    const userInfo = getCurrentUserInfo();
    if (!userInfo || !userInfo.isSuperuser) {
        displayAdminCatalogMessage("Acceso denegado.", true);
        if (catalogEntriesTableBody) catalogEntriesTableBody.innerHTML = '<tr><td colspan="10">Acceso denegado.</td></tr>';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/catalog/entries/?limit=100`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.status === 401 || response.status === 403) { logout(); window.location.href = 'login.html'; return; }
        if (!response.ok) throw new Error(`Error al cargar entradas del catálogo: ${response.statusText}`);

        const entries = await response.json();
        if (!catalogEntriesTableBody) { console.error("Table body not found."); return; }
        catalogEntriesTableBody.innerHTML = '';

        if (entries.length === 0) {
            if (noCatalogEntriesMessage) noCatalogEntriesMessage.style.display = 'block';
        } else {
            if (noCatalogEntriesMessage) noCatalogEntriesMessage.style.display = 'none';
            entries.forEach(entry => {
                const row = catalogEntriesTableBody.insertRow();
                row.insertCell().textContent = entry.id;
                row.insertCell().textContent = entry.product.id;
                row.insertCell().textContent = entry.product.name;
                row.insertCell().textContent = `S/. ${(entry.effective_price !== null ? entry.effective_price : 0).toFixed(2)}`;

                const imgCell = row.insertCell();
                if (entry.effective_image_url) {
                    const img = document.createElement('img');
                    img.src = entry.effective_image_url.startsWith('http') ? entry.effective_image_url : API_BASE_URL + entry.effective_image_url;
                    img.alt = entry.product.name;
                    img.style.width = '50px'; img.style.height = '50px'; img.style.objectFit = 'cover';
                    imgCell.appendChild(img);
                } else { imgCell.textContent = '-'; }

                row.insertCell().textContent = entry.is_visible_in_catalog ? 'Sí' : 'No';
                row.insertCell().textContent = entry.is_sold_out_in_catalog ? 'Sí' : 'No';
                row.insertCell().textContent = entry.promo_text || '-';
                row.insertCell().textContent = entry.display_order;

                const actionsCell = row.insertCell();
                const editButton = document.createElement('button');
                editButton.className = 'edit-catalog-entry-button mdc-button--outlined';
                editButton.textContent = 'Editar';
                editButton.dataset.entryId = entry.id;
                editButton.addEventListener('click', () => openCatalogEntryModal(entry.id));
                actionsCell.appendChild(editButton);

                const deleteButton = document.createElement('button'); // Delete button logic will be added later
                deleteButton.className = 'delete-catalog-entry-button mdc-button--outlined';
                deleteButton.textContent = 'Eliminar';
                deleteButton.dataset.entryId = entry.id;
                deleteButton.dataset.productName = entry.product.name;
                // deleteButton.addEventListener('click', handleDeleteCatalogEntry); // To be implemented
                actionsCell.appendChild(deleteButton);
            });
        }
    } catch (error) {
        console.error("Error loading catalog entries:", error);
        if (catalogEntriesTableBody) catalogEntriesTableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:red;">${error.message}</td></tr>`;
        if (noCatalogEntriesMessage) noCatalogEntriesMessage.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const userInfo = getCurrentUserInfo();
    if (!isLoggedIn() || !userInfo || !userInfo.isSuperuser) {
        if (catalogEntriesTableBody) catalogEntriesTableBody.innerHTML = '<tr><td colspan="10">Acceso denegado. Redirigiendo...</td></tr>';
        // alert("Acceso denegado (JS check). Se requieren permisos de administrador.");
        // window.location.href = 'index.html';
        return;
    }

    await populateProductDropdown(); // Initial population for "Add" modal
    loadCatalogEntries(); // Load existing entries into table

    if (addToCatalogButton) {
        addToCatalogButton.addEventListener('click', () => {
            openCatalogEntryModal();
        });
    }
    if (catalogEntryModalCloseButton) {
        catalogEntryModalCloseButton.addEventListener('click', closeCatalogEntryModal);
    }
    if (catalogEntryModalCancelButton) {
        catalogEntryModalCancelButton.addEventListener('click', closeCatalogEntryModal);
    }
    if (catalogEntryForm) {
        catalogEntryForm.addEventListener('submit', handleCatalogEntryFormSubmit);
    }

    if (formEntryProductIdSelect) {
        formEntryProductIdSelect.addEventListener('change', () => {
            const selectedProductId = parseInt(formEntryProductIdSelect.value);
            const product = availableInventoryProducts.find(p => p.id === selectedProductId);
            if (product) {
                if (previewProductName) previewProductName.textContent = product.name;
                if (previewProductPrice) {
                    // Assuming price_revista is the base price from ProductRead. Adjust if different.
                    previewProductPrice.textContent = `S/. ${(product.price_revista !== null && product.price_revista !== undefined ? product.price_revista : 0).toFixed(2)}`;
                }
                if (previewProductImage) {
                    previewProductImage.src = product.image_url ? (product.image_url.startsWith('http') ? product.image_url : API_BASE_URL + product.image_url) : LOGO_PLACEHOLDER;
                }
                if (selectedProductPreviewDiv) selectedProductPreviewDiv.style.display = 'block';
            } else {
                if (selectedProductPreviewDiv) selectedProductPreviewDiv.style.display = 'none';
            }
        });
    }

    // Event delegation for edit/delete buttons in table
    if (catalogEntriesTableBody) {
        catalogEntriesTableBody.addEventListener('click', (event) => {
            const editButton = event.target.closest('.edit-catalog-entry-button');
            const deleteButton = event.target.closest('.delete-catalog-entry-button');

            if (editButton) {
                const entryId = editButton.dataset.entryId;
                if (entryId) {
                    openCatalogEntryModal(entryId);
                }
            } else if (deleteButton) {
                const entryId = deleteButton.dataset.entryId;
                const productName = deleteButton.dataset.productName;
                if (entryId) {
                    handleDeleteCatalogEntry(entryId, productName);
                }
            }
        });
    }
});
