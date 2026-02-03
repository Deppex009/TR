// Toast notification function
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = toast.querySelector('.toast-message');
    const toastIcon = toast.querySelector('.toast-icon');
    
    toastMessage.textContent = message;
    
    if (type === 'error') {
        toast.classList.add('error');
        toastIcon.className = 'toast-icon fas fa-exclamation-circle';
    } else {
        toast.classList.remove('error');
        toastIcon.className = 'toast-icon fas fa-check-circle';
    }
    
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Color picker sync
document.addEventListener('DOMContentLoaded', () => {
    const colorPicker = document.getElementById('color-picker');
    const colorInput = document.getElementById('embed-color');
    const colorPreview = document.getElementById('color-preview');
    
    // Convert various color formats to hex
    function normalizeColor(color) {
        if (!color) return '#9B59B6';
        
        color = color.trim().toLowerCase();
        
        // If it's a hex with #
        if (color.startsWith('#')) {
            return color;
        }
        
        // If it's 0x format
        if (color.startsWith('0x')) {
            return '#' + color.substring(2);
        }
        
        // If it's just 6 hex digits
        if (color.length === 6 && /^[0-9a-f]{6}$/i.test(color)) {
            return '#' + color;
        }
        
        // Default
        return '#9B59B6';
    }
    
    if (colorPicker && colorInput && colorPreview) {
        // Set initial color
        const initialColor = normalizeColor(colorInput.value);
        colorPicker.value = initialColor;
        colorPreview.style.background = initialColor;
        
        // Color picker change
        colorPicker.addEventListener('input', (e) => {
            const color = e.target.value;
            colorInput.value = color;
            colorPreview.style.background = color;
        });
        
        // Text input change
        colorInput.addEventListener('input', (e) => {
            const color = normalizeColor(e.target.value);
            colorPicker.value = color;
            colorPreview.style.background = color;
        });
    }
});

// Update Poem Channel
async function updatePoemChannel() {
    const channelId = document.getElementById('poem-channel').value.trim();
    
    if (!channelId) {
        showToast('⚠️ Please enter a channel ID', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/config/poem_channel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ channel_id: channelId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ Poem channel updated successfully!', 'success');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast('❌ Error: ' + error.message, 'error');
        console.error('Error:', error);
    }
}

// Update Color
async function updateColor() {
    const color = document.getElementById('embed-color').value;
    
    try {
        const response = await fetch('/api/config/color', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ color: color })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('🎨 Color updated successfully!');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast('❌ Error updating color', 'error');
        console.error('Error:', error);
    }
}

// Update Image Settings
async function updateImage() {
    const showImage = document.getElementById('show-image').checked;
    const imageUrl = document.getElementById('image-url').value;
    
    try {
        const response = await fetch('/api/config/image', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                show_image: showImage,
                image_url: imageUrl 
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('🖼️ Image settings updated successfully!');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast('❌ Error updating image settings', 'error');
        console.error('Error:', error);
    }
}

// Update Reactions
async function updateReactions() {
    const autoReact = document.getElementById('auto-react').checked;
    const emojis = document.getElementById('react-emojis').value
        .split(',')
        .map(e => e.trim())
        .filter(e => e.length > 0);
    
    try {
        const response = await fetch('/api/config/reactions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                auto_react: autoReact,
                react_emojis: emojis 
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('❤️ Reactions updated successfully!');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast('❌ Error updating reactions', 'error');
        console.error('Error:', error);
    }.trim();
    const logChannelId = document.getElementById('ticket-log').value.trim();
    const adminRoleId = document.getElementById('ticket-admin').value.trim();
    
    try {
        const response = await fetch('/api/config/ticket', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                category_id: categoryId || null,
                log_channel_id: logChannelId || null,
                admin_role_id: adminRoleId || null
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('🎫 Ticket settings updated successfully!', 'success');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast('❌ Error: ' + error.messageccessfully!');
        } else {
            showToast('❌ ' + data.message, 'error');
        }
    } catch (error) {
        showToast('❌ Error updating ticket settings', 'error');
        console.error('Error:', error);
    }
}

// Add smooth scroll behavior
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + S to save all settings
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        showToast('💾 Use individual save buttons to update settings', 'error');
    }
});

// Add loading animation to buttons
document.querySelectorAll('.btn').forEach(button => {
    button.addEventListener('click', function() {
        this.style.pointerEvents = 'none';
        setTimeout(() => {
            this.style.pointerEvents = 'auto';
        }, 1000);
    });
});
