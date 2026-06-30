/**
 * Cart Operations Helper
 * Handles adding items to cart with live badge updates
 */

// Add to cart with real-time badge update
async function addToCartWithUpdate(articleId, buttonElement) {
    try {
        // Disable button during request
        if (buttonElement) {
            buttonElement.disabled = true;
            const originalHTML = buttonElement.innerHTML;
            buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Adding...';
        }

        const response = await fetch(`/add_to_cart/${articleId}`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            // Update cart badge
            updateCartBadge(data.cart_count);

            // Show success toast
            showToast('success', data.message || 'Item added to cart!');

            // Restore button
            if (buttonElement) {
                buttonElement.innerHTML = '<i class="fas fa-check me-2"></i>Added!';
                buttonElement.classList.add('btn-success');
                setTimeout(() => {
                    buttonElement.innerHTML = '<i class="fas fa-cart-plus me-2"></i>Add to Cart';
                    buttonElement.classList.remove('btn-success');
                    buttonElement.disabled = false;
                }, 1500);
            }
        } else {
            throw new Error(data.message || 'Failed to add item');
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        showToast('error', 'Failed to add item to cart');
        
        if (buttonElement) {
            buttonElement.innerHTML = '<i class="fas fa-cart-plus me-2"></i>Add to Cart';
            buttonElement.disabled = false;
        }
    }
}

// Update cart badge with animation
function updateCartBadge(count) {
    const badge = document.getElementById('cartBadge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'flex';
            badge.classList.add('updated');
            setTimeout(() => badge.classList.remove('updated'), 400);
        } else {
            badge.style.display = 'none';
        }
    }

    // Dispatch custom event for other components
    window.dispatchEvent(new CustomEvent('cartUpdated', { 
        detail: { count: count } 
    }));
}

// Show toast notification
function showToast(type, message) {
    // Create toast container if it doesn't exist
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
        document.body.appendChild(container);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    toast.style.cssText = 'min-width: 300px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.appendChild(toast);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 150);
    }, 3000);
}

// Initialize cart count on page load
document.addEventListener('DOMContentLoaded', function() {
    // Update cart count
    const cartBadge = document.getElementById('cartBadge');
    if (cartBadge) {
        fetch('/api/cart/count')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.count > 0) {
                    updateCartBadge(data.count);
                }
            })
            .catch(err => console.log('Cart count fetch failed:', err));
    }

    // Convert all cart forms to AJAX
    document.querySelectorAll('form[action*="/add_to_cart/"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const articleId = this.action.match(/\/add_to_cart\/(\d+)/)[1];
            const button = this.querySelector('button[type="submit"]');
            addToCartWithUpdate(articleId, button);
        });
    });
});