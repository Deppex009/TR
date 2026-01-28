from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
import os
from threading import Thread
import asyncio

app = Flask(__name__)
app.secret_key = 'depex_dashboard_secret_key_2026'

CONFIG_FILE = "poem_config.json"

def load_config():
    """Load configuration from JSON file"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
    
    return {
        "poem_channel": None,
        "embed_color": "0x9B59B6",
        "show_image": True,
        "image_url": "",
        "auto_react": False,
        "react_emojis": ["❤️", "🔥"]
    }

def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

@app.route('/')
def index():
    """Main dashboard page"""
    config = load_config()
    return render_template('index.html', config=config)

@app.after_request
def add_header(response):
    """Add headers to prevent caching"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    config = load_config()
    return jsonify(config)

@app.route('/api/config/update', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        data = request.json
        config = load_config()
        
        # Update config with new data
        for key, value in data.items():
            config[key] = value
        
        if save_config(config):
            return jsonify({"success": True, "message": "Configuration updated successfully!"})
        else:
            return jsonify({"success": False, "message": "Failed to save configuration"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/config/poem_channel', methods=['POST'])
def set_poem_channel():
    """Set poem channel"""
    try:
        data = request.json
        channel_id = data.get('channel_id')
        
        config = load_config()
        config['poem_channel'] = int(channel_id) if channel_id else None
        
        if save_config(config):
            return jsonify({"success": True, "message": "Poem channel updated!"})
        return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/config/color', methods=['POST'])
def set_color():
    """Set embed color"""
    try:
        data = request.json
        color = data.get('color')
        
        config = load_config()
        config['embed_color'] = color
        
        if save_config(config):
            return jsonify({"success": True, "message": "Color updated!"})
        return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/config/image', methods=['POST'])
def set_image():
    """Set image configuration"""
    try:
        data = request.json
        
        config = load_config()
        config['show_image'] = data.get('show_image', config.get('show_image', True))
        config['image_url'] = data.get('image_url', config.get('image_url', ''))
        
        if save_config(config):
            return jsonify({"success": True, "message": "Image settings updated!"})
        return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/config/reactions', methods=['POST'])
def set_reactions():
    """Set auto reactions"""
    try:
        data = request.json
        
        config = load_config()
        config['auto_react'] = data.get('auto_react', False)
        config['react_emojis'] = data.get('react_emojis', ["❤️", "🔥"])
        
        if save_config(config):
            return jsonify({"success": True, "message": "Reactions updated!"})
        return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/config/ticket', methods=['POST'])
def set_ticket():
    """Set ticket configuration"""
    try:
        data = request.json
        
        config = load_config()
        if 'tickets' not in config:
            config['tickets'] = {}
        
        # Update ticket settings
        for key, value in data.items():
            if key == 'category_id':
                config['tickets']['category_id'] = int(value) if value else None
            elif key == 'log_channel_id':
                config['tickets']['log_channel_id'] = int(value) if value else None
            elif key == 'admin_role_id':
                config['tickets']['admin_role_id'] = int(value) if value else None
            else:
                config['tickets'][key] = value
        
        if save_config(config):
            return jsonify({"success": True, "message": "Ticket settings updated!"})
        return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🎨 DEPEX DASHBOARD - Bot Control Panel")
    print("=" * 60)
    print("✨ Dashboard is starting...")
    print("🌐 Access at: http://localhost:5000")
    print("👤 Created by: Depex")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
