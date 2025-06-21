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

const redemptionsTableBody = document.getElementById('redemptions-table-body');
const noRedemptionsMessage = document.getElementById('no-redemptions-message');
// Filter elements
const filterUserIdInput = document.getElementById('filter-redemption-userid');
const filterStatusSelect = document.getElementById('filter-redemption-status');
const filterDateFromInput = document.getElementById('filter-redemption-date-from');
const filterDateToInput = document.getElementById('filter-redemption-date-to');
const applyRedemptionFiltersButton = document.getElementById('apply-redemption-filters-button');
const clearRedemptionFiltersButton = document.getElementById('clear-redemption-filters-button');

// Modal elements
const actionNotesModal = document.getElementById('redemption-action-notes-modal');
const actionNotesModalCloseButton = document.getElementById('redemption-notes-modal-close-button');
const actionNotesModalCancelButton = document.getElementById('redemption-notes-modal-cancel-button');

// Form elements within the modal
const redemptionNotesForm = document.getElementById('redemption-notes-form');
const actionRequestIdInput = document.getElementById('action-request-id');
const actionTypeInput = document.getElementById('action-type');
const formAdminNotesTextarea = document.getElementById('form-admin-notes');
const confirmActionButton = document.getElementById('confirm-action-button');
const redemptionNotesErrorMessageDiv = document.getElementById('redemption-notes-error-message');


// Global display message (e.g., after modal closes)
function displayAdminRedemptionMessage(message, isError = false) {
    alert(message); // Simple alert for now
    if (isError) {
        console.error("Admin Redemptions Global:", message);
    } else {
        console.log("Admin Redemptions Global:", message);
    }
}

// Helper to display messages within a specific div (e.g., inside modal)
function displayMessage(element, message, isError = false) {
    if (element) {
        element.textContent = message;
        element.className = isError ? 'error-message' : 'success-message'; // Ensure these classes are styled
        element.style.display = 'block';
    } else { // Fallback if specific element not found
        displayAdminRedemptionMessage(message, isError);
    }
}


function populateStatusFilterDropdown() {
    if (!filterStatusSelect) return;
    filterStatusSelect.innerHTML = '<option value="">Todos los Estados</option>';
    for (const key in RedemptionRequestStatusEnum) {
        const option = document.createElement('option');
        option.value = RedemptionRequestStatusEnum[key];
        option.textContent = RedemptionRequestStatusDisplay[RedemptionRequestStatusEnum[key]] || RedemptionRequestStatusEnum[key];
        filterStatusSelect.appendChild(option);
    }
}

async function loadRedemptionRequests(filters = {}) {
    const token = getToken();
    if (!isLoggedIn() || !token || !getCurrentUserInfo()?.is_superuser) {
        // displayAdminRedemptionMessage("Acceso denegado.", true); // Already handled by DOMContentLoaded check typically
        if (redemptionsTableBody) redemptionsTableBody.innerHTML = '<tr><td colspan="8">Acceso denegado.</td></tr>';
        return;
    }

    const params = new URLSearchParams();
    if (filters.userId) params.append('user_id_filter', filters.userId);
    if (filters.status) params.append('status_filter', filters.status);
    if (filters.dateFrom) params.append('date_from_filter', filters.dateFrom);
    if (filters.dateTo) params.append('date_to_filter', filters.dateTo);
    params.append('skip', filters.skip || '0');
    params.append('limit', filters.limit || '50');

    const queryString = params.toString();
    const apiUrl = `${API_BASE_URL}/api/admin/redemption-requests/${queryString ? '?' + queryString : ''}`;

    try {
        const response = await fetch(apiUrl, { headers: { 'Authorization': `Bearer ${token}` } });
        if (response.status === 401 || response.status === 403) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        if (!response.ok) throw new Error(`Error al cargar solicitudes: ${response.status} ${response.statusText}`);

        const requests = await response.json();
        if (redemptionsTableBody) redemptionsTableBody.innerHTML = '';

        if (requests.length === 0) {
            if (noRedemptionsMessage) noRedemptionsMessage.style.display = 'block';
        } else {
            if (noRedemptionsMessage) noRedemptionsMessage.style.display = 'none';
            requests.forEach(req => {
                const row = redemptionsTableBody.insertRow();
                row.dataset.requestId = req.id;

                row.insertCell().textContent = req.id;
                const userFullName = req.user?.client_profile?.full_name || req.user?.email || 'N/A';
                row.insertCell().textContent = `${userFullName} (ID: ${req.user_id})`;
                row.insertCell().textContent = req.gift_item?.product?.name || 'N/A';
                row.insertCell().textContent = req.points_at_request;
                row.insertCell().textContent = new Date(req.requested_at).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short'});

                const statusCell = row.insertCell();
                const statusSpan = document.createElement('span');
                statusSpan.classList.add('status-badge');
                const statusKey = req.status;
                statusSpan.classList.add(`status-${statusKey.toLowerCase().replace(/_/g, '-')}`);
                statusSpan.textContent = RedemptionRequestStatusDisplay[statusKey] || statusKey;
                statusSpan.title = `Estado: ${RedemptionRequestStatusDisplay[statusKey] || statusKey}`; // Tooltip
                statusCell.appendChild(statusSpan);

                row.insertCell().textContent = req.admin_notes || '-';

                const actionsCell = row.insertCell();
                actionsCell.innerHTML = '';
                if (req.status === RedemptionRequestStatusEnum.PENDIENTE_APROBACION) {
                    actionsCell.innerHTML += `<button class="approve-request-button mdc-button mdc-button--outlined" data-request-id="${req.id}">Aprobar</button> `;
                    actionsCell.innerHTML += `<button class="reject-request-button mdc-button mdc-button--outlined" data-request-id="${req.id}">Rechazar</button>`;
                } else if (req.status === RedemptionRequestStatusEnum.APROBADO_POR_ENTREGAR) {
                    actionsCell.innerHTML += `<button class="deliver-request-button mdc-button mdc-button--outlined" data-request-id="${req.id}">Marcar Entregado</button>`;
                }
            });
        }
    } catch (error) {
        console.error("Error loading redemption requests:", error);
        if (redemptionsTableBody) redemptionsTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:red;">Error al cargar: ${error.message}</td></tr>`;
        if (noRedemptionsMessage) noRedemptionsMessage.style.display = 'none';
    }
}

function openActionNotesModal(actionType, requestId, title) {
    const modalTitleEl = document.getElementById('redemption-notes-modal-title');

    if(modalTitleEl) modalTitleEl.textContent = title;
    if(actionRequestIdInput) actionRequestIdInput.value = requestId;
    if(actionTypeInput) actionTypeInput.value = actionType;
    if(formAdminNotesTextarea) formAdminNotesTextarea.value = '';
    if(redemptionNotesErrorMessageDiv) {
        redemptionNotesErrorMessageDiv.textContent = '';
        redemptionNotesErrorMessageDiv.style.display = 'none';
    }

    if(confirmActionButton) {
        let buttonText = "Confirmar";
        if (actionType === 'approve') buttonText = "Confirmar Aprobación";
        else if (actionType === 'reject') buttonText = "Confirmar Rechazo";
        else if (actionType === 'deliver') buttonText = "Confirmar Entrega";
        confirmActionButton.textContent = buttonText;
    }

    if (actionNotesModal) actionNotesModal.style.display = 'block';
}

function closeActionNotesModal() {
    if (actionNotesModal) actionNotesModal.style.display = 'none';
    if (redemptionNotesForm) redemptionNotesForm.reset(); // Resets all form fields
    if(redemptionNotesErrorMessageDiv) {
        redemptionNotesErrorMessageDiv.textContent = '';
        redemptionNotesErrorMessageDiv.style.display = 'none';
    }
}

async function handleConfirmRedemptionAction(event) {
    event.preventDefault();
    if (!actionRequestIdInput || !actionTypeInput || !formAdminNotesTextarea || !redemptionNotesErrorMessageDiv) {
        console.error("Modal form elements not found for action submission.");
        return;
    }
    const requestId = actionRequestIdInput.value;
    const actionType = actionTypeInput.value;
    const adminNotes = formAdminNotesTextarea.value.trim();

    if (!requestId || !actionType) {
        displayMessage(redemptionNotesErrorMessageDiv, "Error: ID de solicitud o tipo de acción no definido.", true);
        return;
    }

    const token = getToken();
    const currentUser = getCurrentUserInfo();
    if (!isLoggedIn() || !token || !currentUser?.is_superuser) {
        displayMessage(redemptionNotesErrorMessageDiv, "Acceso denegado. Se requieren permisos de administrador.", true);
        setTimeout(() => { logout(); window.location.href = 'login.html'; }, 2000);
        return;
    }

    let apiUrl = `${API_BASE_URL}/api/admin/redemption-requests/${requestId}/${actionType}`;
    const bodyPayload = { admin_notes: adminNotes || null };

    try {
        confirmActionButton.disabled = true;
        confirmActionButton.textContent = "Procesando...";

        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(bodyPayload)
        });

        const resultData = await response.json();

        if (!response.ok) { // Handles HTTP errors like 400, 404, 422 etc.
             if (response.status === 401 || response.status === 403) { // Specific check for auth errors
                logout(); window.location.href = 'login.html'; return;
            }
            throw new Error(resultData.detail || `Error al procesar la acción '${actionType}'. Estado: ${response.status}`);
        }

        displayAdminRedemptionMessage(`Solicitud #${requestId} procesada como '${actionType}' exitosamente.`, false);
        closeActionNotesModal();
        loadRedemptionRequests();

    } catch (error) {
        console.error(`Error during redemption action '${actionType}':`, error);
        displayMessage(redemptionNotesErrorMessageDiv, error.message, true);
    } finally {
        if(confirmActionButton) {
            confirmActionButton.disabled = false;
            // Restore original button text (or rely on next openActionNotesModal call)
            let buttonText = "Confirmar";
            if (actionType === 'approve') buttonText = "Confirmar Aprobación";
            else if (actionType === 'reject') buttonText = "Confirmar Rechazo";
            else if (actionType === 'deliver') buttonText = "Confirmar Entrega";
            confirmActionButton.textContent = buttonText;
        }
    }
}


document.addEventListener('DOMContentLoaded', () => {
    const userInfo = getCurrentUserInfo();
    if (!isLoggedIn() || !userInfo || !userInfo.is_superuser) {
        return;
    }

    populateStatusFilterDropdown();
    loadRedemptionRequests();

    if (applyRedemptionFiltersButton) {
        applyRedemptionFiltersButton.addEventListener('click', () => {
            const filters = {
                userId: filterUserIdInput.value.trim(),
                status: filterStatusSelect.value,
                dateFrom: filterDateFromInput.value,
                dateTo: filterDateToInput.value
            };
            for (const key in filters) { if (!filters[key]) delete filters[key]; }
            loadRedemptionRequests(filters);
        });
    }

    if (clearRedemptionFiltersButton) {
        clearRedemptionFiltersButton.addEventListener('click', () => {
            if (filterUserIdInput) filterUserIdInput.value = '';
            if (filterStatusSelect) filterStatusSelect.value = '';
            if (filterDateFromInput) filterDateFromInput.value = '';
            if (filterDateToInput) filterDateToInput.value = '';
            loadRedemptionRequests();
        });
    }

    if(actionNotesModalCloseButton) actionNotesModalCloseButton.addEventListener('click', closeActionNotesModal);
    if(actionNotesModalCancelButton) actionNotesModalCancelButton.addEventListener('click', closeActionNotesModal);

    if (redemptionNotesForm) {
        redemptionNotesForm.addEventListener('submit', handleConfirmRedemptionAction);
    }

    if (redemptionsTableBody) {
        redemptionsTableBody.addEventListener('click', (event) => {
            const targetButton = event.target.closest('button');
            if (!targetButton) return;

            const requestId = targetButton.dataset.requestId;
            if (!requestId) return;

            if (targetButton.classList.contains('approve-request-button')) {
                openActionNotesModal('approve', requestId, `Aprobar Solicitud #${requestId}`);
            } else if (targetButton.classList.contains('reject-request-button')) {
                openActionNotesModal('reject', requestId, `Rechazar Solicitud #${requestId}`);
            } else if (targetButton.classList.contains('deliver-request-button')) {
                openActionNotesModal('deliver', requestId, `Marcar como Entregada Solicitud #${requestId}`);
            }
        });
    }
});
