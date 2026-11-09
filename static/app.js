// SPDX-FileCopyrightText: 2026 Siddhant Tiwari
// SPDX-License-Identifier: AGPL-3.0-only
// RIFT is distributed without warranty. See LICENSE and COPYRIGHT.md.

/**
 * Frontend Application Logic for IoT Anonymous Feedback System
 * Shared utilities and API communication functions.
 */

// API Base URL (relative to current domain)
const API_BASE_URL = '';

/**
 * Fetch data from the API with error handling
 * @param {string} endpoint - API endpoint (e.g., '/topics/latest')
 * @param {object} options - Fetch options
 * @returns {Promise<any>} - JSON response data
 */
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const defaultOptions = {
        headers: options.body instanceof FormData ? {} : {
            'Content-Type': 'application/json',
        },
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    try {
        const response = await fetch(url, mergedOptions);
        
        // Check if response is ok
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new APIError(
                errorData.error || `HTTP ${response.status}: ${response.statusText}`,
                response.status,
                errorData
            );
        }

        // Handle empty responses
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }
        
        return await response.text();
        
    } catch (error) {
        // Re-throw APIError instances
        if (error instanceof APIError) {
            throw error;
        }
        
        // Wrap other errors
        throw new APIError(
            error.message || 'Network error occurred',
            0,
            { originalError: error }
        );
    }
}

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(message, status, data = {}) {
        super(message);
        this.name = 'APIError';
        this.status = status;
        this.data = data;
    }
}

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
    if (!text) return '';
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format a timestamp to a readable date string
 * @param {string} timestamp - ISO timestamp string
 * @returns {string} - Formatted date string
 */
function formatDate(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format a number with specified decimal places
 * @param {number} value - Number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} - Formatted number string
 */
function formatNumber(value, decimals = 1) {
    if (value === null || value === undefined) return 'N/A';
    return Number(value).toFixed(decimals);
}

/**
 * Show a toast notification
 * @param {string} message - Notification message
 * @param {string} type - 'success', 'error', 'warning', 'info'
 */
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToast = document.querySelector('.toast-notification');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast-notification toast-${type}`;
    toast.innerHTML = `
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    // Add toast styles if not present
    if (!document.querySelector('#toast-styles')) {
        const styles = document.createElement('style');
        styles.id = 'toast-styles';
        styles.textContent = `
            .toast-notification {
                position: fixed;
                bottom: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                gap: 15px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                z-index: 10000;
                animation: slideIn 0.3s ease-out;
                max-width: 400px;
            }
            
            .toast-success {
                background: #10b981;
                color: white;
            }
            
            .toast-error {
                background: #ef4444;
                color: white;
            }
            
            .toast-warning {
                background: #f59e0b;
                color: white;
            }
            
            .toast-info {
                background: #3b82f6;
                color: white;
            }
            
            .toast-message {
                flex: 1;
            }
            
            .toast-close {
                background: none;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
                opacity: 0.7;
                line-height: 1;
            }
            
            .toast-close:hover {
                opacity: 1;
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(styles);
    }

    document.body.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

/**
 * Debounce function to limit execution rate
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Check if the API is healthy
 * @returns {Promise<object>} - Health status object
 */
async function checkHealth() {
    try {
        return await fetchAPI('/health');
    } catch (error) {
        return {
            status: 'unhealthy',
            error: error.message
        };
    }
}

/**
 * Upload an audio file to the server
 * @param {File} file - Audio file to upload
 * @param {Function} onProgress - Progress callback (optional)
 * @returns {Promise<object>} - Upload response
 */
async function uploadAudio(file, onProgress = null) {
    const formData = new FormData();
    formData.append('file', file);

    const options = {
        method: 'POST',
        body: formData,
        headers: {} // Remove Content-Type to let browser set it with boundary
    };

    // Can't track progress with standard fetch, but keeping the callback signature
    if (onProgress) {
        onProgress(0);
    }

    try {
        const result = await fetchAPI('/upload-audio', options);
        
        if (onProgress) {
            onProgress(100);
        }
        
        return result;
    } catch (error) {
        if (onProgress) {
            onProgress(-1); // Indicate error
        }
        throw error;
    }
}

/**
 * Validate file type
 * @param {File} file - File to validate
 * @param {string[]} allowedTypes - Array of allowed MIME types or extensions
 * @returns {boolean} - True if valid
 */
function validateFileType(file, allowedTypes) {
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    const mimeType = file.type.toLowerCase();
    
    return allowedTypes.some(type => {
        if (type.startsWith('.')) {
            return extension === type.toLowerCase();
        }
        return mimeType === type.toLowerCase() || mimeType.startsWith(type.toLowerCase());
    });
}

/**
 * Format file size to human readable format
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted size string
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Create a simple loading overlay
 * @param {boolean} show - Show or hide the overlay
 * @param {string} message - Loading message
 */
function showLoadingOverlay(show = true, message = 'Loading...') {
    let overlay = document.querySelector('.loading-overlay');
    
    if (show) {
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <p class="loading-message">${escapeHtml(message)}</p>
                </div>
            `;
            document.body.appendChild(overlay);

            // Add styles if not present
            if (!document.querySelector('#loading-overlay-styles')) {
                const styles = document.createElement('style');
                styles.id = 'loading-overlay-styles';
                styles.textContent = `
                    .loading-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.7);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 99999;
                    }
                    
                    .loading-content {
                        text-align: center;
                        color: white;
                    }
                    
                    .loading-overlay .loading-spinner {
                        width: 50px;
                        height: 50px;
                        border: 4px solid rgba(255, 255, 255, 0.3);
                        border-top-color: white;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 15px;
                    }
                    
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `;
                document.head.appendChild(styles);
            }
        }
        
        overlay.querySelector('.loading-message').textContent = message;
    } else {
        if (overlay) {
            overlay.remove();
        }
    }
}

// Export utilities for use in other scripts
window.FeedbackSystem = {
    fetchAPI,
    APIError,
    escapeHtml,
    formatDate,
    formatNumber,
    showToast,
    debounce,
    checkHealth,
    uploadAudio,
    validateFileType,
    formatFileSize,
    showLoadingOverlay
};
