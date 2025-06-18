// console.log("admin_clients.js loaded");

// DOM Element References
const adminClientSearchInput = document.getElementById('admin-client-search');
const adminClientLevelFilter = document.getElementById('admin-client-level-filter');
const adminClientStatusFilter = document.getElementById('admin-client-status-filter');
const adminApplyClientFiltersButton = document.getElementById('admin-apply-client-filters-button');
const adminClearClientFiltersButton = document.getElementById('admin-clear-client-filters-button');

const adminClientModal = document.getElementById('admin-edit-client-modal');
const adminClientEditForm = document.getElementById('admin-client-edit-form');
const adminClientModalTitle = document.getElementById('admin-client-modal-title');
const adminFormUserId = document.getElementById('admin-form-user-id');
const adminFormFullname = document.getElementById('admin-form-fullname');
const adminFormEmail = document.getElementById('admin-form-email');
const adminFormNickname = document.getElementById('admin-form-nickname');
const adminFormWhatsapp = document.getElementById('admin-form-whatsapp');
const adminFormGender = document.getElementById('admin-form-gender');
const adminFormClientLevel = document.getElementById('admin-form-client-level');
const adminFormProfileImageInput = document.getElementById('admin-form-profile-image');
const adminCurrentImagePreview = document.getElementById('admin-current-profile-image-preview');
const adminRemoveProfileImageButton = document.getElementById('admin-remove-profile-image-button');

const clientTableBody = document.getElementById('admin-client-table-body');
const adminClientModalCloseButton = document.getElementById('admin-client-modal-close-button');
const adminClientModalCancelButton = document.getElementById('admin-client-modal-cancel-button');


// Enhanced Modal Control Functions
function openAdminClientModal() {
    if (adminClientModal) adminClientModal.style.display = 'block';
}

function closeAdminClientModal() {
    if (adminClientModal) adminClientModal.style.display = 'none';
    if (adminClientEditForm) adminClientEditForm.reset();
    if (adminFormUserId) adminFormUserId.value = '';
    if (adminCurrentImagePreview) adminCurrentImagePreview.innerHTML = '';
    if (adminRemoveProfileImageButton) adminRemoveProfileImageButton.style.display = 'none';
    if (adminFormProfileImageInput) adminFormProfileImageInput.value = ''; // Clear file input
}

// Event Listeners for Modal general close/cancel
if (adminClientModalCloseButton) {
    adminClientModalCloseButton.addEventListener('click', closeAdminClientModal);
}
if (adminClientModalCancelButton) {
    adminClientModalCancelButton.addEventListener('click', closeAdminClientModal);
}
if (adminClientModal) {
    adminClientModal.addEventListener('click', (event) => {
        if (event.target === adminClientModal) {
            closeAdminClientModal();
        }
    });
}


// Prepare Modal for Editing Client Profile
async function openAdminEditModal(userId) {
    if (!adminClientModalTitle || !adminFormUserId || !adminClientEditForm || !adminFormFullname || !adminFormEmail ||
        !adminFormNickname || !adminFormWhatsapp || !adminFormGender || !adminFormClientLevel ||
        !adminCurrentImagePreview || !adminRemoveProfileImageButton || !adminFormProfileImageInput) {
        console.error("One or more modal form elements are missing for admin edit.");
        alert("Error al cargar el formulario de edición.");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/client-profiles/${userId}`, {
            headers: { 'Authorization': `Bearer ${getToken()}` } // Use getToken()
        });
        if (!response.ok) {
            const errText = await response.text();
            throw new Error(`Failed to fetch client details: ${response.status} ${errText}`);
        }
        const user = await response.json();

        adminClientModalTitle.textContent = "Editar Perfil de Cliente";
        adminFormUserId.value = user.id;
        adminFormFullname.value = user.full_name || '';
        adminFormEmail.value = user.email || '';

        adminFormNickname.value = user.client_profile?.nickname || '';
        adminFormWhatsapp.value = user.client_profile?.whatsapp_number || '';
        adminFormGender.value = user.client_profile?.gender || '';
        adminFormClientLevel.value = user.client_profile?.client_level || 'Plata';

        adminFormProfileImageInput.value = '';

        if (user.client_profile?.profile_image_url) {
            adminCurrentImagePreview.innerHTML = `<p>Imagen actual:</p><img src="${user.client_profile.profile_image_url}" alt="Profile Image">`;
            adminRemoveProfileImageButton.style.display = 'inline-block';
        } else {
            adminCurrentImagePreview.innerHTML = '<p>No hay imagen de perfil.</p>';
            adminRemoveProfileImageButton.style.display = 'none';
        }

        openAdminClientModal();
    } catch (error) {
        console.error("Error opening admin edit modal:", error);
        alert(`No se pudieron cargar los datos del cliente: ${error.message}`);
    }
}


// Fetch and Display Clients (Modified for filters and Edit button listener)
async function fetchAndDisplayAdminClients(filters = {}) {
    if (!clientTableBody) {
        console.error("Admin client table body not found!");
        return;
    }

    const params = new URLSearchParams();
    if (filters.searchTerm) {
        params.append('search_term', filters.searchTerm);
    }
    if (filters.clientLevel) {
        params.append('client_level', filters.clientLevel);
    }
    if (filters.isActive !== undefined && filters.isActive !== "") {
        params.append('is_active', filters.isActive);
    }
    params.append('skip', '0');
    params.append('limit', '100');

    const queryString = params.toString();
    const apiUrl = `${API_BASE_URL}/api/admin/client-profiles/${queryString ? '?' + queryString : ''}`;

    try {
        const response = await fetch(apiUrl, {
            headers: { 'Authorization': `Bearer ${getToken()}` } // Use getToken()
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const users = await response.json();

        clientTableBody.innerHTML = '';

        if (users.length === 0) {
            clientTableBody.innerHTML = '<tr><td colspan="8">No se encontraron clientes.</td></tr>';
            return;
        }

        users.forEach(user => {
            const row = clientTableBody.insertRow();

            row.insertCell().textContent = user.id;
            row.insertCell().textContent = user.full_name || '-';
            row.insertCell().textContent = user.email;

            const profile = user.client_profile;

            row.insertCell().textContent = profile?.nickname || '-';

            const whatsappCell = row.insertCell();
            if (profile?.whatsapp_number) {
                const cleanPhoneNumber = profile.whatsapp_number.replace(/[^0-9]/g, '');
                whatsappCell.innerHTML = `<a href="https://wa.me/${cleanPhoneNumber}" target="_blank">${profile.whatsapp_number} <i class="fab fa-whatsapp"></i></a>`;
            } else {
                whatsappCell.textContent = '-';
            }

            row.insertCell().textContent = profile?.client_level || '-';
            row.insertCell().textContent = user.is_active ? 'Sí' : 'No';

            const actionsCell = row.insertCell();
            const editButton = document.createElement('button');
            editButton.classList.add('admin-edit-client-button', 'mdc-button--outlined'); // Ensure classes for styling
            editButton.textContent = 'Editar Perfil';
            editButton.dataset.userId = user.id;
            editButton.addEventListener('click', () => openAdminEditModal(user.id));
            actionsCell.appendChild(editButton);

            const historyButton = document.createElement('button');
            historyButton.classList.add('admin-view-history-button', 'mdc-button--outlined');
            historyButton.textContent = 'Ver Historial';
            historyButton.dataset.userId = user.id;
            historyButton.addEventListener('click', (event) => { // Added event listener
                event.preventDefault();
                const userId = historyButton.dataset.userId;
                if (userId) {
                    window.location.href = `admin_client_history.html?user_id=${userId}`;
                } else {
                    console.error("User ID not found on 'Ver Historial' button:", historyButton);
                    alert("No se pudo obtener el ID del usuario para ver el historial.");
                }
            });
            actionsCell.appendChild(historyButton);
        });

    } catch (error) {
        console.error("Error fetching admin clients:", error);
        if (clientTableBody) {
            clientTableBody.innerHTML = '<tr><td colspan="8">Error al cargar la lista de clientes. Ver consola para más detalles.</td></tr>';
        }
    }
}

// Handle Admin Client Form Submission
async function handleAdminClientFormSubmit(event) {
    event.preventDefault();
    const userId = adminFormUserId.value;
    if (!userId) {
        alert("Error: User ID no encontrado en el formulario.");
        return;
    }

    const profileUpdateData = {
        nickname: adminFormNickname.value,
        whatsapp_number: adminFormWhatsapp.value,
        gender: adminFormGender.value,
        client_level: adminFormClientLevel.value
    };

    try {
        // 1. Update text/select data
        const textDataResponse = await fetch(`${API_BASE_URL}/api/admin/client-profiles/${userId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getToken()}` // Use getToken()
            },
            body: JSON.stringify(profileUpdateData)
        });

        if (!textDataResponse.ok) {
            const err = await textDataResponse.json().catch(() => ({ detail: 'Error al actualizar datos del perfil.' }));
            throw new Error(err.detail || 'Error al actualizar datos del perfil.');
        }

        // 2. Handle image upload if a new image is selected
        if (adminFormProfileImageInput && adminFormProfileImageInput.files.length > 0) {
            const imageFormData = new FormData();
            imageFormData.append('image', adminFormProfileImageInput.files[0]);

            const imageResponse = await fetch(`${API_BASE_URL}/api/admin/client-profiles/${userId}/profile-image`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${getToken()}` }, // Use getToken()
                body: imageFormData
            });

            if (!imageResponse.ok) {
                const imgErr = await imageResponse.json().catch(() => ({ detail: 'Error al subir la nueva imagen de perfil.' }));
                throw new Error(imgErr.detail || 'Error al subir la nueva imagen de perfil.');
            }
        }

        alert('Perfil de cliente actualizado exitosamente!');
        closeAdminClientModal();
        fetchAndDisplayAdminClients({}); // Refresh table with no filters
    } catch (error) {
        console.error("Error submitting client profile form:", error);
        alert(`Error: ${error.message}`);
    }
}

if (adminClientEditForm) {
    adminClientEditForm.addEventListener('submit', handleAdminClientFormSubmit);
}

// Handle Remove Profile Image (Admin)
async function handleAdminRemoveProfileImage() {
    const userId = adminFormUserId.value;
    if (!userId) {
        alert('User ID no encontrado. No se puede eliminar la imagen.');
        return;
    }
    if (!confirm('¿Estás seguro de que deseas eliminar la imagen de perfil actual para este cliente?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/client-profiles/${userId}/profile-image`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` } // Use getToken()
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: 'Error al eliminar la imagen de perfil.' }));
            throw new Error(err.detail || 'Error al eliminar la imagen de perfil.');
        }

        alert('Imagen de perfil eliminada exitosamente.');
        if(adminCurrentImagePreview) adminCurrentImagePreview.innerHTML = '<p>No hay imagen de perfil.</p>';
        if(adminRemoveProfileImageButton) adminRemoveProfileImageButton.style.display = 'none';
        if(adminFormProfileImageInput) adminFormProfileImageInput.value = '';

    } catch (error) {
        console.error("Error deleting profile image (admin):", error);
        alert(`Error: ${error.message}`);
    }
}

if (adminRemoveProfileImageButton) {
    adminRemoveProfileImageButton.addEventListener('click', handleAdminRemoveProfileImage);
}


// Initial call on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    console.log("Admin Clients DOMContentLoaded");
    fetchAndDisplayAdminClients(); // Initial load with no filters

    // Add Event Listeners for Filter Buttons
    if (adminApplyClientFiltersButton) {
        adminApplyClientFiltersButton.addEventListener('click', () => {
            const filters = {
                searchTerm: adminClientSearchInput.value.trim(),
                clientLevel: adminClientLevelFilter.value,
                isActive: adminClientStatusFilter.value
            };
            fetchAndDisplayAdminClients(filters);
        });
    }

    if (adminClearClientFiltersButton) {
        adminClearClientFiltersButton.addEventListener('click', () => {
            if(adminClientSearchInput) adminClientSearchInput.value = '';
            if(adminClientLevelFilter) adminClientLevelFilter.value = '';
            if(adminClientStatusFilter) adminClientStatusFilter.value = '';
            fetchAndDisplayAdminClients(); // Call with no/empty filters
        });
    }
});
