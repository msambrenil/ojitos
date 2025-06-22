// If not using modules and auth.js defines API_BASE_URL globally:
// const API_BASE_URL = ''; // Or ensure it's available from auth.js

let currentLoggedInUserId = null;

// Global DOM element declarations (assignments happen in DOMContentLoaded)
let viewFullname, viewEmail, viewNickname, viewWhatsapp, viewGender, viewClientLevel, viewAvailablePoints;
let editProfileForm, editNicknameInput, editWhatsappInput, editGenderSelect, editProfileErrorMessageDiv;
let currentProfileImage, removeProfileImageButton, profileImageUploadInput, uploadProfileImageButton, imageUploadErrorMessageDiv;
let viewMyPurchaseHistoryButton;
let myRedemptionsTableBody, noMyRedemptionsMessage;


// Redemption Request Statuses
const RedemptionRequestStatusEnum = {
    PENDIENTE_APROBACION: "pendiente_aprobacion",
    APROBADO_POR_ENTREGAR: "aprobado_por_entregar",
    ENTREGADO: "entregado",
    RECHAZADO: "rechazado",
    CANCELADO_POR_CLIENTE: "cancelado_por_cliente"
};
const RedemptionRequestStatusDisplay = {
    [RedemptionRequestStatusEnum.PENDIENTE_APROBACION]: "Pendiente de Aprobación",
    [RedemptionRequestStatusEnum.APROBADO_POR_ENTREGAR]: "Aprobado (Por Entregar)",
    [RedemptionRequestStatusEnum.ENTREGADO]: "Entregado",
    [RedemptionRequestStatusEnum.RECHAZADO]: "Rechazado",
    [RedemptionRequestStatusEnum.CANCELADO_POR_CLIENTE]: "Cancelado por Cliente"
};


document.addEventListener('DOMContentLoaded', async () => { // Made async
    // Page protection (redirect if not logged in) is handled by an inline script in my_profile.html
    // updateAuthUI() is called by auth.js's own DOMContentLoaded listener

    // Assign DOM Element References
    viewFullname = document.getElementById('view-fullname');
    viewEmail = document.getElementById('view-email'); // Corrected: remove const
    viewNickname = document.getElementById('view-nickname'); // Corrected: remove const
    viewWhatsapp = document.getElementById('view-whatsapp'); // Corrected: remove const
    viewGender = document.getElementById('view-gender'); // Corrected: remove const
    // Removed duplicate assignments that were already corrected by the lines above
    viewClientLevel = document.getElementById('view-client-level');
    viewAvailablePoints = document.getElementById('view-available-points');

    editProfileForm = document.getElementById('edit-profile-form');
    editNicknameInput = document.getElementById('edit-nickname');
    editWhatsappInput = document.getElementById('edit-whatsapp');
    editGenderSelect = document.getElementById('edit-gender');
    editProfileErrorMessageDiv = document.getElementById('edit-profile-error-message');

    currentProfileImage = document.getElementById('current-profile-image');
    removeProfileImageButton = document.getElementById('remove-profile-image-button');
    profileImageUploadInput = document.getElementById('profile-image-upload');
    uploadProfileImageButton = document.getElementById('upload-profile-image-button');
    imageUploadErrorMessageDiv = document.getElementById('image-upload-error-message');

    // Redemption Request elements
    myRedemptionsTableBody = document.getElementById('my-redemptions-table-body');
    noMyRedemptionsMessage = document.getElementById('no-my-redemptions-message');


    async function loadProfileData() { // This function is already defined within DOMContentLoaded
        const token = getToken(); // from auth.js
        if (!token) {
            // This should have been caught by inline page protection script
            console.warn("No token found, redirecting to login from loadProfileData (safeguard).");
            window.location.href = 'login.html';
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/me/profile/`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.status === 401) { // Token expired or invalid
                logout(); // from auth.js
                window.location.href = 'login.html';
                return;
            }
            if (!response.ok) {
                const errData = await response.json().catch(() => ({detail: 'Error al cargar los datos del perfil.'}));
                throw new Error(errData.detail || 'Error al cargar los datos del perfil.');
            }

            const user = await response.json(); // UserReadWithClientProfile

            // Populate display area
            if (viewFullname) viewFullname.textContent = user.full_name || '-';
            if (viewEmail) viewEmail.textContent = user.email || '-';
            currentLoggedInUserId = user.id; // Store the user ID

            const profile = user.client_profile;
            if (viewNickname) viewNickname.textContent = profile?.nickname || '-';
            if (viewWhatsapp) viewWhatsapp.textContent = profile?.whatsapp_number || '-';
            if (viewGender) viewGender.textContent = profile?.gender || '-';
            if (viewClientLevel) viewClientLevel.textContent = profile?.client_level || '-';
            if (viewAvailablePoints) { // Populate available points
                const points = profile?.available_points;
                viewAvailablePoints.textContent = (points !== null && points !== undefined) ? points.toString() : '0';
            }

            // Populate edit form
            if (editNicknameInput) editNicknameInput.value = profile?.nickname || '';
            if (editWhatsappInput) editWhatsappInput.value = profile?.whatsapp_number || '';
            if (editGenderSelect) editGenderSelect.value = profile?.gender || '';

            // Populate image
            if (currentProfileImage) {
                if (profile?.profile_image_url) {
                    currentProfileImage.src = profile.profile_image_url;
                } else {
                    currentProfileImage.src = 'images/avatar_placeholder.png'; // Default placeholder
                }
            }
            if (removeProfileImageButton) {
                removeProfileImageButton.style.display = profile?.profile_image_url ? 'inline-block' : 'none';
            }

        } catch (error) {
            console.error('Error loading profile data:', error);
            if (editProfileErrorMessageDiv) { // Display error in edit form's error div or a general page error div
                editProfileErrorMessageDiv.textContent = `Error al cargar perfil: ${error.message}`;
                editProfileErrorMessageDiv.style.display = 'block';
            } else {
                alert(`Error al cargar perfil: ${error.message}`);
            }
        }
    }

    async function handleEditProfileFormSubmit(event) {
        event.preventDefault();
        if (editProfileErrorMessageDiv) {
             editProfileErrorMessageDiv.style.display = 'none';
             editProfileErrorMessageDiv.textContent = '';
        }

        const token = getToken();
        if (!token) {
            alert("Sesión no encontrada. Por favor, inicia sesión de nuevo.");
            logout();
            window.location.href = 'login.html';
            return;
        }

        const profileUpdateData = {
            nickname: editNicknameInput ? editNicknameInput.value.trim() : undefined,
            whatsapp_number: editWhatsappInput ? editWhatsappInput.value.trim() : undefined,
            gender: editGenderSelect ? editGenderSelect.value : undefined
        };

        try {
            const response = await fetch(`${API_BASE_URL}/api/me/profile/`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(profileUpdateData)
            });

            if (response.status === 401) {
                logout();
                window.location.href = 'login.html';
                return;
            }

            const responseData = await response.json(); // UserReadWithClientProfile
            if (!response.ok) {
                throw new Error(responseData.detail || 'Error al actualizar el perfil.');
            }

            alert('Perfil actualizado exitosamente!');

            // Update display fields with new data from responseData
            const updatedProfile = responseData.client_profile;
            if (viewNickname) viewNickname.textContent = updatedProfile?.nickname || '-';
            if (viewWhatsapp) viewWhatsapp.textContent = updatedProfile?.whatsapp_number || '-';
            if (viewGender) viewGender.textContent = updatedProfile?.gender || '-';
            // Full name and email are not editable here, client_level is admin-only
            if (viewFullname) viewFullname.textContent = responseData.full_name || '-';
            if (viewEmail) viewEmail.textContent = responseData.email || '-';
            // Refresh points display after profile update, though this form doesn't change points
            if (viewAvailablePoints && responseData.client_profile) {
                const points = responseData.client_profile.available_points;
                viewAvailablePoints.textContent = (points !== null && points !== undefined) ? points.toString() : '0';
            }


        } catch (error) {
            console.error('Error updating profile:', error);
            if (editProfileErrorMessageDiv) {
                editProfileErrorMessageDiv.textContent = error.message;
                editProfileErrorMessageDiv.style.display = 'block';
            } else {
                alert(error.message);
            }
        }
    }

    // Initial data load
    if (isLoggedIn()) { // Check if logged in before trying to load data
        await loadProfileData(); // Await profile data
        loadMyRedemptionRequests(); // Then load redemption requests
    } else {
        // This should be caught by the inline script, but as a fallback.
        // window.location.href = 'login.html';
    }

    // Attach event listener to edit form
    if (editProfileForm) {
        editProfileForm.addEventListener('submit', handleEditProfileFormSubmit);
    }

    // Image management listeners
    if (uploadProfileImageButton) {
        uploadProfileImageButton.addEventListener('click', handleUploadProfileImage);
    }
    if (removeProfileImageButton) {
        removeProfileImageButton.addEventListener('click', handleRemoveProfileImage);
    }

    viewMyPurchaseHistoryButton = document.getElementById('view-my-purchase-history-button');
    if (viewMyPurchaseHistoryButton) {
        viewMyPurchaseHistoryButton.addEventListener('click', () => {
            if (currentLoggedInUserId) {
                window.location.href = `admin_client_history.html?user_id=${currentLoggedInUserId}`;
            } else {
                alert('No se pudo obtener tu ID de usuario. Por favor, recarga la página.');
                console.error("currentLoggedInUserId is not set for purchase history link.");
            }
        });
    }
});

async function handleUploadProfileImage() {
    if (imageUploadErrorMessageDiv) {
        imageUploadErrorMessageDiv.style.display = 'none';
        imageUploadErrorMessageDiv.textContent = '';
    }

    const token = getToken();
    if (!token) {
        alert("Sesión no encontrada. Por favor, inicia sesión de nuevo.");
        logout(); // Ensure logout state is cleared
        window.location.href = 'login.html';
        return;
    }

    if (!profileImageUploadInput || !profileImageUploadInput.files || profileImageUploadInput.files.length === 0) {
        if (imageUploadErrorMessageDiv) {
            imageUploadErrorMessageDiv.textContent = 'Por favor, selecciona un archivo de imagen.';
            imageUploadErrorMessageDiv.style.display = 'block';
        }
        return;
    }

    const imageFile = profileImageUploadInput.files[0];
    const formData = new FormData();
    formData.append('image', imageFile);

    try {
        const response = await fetch(`${API_BASE_URL}/api/me/profile/profile-image`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (response.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }

        const responseData = await response.json();
        if (!response.ok) {
            throw new Error(responseData.detail || 'Error al subir la imagen.');
        }

        if (currentProfileImage && responseData.client_profile?.profile_image_url) {
            currentProfileImage.src = responseData.client_profile.profile_image_url + `?t=${new Date().getTime()}`; // Cache buster
        } else if (currentProfileImage) {
            currentProfileImage.src = 'images/avatar_placeholder.png';
        }
        if (removeProfileImageButton) removeProfileImageButton.style.display = 'inline-block';
        if (profileImageUploadInput) profileImageUploadInput.value = '';
        alert('Imagen de perfil actualizada exitosamente.');

    } catch (error) {
        console.error('Error uploading profile image:', error);
        if (imageUploadErrorMessageDiv) {
            imageUploadErrorMessageDiv.textContent = error.message;
            imageUploadErrorMessageDiv.style.display = 'block';
        } else {
            alert(error.message);
        }
    }
}

async function loadMyRedemptionRequests() {
    if (!myRedemptionsTableBody) return;

    const token = getToken();
    if (!token) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/me/redeem/requests/?limit=20`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || 'Error al cargar tus solicitudes de canje.');
        }

        const requests = await response.json();

        myRedemptionsTableBody.innerHTML = '';
        if (noMyRedemptionsMessage) noMyRedemptionsMessage.style.display = 'none';

        if (requests.length === 0) {
            if (noMyRedemptionsMessage) {
                noMyRedemptionsMessage.textContent = 'No has realizado ninguna solicitud de canje todavía.';
                noMyRedemptionsMessage.style.display = 'block';
            }
        } else {
            requests.forEach(req => {
                const row = myRedemptionsTableBody.insertRow();

                row.insertCell().textContent = req.id;
                row.insertCell().textContent = req.gift_item?.product?.name || 'Regalo no disponible';
                row.insertCell().textContent = req.points_at_request;
                row.insertCell().textContent = new Date(req.requested_at).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' });

                const statusCell = row.insertCell();
                const statusSpan = document.createElement('span');
                statusSpan.classList.add('status-badge');
                const statusKey = req.status;
                statusSpan.classList.add(`status-${statusKey.toLowerCase().replace(/_/g, '-')}`);
                statusSpan.textContent = RedemptionRequestStatusDisplay[statusKey] || statusKey;
                statusSpan.title = `Estado: ${RedemptionRequestStatusDisplay[statusKey] || statusKey}`;
                statusCell.appendChild(statusSpan);

                row.insertCell().textContent = req.admin_notes || '-';
            });
        }

    } catch (error) {
        console.error('Error loading my redemption requests:', error);
        if (noMyRedemptionsMessage) {
            noMyRedemptionsMessage.textContent = `Error: ${error.message}`;
            noMyRedemptionsMessage.style.display = 'block';
        } else if (myRedemptionsTableBody) {
             myRedemptionsTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:red;">Error: ${error.message}</td></tr>`;
        }
    }
}

async function handleRemoveProfileImage() {
    if (imageUploadErrorMessageDiv) {
        imageUploadErrorMessageDiv.style.display = 'none';
        imageUploadErrorMessageDiv.textContent = '';
    }

    if (!confirm('¿Estás seguro de que deseas eliminar tu imagen de perfil?')) {
        return;
    }

    const token = getToken();
    if (!token) {
        alert("Sesión no encontrada. Por favor, inicia sesión de nuevo.");
        logout();
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/me/profile/profile-image`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }

        const responseData = await response.json();
        if (!response.ok) {
            throw new Error(responseData.detail || 'Error al eliminar la imagen.');
        }

        if (currentProfileImage) {
            currentProfileImage.src = 'images/avatar_placeholder.png';
        }
        if (removeProfileImageButton) removeProfileImageButton.style.display = 'none';
        alert('Imagen de perfil eliminada exitosamente.');

    } catch (error) {
        console.error('Error deleting profile image:', error);
        if (imageUploadErrorMessageDiv) {
            imageUploadErrorMessageDiv.textContent = error.message;
            imageUploadErrorMessageDiv.style.display = 'block';
        } else {
            alert(error.message);
        }
    }
}
