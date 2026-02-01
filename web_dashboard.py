from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import requests
from functools import wraps
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = 'depex_super_secret_key_2026'

CONFIG_FILE = "poem_config.json"

# Discord OAuth2 Settings
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1460760802138128567")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "VqoJHnxc2d-xdZbns5HTI_MgOGEtvSdn")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

def load_config():
    """Load multi-server configuration"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
    
    return {
        "servers": {}  # Format: {"server_id": {...settings...}}
    }

def save_config(config):
    """Save multi-server configuration"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get_server_config(server_id):
    """Get config for specific server"""
    config = load_config()
    if "servers" not in config:
        config["servers"] = {}
    
    if server_id not in config["servers"]:
        config["servers"][server_id] = {
            "poem_channel": None,
            "embed_color": "#9B59B6",
            "show_image": True,
            "image_url": "",
            "auto_react": False,
            "react_emojis": ["❤️", "🔥"],
            "tickets": {},
            "giveaway": {
                "channel_id": None,
                "duration": "1h",
                "winners": 1,
                "emoji": "🎉",
                "color": "#5865F2",
                "image_url": ""
            }
        }
        save_config(config)

    server_cfg = config["servers"][server_id]
    if "giveaway" not in server_cfg:
        server_cfg["giveaway"] = {
            "channel_id": None,
            "duration": "1h",
            "winners": 1,
            "emoji": "🎉",
            "color": "#5865F2",
            "image_url": ""
        }
        save_config(config)

    return server_cfg

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def login():
    """Login page"""
    if 'user' in session:
        return redirect(url_for('select_server'))
    return render_template('login.html')

@app.route('/auth')
def auth():
    """Redirect to Discord OAuth"""
    discord_auth_url = f"{DISCORD_API_BASE}/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds"
    return redirect(discord_auth_url)

@app.route('/callback')
def callback():
    """OAuth callback - Real Discord authentication"""
    code = request.args.get('code')
    
    if not code:
        return redirect(url_for('login'))
    
    try:
        # Exchange code for access token
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        r = requests.post(f'{DISCORD_API_BASE}/oauth2/token', data=data, headers=headers)
        r.raise_for_status()
        token_data = r.json()
        
        access_token = token_data['access_token']
        
        # Get user info
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(f'{DISCORD_API_BASE}/users/@me', headers=headers)
        user_response.raise_for_status()
        user = user_response.json()
        
        # Get user's guilds
        guilds_response = requests.get(f'{DISCORD_API_BASE}/users/@me/guilds', headers=headers)
        guilds_response.raise_for_status()
        guilds = guilds_response.json()
        
        # Get bot's guilds to filter (optional - show all if bot token fails)
        user_guilds = []
        try:
            if DISCORD_BOT_TOKEN:
                bot_headers = {'Authorization': f'Bot {DISCORD_BOT_TOKEN}'}
                bot_guilds_response = requests.get(f'{DISCORD_API_BASE}/users/@me/guilds', headers=bot_headers)
                bot_guilds_response.raise_for_status()
                bot_guilds = bot_guilds_response.json()
                bot_guild_ids = {g['id'] for g in bot_guilds}
                
                # Filter guilds where user has MANAGE_GUILD permission and bot is present
                user_guilds = [
                    g for g in guilds 
                    if (int(g['permissions']) & 0x20) == 0x20 and g['id'] in bot_guild_ids
                ]
        except Exception as bot_err:
            print(f"Bot guild fetch failed: {bot_err}, showing all user guilds with manage permission")
        
        # If bot check failed or no guilds found, show all guilds with manage permission
        if not user_guilds:
            user_guilds = [
                g for g in guilds 
                if (int(g['permissions']) & 0x20) == 0x20
            ]
        
        session['user'] = {
            'id': user['id'],
            'username': user['username'],
            'discriminator': user.get('discriminator', '0'),
            'avatar': user.get('avatar')
        }
        session['guilds'] = user_guilds
        session['access_token'] = access_token
        
        return redirect(url_for('select_server'))
        
    except Exception as e:
        logger.error(f"OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return f"<h1>OAuth Error</h1><pre>{str(e)}</pre><p><a href='/'>Go back</a></p>"

@app.route('/select-server')
@login_required
def select_server():
    """Server selection page"""
    return render_template('select_server.html', guilds=session.get('guilds', []))

@app.route('/dashboard/<server_id>')
@login_required
def dashboard(server_id):
    """Main dashboard for specific server"""
    server_config = get_server_config(server_id)
    
    # Get server name from session
    server_name = "Unknown Server"
    for guild in session.get('guilds', []):
        if guild['id'] == server_id:
            server_name = guild['name']
            break
    
    return render_template('dashboard_new.html', 
                         config=server_config, 
                         server_id=server_id,
                         server_name=server_name)

@app.route('/api/config/<server_id>', methods=['GET'])
@login_required
def get_config(server_id):
    """Get server configuration"""
    config = get_server_config(server_id)
    return jsonify(config)

@app.route('/api/config/<server_id>/update', methods=['POST'])
@login_required
def update_server_config(server_id):
    """Update server configuration"""
    try:
        data = request.json
        config = load_config()
        
        if "servers" not in config:
            config["servers"] = {}
        
        if server_id not in config["servers"]:
            config["servers"][server_id] = {}
        
        # Update specific settings
        for key, value in data.items():
            config["servers"][server_id][key] = value
        
        if save_config(config):
            return jsonify({"success": True, "message": "Settings updated!"})
        return jsonify({"success": False, "message": "Failed to save"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('login'))

@app.after_request
def add_header(response):
    """Prevent caching"""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    print("=" * 60)
    print("🎨 DEPEX MULTI-SERVER DASHBOARD")
    print("=" * 60)
    print("✨ Dashboard starting...")
    print("🌐 Access at: http://localhost:5000")
    print("👤 Created by: Depex")
    print("🔥 Features: Multi-Server Support + OAuth Login")
    print("=" * 60)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
