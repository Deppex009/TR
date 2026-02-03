# Poem Bot for Discloud

A Discord poem bot designed for Arabic servers with beautiful embeds and customizable settings.

## Features

✨ **Slash Commands** - Easy to use with English commands and Arabic descriptions
🎨 **Customizable Colors** - Set embed colors by name (red, blue, purple) or hex code (#FF0000)
🖼️ **Image Management** - Enable/disable images and set custom image URL in one command
😊 **Auto Reactions** - Automatically react to poem embeds with custom emojis
📍 **Channel Management** - Set which channel poems appear in
🔄 **Auto Processing** - Delete original messages and repost as beautiful embeds
👤 **Author Info** - Displays who posted the poem with avatar

## Commands

- `/set_channel` - Set the channel for poems
- `/set_color` - Set embed color (name or hex code)
- `/image` - Manage image display (on/off and URL in one command)
- `/auto_react` - Setup auto reactions (on/off and choose emojis)
- `/info` - Show current bot settings

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the bot:
   ```
   python main.py
   ```

## Deploy (GitHub → Discloud)

This project is already configured for Discloud via `discloud.config` (entrypoint is `start_bot.py`).

1. Push to GitHub (safe)
   - Do **not** commit secrets: `.env` is ignored by `.gitignore`.
   - If you ever pasted your token anywhere, rotate it in the Discord Developer Portal.

2. Upload to Discloud
   - Easiest path: from GitHub click **Code → Download ZIP**, then upload that ZIP to Discloud.
   - Or create a GitHub Release and upload the release ZIP.

3. Set environment variables on Discloud
   - Required: `DISCORD_BOT_TOKEN`
   - If you use the web dashboard (OAuth): `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`
   - Restart the app after setting them.

Notes:
- `poem_config.json` is generated at runtime and is intentionally not committed.
- Discloud `TYPE=bot` runs the bot only. If you want the Flask dashboard online too, host it as a separate service (see `DASHBOARD_SETUP.md`).

## Configuration

The bot saves settings in `poem_config.json`:
- `poem_channel` - Target channel ID
- `embed_color` - Current embed color
- `show_image` - Image display toggle
- `image_url` - Current image URL
- `auto_react` - Auto reactions toggle
- `react_emojis` - List of reaction emojis

## Bot Status

The bot displays "By Dep-A7" as the playing status.

## Examples

**Image command:**
```
/image enabled:true url:https://example.com/image.png
/image enabled:false
```

**Auto React command:**
```
/auto_react enabled:true emojis:❤️ 🔥 😍
/auto_react enabled:false
```

---
Made with ❤️ for Arabic poetry lovers
