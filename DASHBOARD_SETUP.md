# Depex Dashboard - Setup Instructions

## 🔧 Discord OAuth Setup

1. **Go to Discord Developer Portal:**
   - https://discord.com/developers/applications
   - Select your bot application

2. **Setup OAuth2:**
   - Go to OAuth2 section
   - Add Redirects: 
     - `http://localhost:5000/callback` (for local testing)
     - `https://your-domain.com/callback` (for production)

3. **Get Your Credentials:**
   - Copy your **Client ID**
   - Copy your **Client Secret**
   - Copy your **Bot Token** from the Bot section

4. **Set Environment Variables:**
   Create a `.env` file in the project root:
   ```
   DISCORD_CLIENT_ID=your_client_id_here
   DISCORD_CLIENT_SECRET=your_client_secret_here
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_REDIRECT_URI=http://localhost:5000/callback
   ```

## 🌐 Make Dashboard Public with Ngrok

1. **Install Ngrok:**
   - Download from: https://ngrok.com/download
   - Extract and place ngrok.exe in your project folder

2. **Run Ngrok:**
   ```bash
   ngrok http 5000
   ```

3. **Update Discord OAuth:**
   - Copy the HTTPS URL from ngrok (e.g., `https://abc123.ngrok.io`)
   - Add to Discord OAuth Redirects: `https://abc123.ngrok.io/callback`
   - Update `.env`: `DISCORD_REDIRECT_URI=https://abc123.ngrok.io/callback`

4. **Share Your Dashboard:**
   - Anyone can access: `https://abc123.ngrok.io`
   - They login with Discord and configure their servers!

## 📝 Bot Configuration

Update your bot (`main.py`) to read from the new multi-server config:

```python
# In your bot, load config per guild:
def get_guild_config(guild_id):
    with open('poem_config.json', 'r') as f:
        config = json.load(f)
    return config.get('servers', {}).get(str(guild_id), {})
```

## 🚀 Running

1. **Start Dashboard:**
   ```bash
   python web_dashboard.py
   ```

2. **Start Bot:**
   ```bash
   python main.py
   ```

3. **Start Ngrok (for public access):**
   ```bash
   ngrok http 5000
   ```

## ✨ Features

- ✅ Real Discord OAuth login
- ✅ Multi-server support (each server has own settings)
- ✅ Organized tabs (Poems, Tickets, General)
- ✅ Public access via Ngrok
- ✅ Mobile responsive
- ✅ Made by Depex © 2026
