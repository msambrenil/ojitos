const themeToggleButton = document.getElementById('theme-toggle-button');
const bodyElement = document.body;

// Function to apply the saved theme on load
function applyInitialTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        bodyElement.classList.add('dark-mode');
        // Optionally update button text/icon here if implemented
        // e.g., themeToggleButton.textContent = 'Light Mode';
    } else {
        bodyElement.classList.remove('dark-mode'); // Ensure it's light if not dark or no preference
        // Optionally update button text/icon here
        // e.g., themeToggleButton.textContent = 'Dark Mode';
    }
}

// Theme toggle button event listener
if (themeToggleButton) {
    themeToggleButton.addEventListener('click', () => {
        bodyElement.classList.toggle('dark-mode');
        if (bodyElement.classList.contains('dark-mode')) {
            localStorage.setItem('theme', 'dark');
            // Optionally update button text/icon
            // e.g., themeToggleButton.textContent = 'Light Mode';
        } else {
            localStorage.setItem('theme', 'light');
            // Optionally update button text/icon
            // e.g., themeToggleButton.textContent = 'Dark Mode';
        }
    });
}

// --- Existing dashboard data fetching logic ---
async function fetchCardData(endpointUrl, elementId) {
    try {
        const response = await fetch(endpointUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        const element = document.getElementById(elementId);
        if (element) {
            if (data && typeof data.value !== 'undefined') {
                element.textContent = data.value;
            } else {
                console.error(`Error: 'value' property not found in data from ${endpointUrl}`, data);
                element.textContent = '-'; // Fallback
            }
        } else {
            console.error(`Error: Element with ID '${elementId}' not found.`);
        }
    } catch (error) {
        console.error(`Error fetching data for ${elementId} from ${endpointUrl}:`, error);
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = 'Error'; // Display error in card
        }
    }
}

function loadDashboardData() {
    fetchCardData('/api/dashboard/ventas-entregadas', 'value-ventas-entregadas');
    fetchCardData('/api/dashboard/a-entregar', 'value-a-entregar');
    fetchCardData('/api/dashboard/por-armar', 'value-por-armar');
    fetchCardData('/api/dashboard/cobradas', 'value-cobradas');
    fetchCardData('/api/dashboard/a-cobrar', 'value-a-cobrar');
}

document.addEventListener('DOMContentLoaded', () => {
    applyInitialTheme(); // Apply theme as soon as DOM is ready
    loadDashboardData(); // Then load dashboard data
});
