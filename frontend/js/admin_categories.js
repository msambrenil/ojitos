// Element References
const createCategoryForm = document.getElementById('create-category-form');
const newCategoryNameInput = document.getElementById('new-category-name');
const newCategoryDescriptionTextarea = document.getElementById('new-category-description');
const createCategoryErrorMessageDiv = document.getElementById('create-category-error-message');

const categoriesTableBody = document.getElementById('categories-table-body');
const noCategoriesMessage = document.getElementById('no-categories-message');

const editCategoryModal = document.getElementById('edit-category-modal');
const editCategoryForm = document.getElementById('edit-category-form');
const editCategoryIdInput = document.getElementById('edit-category-id');
const editCategoryNameInput = document.getElementById('edit-category-name');
const editCategoryDescriptionTextarea = document.getElementById('edit-category-description');
const editCategoryModalTitle = document.getElementById('edit-category-modal-title');
const editCategoryErrorMessageDiv = document.getElementById('edit-category-error-message');
const editCategoryModalCloseButton = document.getElementById('edit-category-modal-close-button');
const editCategoryModalCancelButton = document.getElementById('edit-category-modal-cancel-button');

// Assumed from auth.js: API_BASE_URL, getToken(), logout(), isLoggedIn()

// --- Utility Functions ---
function displayMessage(element, message, isError = false, duration = 3000) {
    if (!element) {
        console.warn("displayMessage: Target element not found for message:", message);
        alert(message); // Fallback if specific element is missing
        return;
    }
    element.textContent = message;
    element.className = isError ? 'error-message' : 'success-message'; // Ensure these classes are styled
    element.style.display = 'block';
    setTimeout(() => { element.style.display = 'none'; }, duration);
}

// --- Core Logic ---
async function loadCategories() {
    const token = getToken();
    // Page protection script in HTML should handle basic isLoggedIn check.
    // This function proceeds assuming user is at least logged in.
    // Backend will enforce admin for CUD operations.
    // GET /api/categories is auth-user accessible as per plan, so token is needed.
    if (!token && typeof isLoggedIn === 'function' && isLoggedIn()) {
        // This case (logged in but no token) implies an issue, force logout.
        if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
        return;
    }
    if (!token && typeof isLoggedIn === 'function' && !isLoggedIn()){ // Not logged in, redirect if page protection missed it.
         window.location.href = 'login.html'; return;
    }


    try {
        const response = await fetch(`${API_BASE_URL}/api/categories/?limit=1000`, { // Get up to 1000 categories
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (!response.ok) {
            // If GET is admin-only and fails due to 401/403, this will catch it.
            if (response.status === 401 || response.status === 403) {
                 if (typeof logout === 'function') logout(); else window.location.href = 'login.html'; return;
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Error al cargar las categorías.');
        }

        const categories = await response.json(); // Expects List[CategoryRead]

        if (!categoriesTableBody) {
            console.error("Categories table body not found.");
            return;
        }
        categoriesTableBody.innerHTML = ''; // Clear existing table rows

        if (categories.length === 0) {
            if (noCategoriesMessage) noCategoriesMessage.style.display = 'block';
        } else {
            if (noCategoriesMessage) noCategoriesMessage.style.display = 'none';
            categories.forEach(category => {
                const row = categoriesTableBody.insertRow();
                row.insertCell().textContent = category.id;
                row.insertCell().textContent = category.name;
                row.insertCell().textContent = category.description || '-';

                const actionsCell = row.insertCell();
                actionsCell.innerHTML = `
                    <button class="edit-category-button mdc-button mdc-button--outlined mdc-button--dense" data-category-id="${category.id}" data-category-name="${category.name}" data-category-description="${category.description || ''}">Editar</button>
                    <button class="delete-category-button mdc-button mdc-button--outlined mdc-button--dense mdc-button--danger" data-category-id="${category.id}" data-category-name="${category.name}">Eliminar</button>
                `;
            });
        }
    } catch (error) {
        console.error("Error loading categories:", error);
        if (createCategoryErrorMessageDiv) displayMessage(createCategoryErrorMessageDiv, error.message, true);
        else alert(`Error al cargar categorías: ${error.message}`);
    }
}

async function handleCreateCategoryFormSubmit(event) {
    event.preventDefault();
    if (!newCategoryNameInput || !newCategoryDescriptionTextarea || !createCategoryErrorMessageDiv) return;

    const categoryName = newCategoryNameInput.value.trim();
    const categoryDescription = newCategoryDescriptionTextarea.value.trim();

    if (!categoryName) {
        displayMessage(createCategoryErrorMessageDiv, 'El nombre de la categoría no puede estar vacío.', true);
        return;
    }

    const token = getToken();
    if (!token) {
        alert("Acceso denegado. Inicia sesión como administrador.");
        if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/categories/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name: categoryName, description: categoryDescription })
        });

        if (response.status === 401 || response.status === 403) {
            alert("Acceso denegado. No tienes permisos para esta acción.");
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Error al crear la categoría.');
        }

        displayMessage(createCategoryErrorMessageDiv, `Categoría "${data.name}" creada exitosamente.`, false, 3000);
        newCategoryNameInput.value = '';
        newCategoryDescriptionTextarea.value = '';
        loadCategories(); // Refresh the list
    } catch (error) {
        console.error("Error creating category:", error);
        displayMessage(createCategoryErrorMessageDiv, error.message, true);
    }
}

function openEditCategoryModal(categoryId, name, description) {
    if (!editCategoryModal || !editCategoryIdInput || !editCategoryNameInput || !editCategoryDescriptionTextarea) return;

    editCategoryIdInput.value = categoryId;
    editCategoryNameInput.value = name;
    editCategoryDescriptionTextarea.value = description || '';
    if (editCategoryModalTitle) editCategoryModalTitle.textContent = `Editar Categoría: ${name}`;
    if (editCategoryErrorMessageDiv) editCategoryErrorMessageDiv.style.display = 'none';
    editCategoryModal.style.display = 'block';
}

function closeEditCategoryModal() {
    if (editCategoryModal) editCategoryModal.style.display = 'none';
}

async function handleEditCategoryFormSubmit(event) {
    event.preventDefault();
    if (!editCategoryIdInput || !editCategoryNameInput || !editCategoryDescriptionTextarea || !editCategoryErrorMessageDiv) return;

    const categoryId = editCategoryIdInput.value;
    const newCategoryName = editCategoryNameInput.value.trim();
    const newCategoryDescription = editCategoryDescriptionTextarea.value.trim();

    if (!newCategoryName) {
        displayMessage(editCategoryErrorMessageDiv, 'El nombre de la categoría no puede estar vacío.', true);
        return;
    }

    const token = getToken();
    if (!token) {
        alert("Acceso denegado. Inicia sesión como administrador.");
        if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/categories/${categoryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name: newCategoryName, description: newCategoryDescription })
        });

        if (response.status === 401 || response.status === 403) {
            alert("Acceso denegado. No tienes permisos para esta acción.");
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Error al actualizar la categoría.');
        }

        closeEditCategoryModal();
        displayMessage(createCategoryErrorMessageDiv, `Categoría actualizada a "${data.name}".`, false, 3000);
        loadCategories(); // Refresh list
    } catch (error) {
        console.error("Error updating category:", error);
        displayMessage(editCategoryErrorMessageDiv, error.message, true);
    }
}

async function handleDeleteCategory(categoryId, categoryName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar la categoría "${categoryName}"? Los productos asociados quedarán sin categoría.`)) {
        return;
    }

    const token = getToken();
    if (!token) {
        alert("Acceso denegado. Inicia sesión como administrador.");
        if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/categories/${categoryId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401 || response.status === 403) {
            alert("Acceso denegado. No tienes permisos para esta acción.");
            if (typeof logout === 'function') logout(); else window.location.href = 'login.html';
            return;
        }

        if (response.status === 204) { // No content, successful delete
            displayMessage(createCategoryErrorMessageDiv, `Categoría "${categoryName}" eliminada.`, false, 3000);
            loadCategories(); // Refresh list
        } else {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.detail || 'Error al eliminar la categoría.');
        }
    } catch (error) {
        console.error("Error deleting category:", error);
        displayMessage(createCategoryErrorMessageDiv, error.message, true);
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    if (typeof isLoggedIn === 'function' && !isLoggedIn()) {
        window.location.href = 'login.html';
        return;
    }
    // Further admin role check for page access could be done here if getCurrentUserInfo is available
    // and provides isSuperuser flag. For now, relying on backend for CUD protection.

    if (typeof loadCategories === 'function') {
        loadCategories();
    }

    if (createCategoryForm) {
        createCategoryForm.addEventListener('submit', handleCreateCategoryFormSubmit);
    }
    if (editCategoryForm) {
        editCategoryForm.addEventListener('submit', handleEditCategoryFormSubmit);
    }
    if (editCategoryModalCloseButton) {
        editCategoryModalCloseButton.addEventListener('click', closeEditCategoryModal);
    }
    if (editCategoryModalCancelButton) {
        editCategoryModalCancelButton.addEventListener('click', closeEditCategoryModal);
    }

    if (categoriesTableBody) {
        categoriesTableBody.addEventListener('click', (event) => {
            const targetButton = event.target.closest('button');
            if (!targetButton) return;

            const categoryId = targetButton.dataset.categoryId;
            const categoryName = targetButton.dataset.categoryName;

            if (targetButton.classList.contains('edit-category-button')) {
                const categoryDescription = targetButton.dataset.categoryDescription; // Get description
                if (categoryId && categoryName) openEditCategoryModal(categoryId, categoryName, categoryDescription);
            } else if (targetButton.classList.contains('delete-category-button')) {
                if (categoryId && categoryName) handleDeleteCategory(categoryId, categoryName);
            }
        });
    }
    console.log("admin_categories.js loaded and event listeners attached.");
});
