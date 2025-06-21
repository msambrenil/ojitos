// Element References
const createTagForm = document.getElementById('create-tag-form');
const newTagNameInput = document.getElementById('new-tag-name');
const createTagErrorMessageDiv = document.getElementById('create-tag-error-message');

const tagsTableBody = document.getElementById('tags-table-body');
const noTagsMessage = document.getElementById('no-tags-message');

const editTagModal = document.getElementById('edit-tag-modal');
const editTagForm = document.getElementById('edit-tag-form');
const editTagIdInput = document.getElementById('edit-tag-id');
const editTagNameInput = document.getElementById('edit-tag-name');
const editTagModalTitle = document.getElementById('edit-tag-modal-title');
const editTagErrorMessageDiv = document.getElementById('edit-tag-error-message');
const editTagModalCloseButton = document.getElementById('edit-tag-modal-close-button');
const editTagModalCancelButton = document.getElementById('edit-tag-modal-cancel-button');

// Assumed from auth.js: API_BASE_URL, getToken(), logout()

// --- Utility Functions ---
function displayMessage(element, message, isError = false, duration = 3000) {
    if (!element) {
        console.warn("displayMessage: Target element not found.");
        return;
    }
    element.textContent = message;
    element.className = isError ? 'error-message' : 'success-message'; // Ensure these classes are styled
    element.style.display = 'block';
    setTimeout(() => { element.style.display = 'none'; }, duration);
}

// --- Core Logic ---
async function loadTags() {
    const token = getToken();
    if (!token) {
        console.error("No token found for loading tags. User might need to log in.");
        // Page protection in HTML should ideally handle redirect before this.
        // If reached, could force logout or display a global error.
        if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/tags/?limit=1000`, { // Get up to 1000 tags
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401 || response.status === 403) {
            console.warn("Unauthorized or Forbidden fetching tags. Logging out.");
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al cargar los tags.');
        }

        const tags = await response.json(); // Expects List[TagRead]

        if (!tagsTableBody) {
            console.error("Tags table body not found.");
            return;
        }
        tagsTableBody.innerHTML = ''; // Clear existing table rows

        if (tags.length === 0) {
            if (noTagsMessage) noTagsMessage.style.display = 'block';
        } else {
            if (noTagsMessage) noTagsMessage.style.display = 'none';
            tags.forEach(tag => {
                const row = tagsTableBody.insertRow();
                row.insertCell().textContent = tag.id;
                row.insertCell().textContent = tag.name;

                const actionsCell = row.insertCell();
                // Using mdc-button--outlined and mdc-button--dense for consistency if available
                actionsCell.innerHTML = `
                    <button class="edit-tag-button mdc-button mdc-button--outlined mdc-button--dense" data-tag-id="${tag.id}" data-tag-name="${tag.name}">Editar</button>
                    <button class="delete-tag-button mdc-button mdc-button--outlined mdc-button--dense mdc-button--danger" data-tag-id="${tag.id}" data-tag-name="${tag.name}">Eliminar</button>
                `;
            });
        }
    } catch (error) {
        console.error("Error loading tags:", error);
        // Display error message in a general area if createTagErrorMessageDiv isn't always appropriate
        if (createTagErrorMessageDiv) displayMessage(createTagErrorMessageDiv, error.message, true);
        else alert(`Error al cargar tags: ${error.message}`); // Fallback
    }
}

async function handleCreateTagFormSubmit(event) {
    event.preventDefault();
    if (!newTagNameInput || !createTagErrorMessageDiv) return;

    const tagName = newTagNameInput.value.trim();
    if (!tagName) {
        displayMessage(createTagErrorMessageDiv, 'El nombre del tag no puede estar vacío.', true);
        return;
    }

    const token = getToken();
    if (!token) { /* Should be caught by page protection or loadTags auth check */ return; }

    try {
        const response = await fetch(`${API_BASE_URL}/api/tags/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name: tagName })
        });

        if (response.status === 401 || response.status === 403) {
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Error al crear el tag.');
        }

        displayMessage(createTagErrorMessageDiv, `Tag "${data.name}" creado exitosamente.`, false, 3000);
        newTagNameInput.value = ''; // Clear input
        loadTags(); // Refresh the list
    } catch (error) {
        console.error("Error creating tag:", error);
        displayMessage(createTagErrorMessageDiv, error.message, true);
    }
}

function openEditTagModal(tagId, tagName) {
    if (!editTagModal || !editTagIdInput || !editTagNameInput) return;

    editTagIdInput.value = tagId;
    editTagNameInput.value = tagName;
    if (editTagModalTitle) editTagModalTitle.textContent = `Editar Tag: ${tagName}`;
    if (editTagErrorMessageDiv) editTagErrorMessageDiv.style.display = 'none'; // Clear previous errors
    editTagModal.style.display = 'block';
}

function closeEditTagModal() {
    if (editTagModal) editTagModal.style.display = 'none';
}

async function handleEditTagFormSubmit(event) {
    event.preventDefault();
    if (!editTagIdInput || !editTagNameInput || !editTagErrorMessageDiv) return;

    const tagId = editTagIdInput.value;
    const newTagName = editTagNameInput.value.trim();
    if (!newTagName) {
        displayMessage(editTagErrorMessageDiv, 'El nombre del tag no puede estar vacío.', true);
        return;
    }

    const token = getToken();
    if (!token) { /* Page protection */ return; }

    try {
        const response = await fetch(`${API_BASE_URL}/api/tags/${tagId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name: newTagName })
        });

        if (response.status === 401 || response.status === 403) {
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Error al actualizar el tag.');
        }

        closeEditTagModal();
        // Display success message near the create form or a global notification area
        displayMessage(createTagErrorMessageDiv, `Tag actualizado a "${data.name}".`, false, 3000);
        loadTags(); // Refresh list
    } catch (error) {
        console.error("Error updating tag:", error);
        displayMessage(editTagErrorMessageDiv, error.message, true);
    }
}

async function handleDeleteTag(tagId, tagName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar el tag "${tagName}"? Esto lo quitará de todos los productos asociados.`)) {
        return;
    }

    const token = getToken();
    if (!token) { /* Page protection */ return; }

    try {
        const response = await fetch(`${API_BASE_URL}/api/tags/${tagId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401 || response.status === 403) {
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        if (response.status === 204) { // No content, successful delete
            displayMessage(createTagErrorMessageDiv, `Tag "${tagName}" eliminado.`, false, 3000);
            loadTags(); // Refresh list
        } else {
            const data = await response.json().catch(() => ({})); // Try to parse error, default if not parsable
            throw new Error(data.detail || 'Error al eliminar el tag.');
        }
    } catch (error) {
        console.error("Error deleting tag:", error);
        displayMessage(createTagErrorMessageDiv, error.message, true);
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    // Page protection (basic check if user is logged in) is in HTML.
    // Admin role for CUD operations is enforced by the backend.
    // A more robust frontend check for admin role could be added here if user info (with role) is available.
    if (typeof isLoggedIn === 'function' && !isLoggedIn()) {
        // This check is technically redundant if the HTML inline script already handles it.
        // However, it's a safeguard.
        window.location.href = 'login.html';
        return; // Stop further execution if not logged in
    }

    if (typeof loadTags === 'function') {
        loadTags();
    }

    if (createTagForm) {
        createTagForm.addEventListener('submit', handleCreateTagFormSubmit);
    }
    if (editTagForm) {
        editTagForm.addEventListener('submit', handleEditTagFormSubmit);
    }
    if (editTagModalCloseButton) {
        editTagModalCloseButton.addEventListener('click', closeEditTagModal);
    }
    if (editTagModalCancelButton) { // Assuming 'cancel-modal-button' is a generic class for cancel
        editTagModalCancelButton.addEventListener('click', closeEditTagModal);
    }

    // Event delegation for edit/delete buttons in the table
    if (tagsTableBody) {
        tagsTableBody.addEventListener('click', (event) => {
            const targetButton = event.target.closest('button'); // Get the button element
            if (!targetButton) return;

            const tagId = targetButton.dataset.tagId;
            const tagName = targetButton.dataset.tagName;

            if (targetButton.classList.contains('edit-tag-button')) {
                if (tagId && tagName) openEditTagModal(tagId, tagName);
            } else if (targetButton.classList.contains('delete-tag-button')) {
                if (tagId && tagName) handleDeleteTag(tagId, tagName);
            }
        });
    }
    console.log("admin_tags.js loaded and event listeners attached.");
});
