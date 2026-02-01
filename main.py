import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
import asyncio
import random
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Config file
CONFIG_FILE = "poem_config.json"

def load_config():
    """Load configuration from JSON file - supports both old and new multi-server format"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                # Check if it's the new multi-server format
                if "servers" in cfg:
                    # Return the entire multi-server config
                    return cfg
                # Old format - add new button defaults if they don't exist
                if "tickets" in cfg:
                    if "buttons" not in cfg["tickets"]:
                        cfg["tickets"]["buttons"] = {}
                    # Ping admin button
                    if "ping_admin" not in cfg["tickets"]["buttons"]:
                        cfg["tickets"]["buttons"]["ping_admin"] = "استدعاء الإدارة"
                    if "ping_admin_emoji" not in cfg["tickets"]["buttons"]:
                        cfg["tickets"]["buttons"]["ping_admin_emoji"] = "📢"
                    if "ping_admin_style" not in cfg["tickets"]["buttons"]:
                        cfg["tickets"]["buttons"]["ping_admin_style"] = "secondary"
                    # Mention member button (admin only)
                    if "mention_member" not in cfg["tickets"]["buttons"]:
                        cfg["tickets"]["buttons"]["mention_member"] = "منشن العضو"
                    if "mention_member_emoji" not in cfg["tickets"]["buttons"]:
                        cfg["tickets"]["buttons"]["mention_member_emoji"] = "👤"
                    if "mention_member_style" not in cfg["tickets"]["buttons"]:
                        cfg["tickets"]["buttons"]["mention_member_style"] = "secondary"
                    # Messages
                    if "messages" not in cfg["tickets"]:
                        cfg["tickets"]["messages"] = {}
                    if "ping_admin_message" not in cfg["tickets"]["messages"]:
                        cfg["tickets"]["messages"]["ping_admin_message"] = "تم استدعاء الإدارة @ADMIN"
                    if "mention_member_message" not in cfg["tickets"]["messages"]:
                        cfg["tickets"]["messages"]["mention_member_message"] = "@MEMBER تفضل"
                    if "ticket_created_success" not in cfg["tickets"]["messages"]:
                        cfg["tickets"]["messages"]["ticket_created_success"] = "✅ تم فتح التكيت"
                    if "by_emoji" not in cfg["tickets"]["messages"]:
                        cfg["tickets"]["messages"]["by_emoji"] = "👤"
                    # Force update reason_label and modal_placeholder to Arabic
                    cfg["tickets"]["messages"]["reason_label"] = "السبب"
                    cfg["tickets"]["messages"]["modal_placeholder"] = "اذكر سبب فتح للتذكره :"
                    # Force clear footer_text to show only time
                    cfg["tickets"]["messages"]["footer_text"] = ""
                return cfg
    except Exception as e:
        logger.error(f"Error loading config: {e}")
    
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
            logger.info("Config saved successfully")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def get_guild_config(guild_id):
    """Get configuration for a specific guild (server) - supports multi-server format"""
    config = load_config()
    
    # If it's multi-server format from dashboard
    if "servers" in config:
        guild_id_str = str(guild_id)
        if guild_id_str in config["servers"]:
            guild_cfg = config["servers"][guild_id_str]
            if "giveaway" not in guild_cfg:
                guild_cfg["giveaway"] = {
                    "channel_id": None,
                    "duration": "1h",
                    "winners": 1,
                    "emoji": "🎉",
                    "color": "#5865F2",
                    "image_url": ""
                }
                save_config(config)
            return guild_cfg
        else:
            # Create default config for this server
            default = {
                "poem_channel": None,
                "embed_color": "#9B59B6",
                "show_image": True,
                "image_url": "",
                "auto_react": False,
                "react_emojis": ["❤️", "🔥"],
                "tickets": {
                    "category_id": None,
                    "log_channel_id": None,
                    "admin_role_id": None
                },
                "giveaway": {
                    "channel_id": None,
                    "duration": "1h",
                    "winners": 1,
                    "emoji": "🎉",
                    "color": "#5865F2",
                    "image_url": ""
                }
            }
            config["servers"][guild_id_str] = default
            save_config(config)
            return default
    
    # Old single-server format - return as is for backward compatibility
    return config

def update_guild_config(guild_id, updates):
    """Update configuration for a specific guild"""
    full_config = load_config()
    
    # Convert to multi-server format if needed
    if "servers" not in full_config:
        full_config = {"servers": {}}
    
    guild_id_str = str(guild_id)
    
    # Get existing config or create new
    if guild_id_str not in full_config["servers"]:
        full_config["servers"][guild_id_str] = {
            "poem_channel": None,
            "embed_color": "#9B59B6",
            "show_image": True,
            "image_url": "",
            "auto_react": False,
            "react_emojis": ["❤️", "🔥"],
            "tickets": {
                "category_id": None,
                "log_channel_id": None,
                "admin_role_id": None
            },
            "giveaway": {
                "channel_id": None,
                "duration": "1h",
                "winners": 1,
                "emoji": "🎉",
                "color": "#5865F2",
                "image_url": ""
            }
        }
    
    # Update with new values
    full_config["servers"][guild_id_str].update(updates)
    save_config(full_config)

config = load_config()

# Helper function to convert color name to hex
COLOR_NAMES = {
    "red": "FF0000",
    "blue": "0000FF",
    "green": "00FF00",
    "yellow": "FFFF00",
    "purple": "9B59B6",
    "pink": "FF69B4",
    "orange": "FFA500",
    "cyan": "00FFFF",
    "lime": "32CD32",
    "gold": "FFD700",
    "white": "FFFFFF",
    "black": "000000",
    "grey": "808080",
    "gray": "808080",
    "magenta": "FF00FF",
    "brown": "A52A2A",
    "navy": "000080",
    "teal": "008080",
    "silver": "C0C0C0",
    "maroon": "800000",
    "olive": "808000",
    "aqua": "00FFFF",
    "coral": "FF7F50",
    "crimson": "DC143C",
    "indigo": "4B0082",
    "violet": "EE82EE",
    "turquoise": "40E0D0",
    "salmon": "FA8072",
    "khaki": "F0E68C",
    "lavender": "E6E6FA",
}

def parse_color(color_input):
    """Parse color name or ANY hex code to discord.Color - supports ALL colors"""
    try:
        color_input = str(color_input).lower().strip()
        
        # Remove any spaces
        color_input = color_input.replace(" ", "")
        
        # Check if it's a named color first
        if color_input in COLOR_NAMES:
            hex_code = COLOR_NAMES[color_input]
            return discord.Color(int(hex_code, 16))
        
        # Handle #RRGGBB format
        if color_input.startswith("#"):
            hex_code = color_input[1:]
            if len(hex_code) == 6:
                return discord.Color(int(hex_code, 16))
        
        # Handle 0xRRGGBB format
        if color_input.startswith("0x"):
            hex_code = color_input[2:]
            if len(hex_code) == 6:
                return discord.Color(int(hex_code, 16))
        
        # Try as plain hex RRGGBB
        if len(color_input) == 6:
            # Check if all characters are valid hex
            int(color_input, 16)  # This will raise ValueError if invalid
            return discord.Color(int(color_input, 16))
        
    except Exception as e:
        logger.warning(f"Color parse error for '{color_input}': {e}")
    
    # Default fallback color
    return discord.Color(0x9B59B6)

# Giveaway helpers
GIVEAWAY_DURATION_REGEX = re.compile(r"^(\d+)(s|m|h|d|w)$", re.IGNORECASE)
active_giveaways = {}

def parse_duration(duration_str):
    if not duration_str:
        return None
    duration_str = duration_str.strip().lower()
    match = GIVEAWAY_DURATION_REGEX.match(duration_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return amount * multipliers[unit]
    if duration_str.isdigit():
        return int(duration_str) * 60
    return None

def build_giveaway_embed(prize, host, end_ts, winners_count, entries_count, color, emoji, image_url=None, ended=False):
    status_title = "🎉 Giveaway Ended" if ended else "🎉 Giveaway"
    embed = discord.Embed(
        title=f"{status_title} | سحب",
        description=f"**Prize:** {prize}\n**الجائزة:** {prize}",
        color=color
    )
    embed.add_field(name="Hosted by | المستضيف", value=host.mention, inline=True)
    embed.add_field(name="Winners | الفائزون", value=str(winners_count), inline=True)
    embed.add_field(name="Entries | المشاركات", value=str(entries_count), inline=True)
    time_label = "Ended" if ended else "Ends"
    embed.add_field(name=f"{time_label} | ينتهي", value=f"<t:{end_ts}:F>\n(<t:{end_ts}:R>)", inline=False)
    embed.set_footer(text=f"Click {emoji} to enter | اضغط {emoji} للمشاركة")
    if image_url:
        embed.set_image(url=image_url)
    return embed

class GiveawayJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter | دخول", style=discord.ButtonStyle.primary, emoji="🎉")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        giveaway = active_giveaways.get(interaction.message.id)
        if not giveaway:
            return await interaction.response.send_message("❌ Giveaway انتهى", ephemeral=True)

        if interaction.user.bot:
            return await interaction.response.send_message("❌ Bots cannot join", ephemeral=True)

        if interaction.user.id in giveaway["entries"]:
            return await interaction.response.send_message("✅ You already entered | تم تسجيلك", ephemeral=True)

        giveaway["entries"].add(interaction.user.id)

        embed = build_giveaway_embed(
            prize=giveaway["prize"],
            host=interaction.guild.get_member(giveaway["host_id"]) or interaction.user,
            end_ts=giveaway["end_ts"],
            winners_count=giveaway["winners"],
            entries_count=len(giveaway["entries"]),
            color=discord.Color(giveaway["color"]),
            emoji=giveaway["emoji"],
            image_url=giveaway.get("image_url")
        )
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("🎉 You joined the giveaway | تم تسجيلك في السحب", ephemeral=True)

async def end_giveaway(message_id: int):
    giveaway = active_giveaways.get(message_id)
    if not giveaway:
        return

    channel = bot.get_channel(giveaway["channel_id"])
    if channel is None:
        try:
            channel = await bot.fetch_channel(giveaway["channel_id"])
        except Exception:
            active_giveaways.pop(message_id, None)
            return

    try:
        message = await channel.fetch_message(message_id)
    except Exception:
        active_giveaways.pop(message_id, None)
        return

    entries = list(giveaway["entries"])
    winners_count = giveaway["winners"]
    winners_ids = random.sample(entries, k=min(winners_count, len(entries))) if entries else []

    view = GiveawayJoinView()
    for item in view.children:
        if isinstance(item, discord.ui.Button):
            item.disabled = True
            item.emoji = giveaway["emoji"]

    embed = build_giveaway_embed(
        prize=giveaway["prize"],
        host=message.guild.get_member(giveaway["host_id"]) or message.guild.me,
        end_ts=giveaway["end_ts"],
        winners_count=giveaway["winners"],
        entries_count=len(giveaway["entries"]),
        color=discord.Color(giveaway["color"]),
        emoji=giveaway["emoji"],
        image_url=giveaway.get("image_url"),
        ended=True
    )
    await message.edit(embed=embed, view=view)

    if winners_ids:
        winners_mentions = " ".join(f"<@{user_id}>" for user_id in winners_ids)
        await channel.send(f"🎉 **Winners | الفائزون:** {winners_mentions}\n**Prize | الجائزة:** {giveaway['prize']}")
    else:
        await channel.send("❌ No valid entries | لا توجد مشاركات صحيحة")

    active_giveaways.pop(message_id, None)

async def schedule_giveaway_end(message_id: int, seconds: int):
    await asyncio.sleep(seconds)
    await end_giveaway(message_id)

async def start_giveaway(interaction: discord.Interaction, prize: str, duration: str, winners: int, channel: discord.TextChannel = None):
    seconds = parse_duration(duration)
    if not seconds or seconds <= 0:
        await interaction.response.send_message("❌ Duration format: 10s, 5m, 2h, 1d | صيغة المدة: 10s 5m 2h 1d", ephemeral=True)
        return

    if winners < 1:
        await interaction.response.send_message("❌ Winners must be at least 1 | عدد الفائزين يجب أن يكون 1 على الأقل", ephemeral=True)
        return

    guild_cfg = get_guild_config(interaction.guild_id)
    giveaway_cfg = guild_cfg.get("giveaway", {})

    target_channel = channel
    if target_channel is None and giveaway_cfg.get("channel_id"):
        target_channel = interaction.guild.get_channel(int(giveaway_cfg.get("channel_id")))
    if target_channel is None:
        target_channel = interaction.channel

    emoji = giveaway_cfg.get("emoji", "🎉")
    color = parse_color(giveaway_cfg.get("color", "#5865F2"))
    image_url = giveaway_cfg.get("image_url")

    end_ts = int(datetime.utcnow().timestamp()) + seconds
    embed = build_giveaway_embed(
        prize=prize,
        host=interaction.user,
        end_ts=end_ts,
        winners_count=winners,
        entries_count=0,
        color=color,
        emoji=emoji,
        image_url=image_url
    )

    view = GiveawayJoinView()
    for item in view.children:
        if isinstance(item, discord.ui.Button):
            item.emoji = emoji

    message = await target_channel.send(embed=embed, view=view)
    active_giveaways[message.id] = {
        "guild_id": interaction.guild_id,
        "channel_id": target_channel.id,
        "prize": prize,
        "host_id": interaction.user.id,
        "end_ts": end_ts,
        "winners": winners,
        "entries": set(),
        "emoji": emoji,
        "color": color.value,
        "image_url": image_url
    }

    asyncio.create_task(schedule_giveaway_end(message.id, seconds))
    if not interaction.response.is_done():
        await interaction.response.send_message("✅ Giveaway started | تم بدء السحب", ephemeral=True)
    else:
        await interaction.followup.send("✅ Giveaway started | تم بدء السحب", ephemeral=True)

class GiveawayModal(discord.ui.Modal, title="Giveaway | سحب"):
    prize = discord.ui.TextInput(label="Prize | الجائزة", placeholder="Nitro / Role / Gift", max_length=200)
    duration = discord.ui.TextInput(label="Duration (10m, 2h, 1d) | المدة", default="1h", max_length=20)
    winners = discord.ui.TextInput(label="Winners | عدد الفائزين", default="1", max_length=3)
    channel_id = discord.ui.TextInput(label="Channel ID (optional) | معرف القناة", required=False, max_length=25)

    async def on_submit(self, interaction: discord.Interaction):
        channel = None
        if self.channel_id.value:
            try:
                channel = interaction.guild.get_channel(int(self.channel_id.value))
            except Exception:
                channel = None

        try:
            winners_count = int(self.winners.value)
        except Exception:
            winners_count = 1

        await start_giveaway(interaction, self.prize.value, self.duration.value, winners_count, channel)

class GiveawayPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Giveaway | إنشاء سحب", style=discord.ButtonStyle.success, emoji="🎉")
    async def create_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GiveawayModal())

@bot.tree.command(name="giveawayf", description="Host a giveaway | إنشاء سحب")
@app_commands.describe(prize="Prize", duration="Duration (10m, 2h, 1d)", winners="Number of winners", channel="Channel to host in")
async def giveawayf(interaction: discord.Interaction, prize: str, duration: str, winners: int, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ You need Manage Server permission | تحتاج صلاحية إدارة السيرفر", ephemeral=True)
    await start_giveaway(interaction, prize, duration, winners, channel)

@bot.tree.command(name="giveaway_panel", description="Open giveaway panel | فتح لوحة السحب")
async def giveaway_panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ You need Manage Server permission | تحتاج صلاحية إدارة السيرفر", ephemeral=True)

    embed = discord.Embed(
        title="🎁 Giveaway Panel | لوحة السحب",
        description="**Create a giveaway with a simple panel**\n\n**أنشئ سحب بسهولة من اللوحة**",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Made by Depex © 2026")
    await interaction.response.send_message(embed=embed, view=GiveawayPanelView(), ephemeral=True)

@bot.event
async def on_ready():
    """Bot is ready"""
    try:
        await bot.tree.sync()
        activity = discord.Activity(type=discord.ActivityType.playing, name="By Dep-A7")
        await bot.change_presence(activity=activity)
        logger.info(f"✅ Bot ready! Logged in as {bot.user}")
    except Exception as e:
        logger.error(f"Ready event error: {e}")

@bot.tree.command(name="set_channel", description="Set the channel for poems | اختر قناة الأشعار")
@app_commands.describe(channel="The channel where poems will be posted | القناة التي ستُرسل فيها الأشعار")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the poem channel"""
    try:
        guild_config = get_guild_config(interaction.guild_id)
        update_guild_config(interaction.guild_id, {"poem_channel": channel.id})
        
        embed = discord.Embed(
            title="✅ Channel Set | تم تعيين القناة",
            description=f"Poem channel set to {channel.mention}\n\nتم تعيين قناة الأشعار إلى {channel.mention}",
            color=parse_color(guild_config.get("embed_color", "#9B59B6"))
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Channel set to {channel.id} for guild {interaction.guild_id}")
    except Exception as e:
        logger.error(f"Set channel error: {e}")
        await interaction.response.send_message("❌ Error setting channel", ephemeral=True)

@bot.tree.command(name="set_color", description="Set embed color | اختر لون الإطار")
@app_commands.describe(color="ANY color: name, #RRGGBB, 0xRRGGBB, or RRGGBB | أي لون: اسم أو كود")
async def set_color(interaction: discord.Interaction, color: str):
    """Set the embed color"""
    try:
        update_guild_config(interaction.guild_id, {"embed_color": color.lower()})
        
        parsed_color = parse_color(color)
        embed = discord.Embed(
            title="✅ Color Set | تم تعيين اللون",
            description=f"Embed color changed to `{color}`\n\n**Supports:**\n• Color names: red, blue, purple, pink, etc.\n• Hex codes: #FF5733, 0xFF5733, FF5733\n• ANY valid 6-digit hex color!\n\nتم تغيير لون الإطار إلى `{color}`",
            color=parsed_color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Color set to {color}")
    except Exception as e:
        logger.error(f"Set color error: {e}")
        await interaction.response.send_message("❌ Error setting color", ephemeral=True)

@bot.tree.command(name="image", description="Manage poem images | إدارة صور الأشعار")
@app_commands.describe(
    enabled="Enable or disable images | تفعيل أو تعطيل الصور",
    url="Image URL (optional) | رابط الصورة (اختياري)"
)
async def image(interaction: discord.Interaction, enabled: bool, url: str = None):
    """Manage image settings - enable/disable and set URL"""
    try:
        config["show_image"] = enabled
        
        if url:
            config["image_url"] = url
        
        save_config(config)
        
        status = "✅ Enabled | مُفعَّلة" if enabled else "❌ Disabled | معطَّلة"
        embed = discord.Embed(
            title="🖼️ Image Settings | إعدادات الصور",
            description=f"Status: {status}\n\nالحالة: {status}",
            color=parse_color(config["embed_color"])
        )
        
        if url:
            embed.add_field(name="URL Updated", value=url, inline=False)
            if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                embed.set_image(url=url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Image settings updated - enabled: {enabled}")
    except Exception as e:
        logger.error(f"Image command error: {e}")
        await interaction.response.send_message("❌ Error updating image settings", ephemeral=True)

@bot.tree.command(name="colors", description="See available colors | شاهد الألوان المتاحة")
async def colors(interaction: discord.Interaction):
    """Show available colors"""
    color_list = ", ".join(COLOR_NAMES.keys())
    embed = discord.Embed(
        title="🎨 Available Colors | الألوان المتاحة",
        description=f"**Colors:** {color_list}\n\n**Hex Codes:** Use #FF0000 or 0xFF0000 format\n\n**الألوان:** {color_list}\n\n**أكواد سادس عشر:** استخدم صيغة #FF0000 أو 0xFF0000",
        color=parse_color(config["embed_color"])
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="upload_image", description="Upload image by attachment | أرفع صورة")
@app_commands.describe(image="Upload image file | أرفع ملف الصورة")
async def upload_image(interaction: discord.Interaction, image: discord.Attachment):
    """Upload image via attachment"""
    try:
        # Check if it's an image
        if not image.content_type.startswith('image'):
            await interaction.response.send_message("❌ Please upload an image file | الرجاء رفع ملف صورة", ephemeral=True)
            return
        
        config["image_url"] = image.url
        save_config(config)
        
        embed = discord.Embed(
            title="✅ Image Uploaded | تم رفع الصورة",
            description="Your image is now set as the poem decoration\n\nتم تعيين صورتك كزينة الأشعار",
            color=parse_color(config["embed_color"])
        )
        embed.set_image(url=image.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Image uploaded by {interaction.user}")
    except Exception as e:
        logger.error(f"Upload image error: {e}")
        await interaction.response.send_message("❌ Error uploading image", ephemeral=True)

@bot.tree.command(name="auto_react", description="Setup auto reactions | إعداد التفاعلات التلقائية")
@app_commands.describe(
    enabled="Enable or disable auto reactions | تفعيل أو تعطيل التفاعلات",
    emojis="Add MULTIPLE emojis separated by spaces (❤️ 🔥 😍 💜 👏) | أضف عدة رموز مفصولة بمسافات"
)
async def auto_react(interaction: discord.Interaction, enabled: bool, emojis: str = None):
    """Setup auto reactions on poem embeds"""
    try:
        config["auto_react"] = enabled
        
        if emojis:
            # Split emojis and clean them up
            emoji_list = [e.strip() for e in emojis.split() if e.strip()]
            config["react_emojis"] = emoji_list
        
        save_config(config)
        
        status = "✅ Enabled | مُفعَّلة" if enabled else "❌ Disabled | معطَّلة"
        embed = discord.Embed(
            title="😊 Auto React Settings | إعدادات التفاعلات التلقائية",
            description=f"Status: {status}\n\nالحالة: {status}\n\n✨ **You can use MULTIPLE emojis!**\nJust separate them with spaces: ❤️ 🔥 😍 💜 👏\n\n**Works with:** Unicode emojis, Custom emojis, emoji IDs",
            color=parse_color(config["embed_color"])
        )
        
        if emojis:
            embed.add_field(
                name="Reactions | التفاعلات",
                value=" ".join(config["react_emojis"]),
                inline=False
            )
        else:
            embed.add_field(
                name="Current Reactions | التفاعلات الحالية",
                value=" ".join(config["react_emojis"]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Auto react settings updated - enabled: {enabled}, emojis: {config['react_emojis']}")
    except Exception as e:
        logger.error(f"Auto react command error: {e}")
        await interaction.response.send_message("❌ Error updating reactions", ephemeral=True)

@bot.tree.command(name="help", description="Show all commands | عرض جميع الأوامر")
async def help_command(interaction: discord.Interaction):
    """Show all available commands"""
    try:
        embed = discord.Embed(
            title="📚 Available Commands | الأوامر المتاحة",
            color=parse_color(config["embed_color"])
        )
        
        embed.add_field(
            name="📍 /set_channel",
            value="Choose poem channel | اختر قناة الأشعار",
            inline=False
        )
        embed.add_field(
            name="🎨 /set_color",
            value="Change embed color | غيّر لون الإطار",
            inline=False
        )
        embed.add_field(
            name="🖼️ /image",
            value="Enable/disable images | تفعيل/تعطيل الصور",
            inline=False
        )
        embed.add_field(
            name="📤 /upload_image",
            value="Upload image file | أرفع صورة",
            inline=False
        )
        embed.add_field(
            name="😊 /auto_react (IMPORTANT!)",
            value="Toggle reactions & set MULTIPLE emojis | غيّر التفاعلات والرموز\n\n**Usage:** `/auto_react enabled:true emojis:❤️ 🔥 😍 💜 👏`\n\n**Add as many emojis as you want!** Just separate with spaces.\n\n**To turn OFF:** `/auto_react enabled:false`",
            inline=False
        )
        embed.add_field(
            name="⚙️ /info",
            value="Show current settings | عرض الإعدادات الحالية",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    except Exception as e:
        logger.error(f"Help command error: {e}")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="info", description="Show current settings | عرض الإعدادات الحالية")
async def info(interaction: discord.Interaction):
    """Show current bot settings"""
    try:
        channel = bot.get_channel(config["poem_channel"]) if config["poem_channel"] else None
        
        embed = discord.Embed(
            title="⚙️ Bot Settings | إعدادات البوت",
            color=parse_color(config["embed_color"])
        )
        
        embed.add_field(
            name="📍 Poem Channel | قناة الأشعار",
            value=f"{channel.mention if channel else 'Not set | لم يتم التعيين'}",
            inline=False
        )
        embed.add_field(
            name="🎨 Embed Color | لون الإطار",
            value=f"`{config['embed_color']}`",
            inline=True
        )
        embed.add_field(
            name="🖼️ Image Display | عرض الصور",
            value=f"{'Enabled ✅ | مُفعَّلة' if config['show_image'] else 'Disabled ❌ | معطَّلة'}",
            inline=True
        )
        embed.add_field(
            name="🔗 Image URL | رابط الصورة",
            value=f"{config['image_url']}",
            inline=False
        )
        embed.add_field(
            name="😊 Auto React | التفاعلات التلقائية",
            value=f"{'Enabled ✅ | مُفعَّلة' if config['auto_react'] else 'Disabled ❌ | معطَّلة'}",
            inline=True
        )
        embed.add_field(
            name="Reactions | التفاعلات",
            value=" ".join(config["react_emojis"]),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Info command error: {e}")
        await interaction.response.send_message("❌ Error fetching settings", ephemeral=True)

@bot.tree.command(name="poem_setup", description="Open poem settings panel | فتح لوحة إعدادات الأشعار")
async def poem_setup(interaction: discord.Interaction):
    """Open poem settings panel"""
    try:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You need Administrator permission", ephemeral=True)
        
        guild_cfg = get_guild_config(interaction.guild_id)
        view = PoemSettingsView()
        embed = discord.Embed(
            title="📝 Poem Settings Panel | لوحة إعدادات الأشعار",
            description="**Configure poem system:**\n\n"
                       "📍 **Channel** - Set poem channel\n"
                       "🎨 **Appearance** - Colors, images, reactions\n"
                       "📋 **View Settings** - See current configuration\n\n"
                       "Use the dashboard for full control:\n"
                       f"http://localhost:5000",
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
        )
        embed.set_footer(text="Made by Depex © 2026")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class PoemSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Channel | القناة", emoji="📍", style=discord.ButtonStyle.primary)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PoemChannelModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Appearance | المظهر", emoji="🎨", style=discord.ButtonStyle.primary)
    async def set_appearance(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PoemAppearanceModal()
        await interaction.response.send_modal(modal)

class PoemChannelModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📍 Set Poem Channel")
        
        self.channel = discord.ui.TextInput(label="Channel ID", placeholder="1234567890", required=True)
        self.add_item(self.channel)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel.value)
            update_guild_config(interaction.guild_id, {"poem_channel": channel_id})
            channel = bot.get_channel(channel_id)
            await interaction.response.send_message(f"✅ Poem channel set to {channel.mention if channel else channel_id}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class PoemAppearanceModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🎨 Poem Appearance")
        
        self.color = discord.ui.TextInput(label="Embed Color (hex)", placeholder="#9B59B6 or 9B59B6", required=False)
        self.add_item(self.color)
        
        self.image_url = discord.ui.TextInput(label="Image URL", placeholder="https://...", required=False)
        self.add_item(self.image_url)
        
        self.show_image = discord.ui.TextInput(label="Show Image? (yes/no)", placeholder="yes", required=False)
        self.add_item(self.show_image)
        
        self.auto_react = discord.ui.TextInput(label="Auto React? (yes/no)", placeholder="no", required=False)
        self.add_item(self.auto_react)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            updates = {}
            if self.color.value:
                updates["embed_color"] = self.color.value.replace("#", "")
            if self.image_url.value:
                updates["image_url"] = self.image_url.value
            if self.show_image.value:
                updates["show_image"] = self.show_image.value.lower() in ["yes", "true", "1"]
            if self.auto_react.value:
                updates["auto_react"] = self.auto_react.value.lower() in ["yes", "true", "1"]
            
            update_guild_config(interaction.guild_id, updates)
            await interaction.response.send_message("✅ Poem appearance updated!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.event
async def on_message(message):
    """Process messages in poem channel"""
    if message.author.bot:
        return
    
    # Check if message is in the poem channel
    if config["poem_channel"] and message.channel.id == config["poem_channel"]:
        try:
            # Create embed with custom layout
            embed = discord.Embed(
                title="𝐓𝐑 • 𝐏𝐨𝐞𝐦𝐬",
                description=f"\n\n**{message.content}**\n\n",
                color=parse_color(config["embed_color"])
            )
            
            # Set USER's profile picture on the RIGHT as thumbnail
            if message.author.avatar:
                embed.set_thumbnail(url=message.author.avatar.url)
            
            # Set footer with bot icon and username
            embed.set_footer(
                text=f"{message.author.display_name}",
                icon_url=bot.user.avatar.url if bot.user.avatar else None
            )
            
            # Send embed
            embed_message = await message.channel.send(embed=embed)
            
            # Add auto reactions if enabled
            if config["auto_react"] and config["react_emojis"]:
                for emoji in config["react_emojis"]:
                    try:
                        # Try to add the emoji - works with unicode, custom emojis, etc
                        await embed_message.add_reaction(emoji.strip())
                    except Exception as e:
                        logger.warning(f"Could not add reaction {emoji}: {e}")
                        # Try to find if it's a custom emoji ID
                        try:
                            if emoji.isdigit():
                                # It's just an emoji ID, try to get the emoji
                                emoji_obj = await bot.fetch_emoji(int(emoji))
                                await embed_message.add_reaction(emoji_obj)
                        except:
                            pass
            
            # Send decorative image AFTER the embed if enabled and URL is set - NOT as embed
            if config["show_image"] and config["image_url"]:
                try:
                    await message.channel.send(config["image_url"])
                except Exception as e:
                    logger.warning(f"Could not send image: {e}")
            
            # Delete original message
            await message.delete()
            logger.info(f"Poem processed from {message.author}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    await bot.process_commands(message)

# Error handling
@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    logger.error(f"Error in {event}: {args}", exc_info=True)

# ============= TICKET SYSTEM =============

class TicketDropdown(discord.ui.Select):
    """Dropdown for ticket options"""
    def __init__(self):
        options = []
        for option in config["tickets"]["ticket_options"]:
            options.append(
                discord.SelectOption(
                    label=option["label"],
                    emoji=option.get("emoji", "🎫"),
                    description=option["description"]
                )
            )
        super().__init__(
            placeholder=config["tickets"].get("dropdown_placeholder", "إضغط لفتح التكيت"), 
            min_values=1, 
            max_values=1, 
            options=options,
            custom_id="ticket_dropdown_persistent"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle ticket creation"""
        # Show modal for reason
        modal = TicketReasonModal(self.values[0])
        await interaction.response.send_modal(modal)

class TicketDropdownView(discord.ui.View):
    """View with dropdown"""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

class TicketReasonModal(discord.ui.Modal):
    """Modal to ask for ticket reason"""
    def __init__(self, ticket_type):
        super().__init__(title=config["tickets"]["messages"].get("modal_title", "فتح تذكرة"))
        self.ticket_type = ticket_type
        
        self.reason = discord.ui.TextInput(
            label=config["tickets"]["messages"].get("reason_label", "السبب"),
            placeholder=config["tickets"]["messages"].get("modal_placeholder", "اذكر سبب فتح للتذكره :"),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=500
        )
        self.add_item(self.reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Create ticket channel"""
        try:
            # Defer response immediately to prevent timeout
            await interaction.response.defer(ephemeral=True)
            
            # Increment ticket counter
            config["tickets"]["ticket_counter"] += 1
            ticket_num = config["tickets"]["ticket_counter"]
            save_config(config)
            
            # Get category
            category = None
            if config["tickets"]["category_id"]:
                category = bot.get_channel(config["tickets"]["category_id"])
            
            # Create ticket channel with username
            guild = interaction.guild
            # Clean username for channel name (remove spaces, special chars)
            username = interaction.user.name.lower().replace(" ", "-").replace("_", "-")
            # Remove any non-alphanumeric characters except hyphens
            username = ''.join(c for c in username if c.isalnum() or c == '-')
            channel_name = f"ticket-{username}"
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Add support roles
            for role_id in config["tickets"].get("support_roles", []):
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )
            
            # Create mention string for ping roles
            ping_mentions = ""
            for role_id in config["tickets"].get("ping_roles", []):
                role = guild.get_role(role_id)
                if role:
                    ping_mentions += f" {role.mention}"
            
            # Create ticket embed
            embed = discord.Embed(
                title=self.ticket_type,
                description=config["tickets"]["messages"]["ticket_created_desc"],
                color=parse_color(config["tickets"]["embed_color"])
            )
            
            # Add ticket image
            if config["tickets"].get("panel_image") and config["tickets"]["panel_image"] != "YOUR IMAGE URL HERE":
                embed.set_image(url=config["tickets"]["panel_image"])
            
            # Add fields
            by_label = config["tickets"]["messages"].get("ticket_by_label", "بواسطة")
            by_emoji = config["tickets"]["messages"].get("by_emoji", "👤")
            embed.add_field(name=f"{by_emoji} {by_label}", value=interaction.user.mention, inline=False)
            
            # Use custom footer - only show time
            footer_text = config["tickets"]["messages"].get("footer_text", "")
            if footer_text:
                embed.set_footer(text=f"{footer_text} • {interaction.created_at.strftime('%I:%M %p')}")
            else:
                embed.set_footer(text=interaction.created_at.strftime('%I:%M %p'))
            
            # Create reason embed
            reason_field_name = config["tickets"]["messages"].get("reason_field_name", "REASON:")
            reason_embed = discord.Embed(
                description=f"**{reason_field_name}**\n{self.reason.value}",
                color=parse_color(config["tickets"]["embed_color"])
            )
            
            # Send both embeds together with buttons (reason will appear between embed and buttons)
            view = TicketControlView(ticket_channel.id, interaction.user.id)
            content = f"{interaction.user.mention}{ping_mentions}"
            await ticket_channel.send(content=content, embeds=[embed, reason_embed], view=view)
            
            # Log ticket creation
            await self.log_ticket_creation(interaction, ticket_channel, ticket_num, self.reason.value)
            
            # Follow up with success message
            success_msg = config["tickets"]["messages"].get("ticket_created_success", "✅ تم فتح التكيت")
            await interaction.followup.send(
                f"{success_msg} {ticket_channel.mention}",
                ephemeral=True
            )
            
            logger.info(f"Ticket #{ticket_num} created by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            try:
                await interaction.followup.send("❌ خطأ في فتح التكيت", ephemeral=True)
            except:
                await interaction.response.send_message("❌ خطأ في فتح التكيت", ephemeral=True)
    
    async def log_ticket_creation(self, interaction, ticket_channel, ticket_num, reason):
        """Log ticket creation to log channel"""
        try:
            log_channel_id = config["tickets"].get("log_channel_id")
            if not log_channel_id:
                return
            
            log_channel = bot.get_channel(log_channel_id)
            if not log_channel:
                return
            
            messages = config["tickets"]["messages"]
            
            embed = discord.Embed(
                title=messages.get("log_ticket_opened", "📬 Ticket Opened"),
                color=parse_color(config["tickets"]["embed_color"]),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name=messages.get("log_opened_by", "Opened By"), value=interaction.user.mention, inline=True)
            embed.add_field(name=messages.get("log_channel", "Channel"), value=ticket_channel.mention, inline=True)
            embed.add_field(name="#", value=str(ticket_num), inline=True)
            embed.add_field(name=messages.get("log_reason", "Reason"), value=reason, inline=False)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging ticket creation: {e}")

class TicketControlView(discord.ui.View):
    """Buttons for ticket control"""
    def __init__(self, channel_id, owner_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.owner_id = owner_id
        
        # Convert string to ButtonStyle helper
        style_map = {
            "primary": discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary,
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
            "blurple": discord.ButtonStyle.primary,
            "grey": discord.ButtonStyle.secondary,
            "gray": discord.ButtonStyle.secondary,
            "green": discord.ButtonStyle.success,
            "red": discord.ButtonStyle.danger
        }
        
        # Close button (ADMIN ONLY)
        close_style = style_map.get(config["tickets"]["buttons"].get("close_style", "danger").lower(), discord.ButtonStyle.danger)
        close_btn = discord.ui.Button(
            label=config["tickets"]["buttons"]["close"],
            emoji=config["tickets"]["buttons"]["close_emoji"],
            style=close_style,
            custom_id=f"ticket_close_{channel_id}"
        )
        close_btn.callback = self.close_ticket
        self.add_item(close_btn)
        
        # Claim button (ADMIN ONLY)
        claim_style = style_map.get(config["tickets"]["buttons"].get("claim_style", "primary").lower(), discord.ButtonStyle.primary)
        claim_btn = discord.ui.Button(
            label=config["tickets"]["buttons"]["claim"],
            emoji=config["tickets"]["buttons"]["claim_emoji"],
            style=claim_style,
            custom_id=f"ticket_claim_{channel_id}"
        )
        claim_btn.callback = self.claim_ticket
        self.add_item(claim_btn)
        
        # Ping Admin button (MEMBER CAN USE)
        ping_admin_style = style_map.get(config["tickets"]["buttons"].get("ping_admin_style", "secondary").lower(), discord.ButtonStyle.secondary)
        ping_admin_btn = discord.ui.Button(
            label=config["tickets"]["buttons"].get("ping_admin", "استدعاء الإدارة"),
            emoji=config["tickets"]["buttons"].get("ping_admin_emoji", "📢"),
            style=ping_admin_style,
            custom_id=f"ticket_ping_admin_{channel_id}"
        )
        ping_admin_btn.callback = self.ping_admin
        self.add_item(ping_admin_btn)
        
        # Mention Member button (ADMIN ONLY)
        mention_member_style = style_map.get(config["tickets"]["buttons"].get("mention_member_style", "secondary").lower(), discord.ButtonStyle.secondary)
        mention_member_btn = discord.ui.Button(
            label=config["tickets"]["buttons"].get("mention_member", "منشن العضو"),
            emoji=config["tickets"]["buttons"].get("mention_member_emoji", "👤"),
            style=mention_member_style,
            custom_id=f"ticket_mention_member_{channel_id}"
        )
        mention_member_btn.callback = self.mention_member
        self.add_item(mention_member_btn)
        
        # Add dropdown for menu options (ADMIN ONLY)
        self.add_item(TicketMenuDropdown(channel_id, owner_id))
    
    def has_permission(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permission (support roles only)"""
        # Check if user has any of the support roles
        user_role_ids = [role.id for role in interaction.user.roles]
        support_role_ids = config["tickets"].get("support_roles", [])
        
        # User needs to have at least one support role
        return any(role_id in support_role_ids for role_id in user_role_ids)
    
    async def ping_admin(self, interaction: discord.Interaction):
        """Ping admin roles (anyone can use)"""
        try:
            # Build ping mentions
            ping_mentions = ""
            for role_id in config["tickets"].get("support_roles", []):
                role = interaction.guild.get_role(role_id)
                if role:
                    ping_mentions += f" {role.mention}"
            
            if not ping_mentions:
                await interaction.response.send_message("❌ لا توجد أدوار إدارية محددة", ephemeral=True)
                return
            
            # Get custom message
            message = config["tickets"]["messages"].get("ping_admin_message", "تم استدعاء الإدارة @ADMIN")
            message = message.replace("@ADMIN", ping_mentions)
            
            await interaction.response.send_message(message)
            
        except Exception as e:
            logger.error(f"Error pinging admin: {e}")
            await interaction.response.send_message("❌ خطأ", ephemeral=True)
    
    async def mention_member(self, interaction: discord.Interaction):
        """Mention ticket owner (ADMIN ONLY)"""
        try:
            # Check permissions - admin only
            if not self.has_permission(interaction):
                await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
                return
            
            # Get ticket owner
            owner = interaction.guild.get_member(self.owner_id)
            if owner:
                # Get custom message
                message = config["tickets"]["messages"].get("mention_member_message", "@MEMBER تفضل")
                message = message.replace("@MEMBER", owner.mention)
                await interaction.response.send_message(message)
            else:
                await interaction.response.send_message("❌ لم يتم العثور على العضو", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error mentioning member: {e}")
            await interaction.response.send_message("❌ خطأ", ephemeral=True)
    
    async def close_ticket(self, interaction: discord.Interaction):
        """Close ticket (ADMIN ONLY)"""
        try:
            # Check permissions - admin only
            if not self.has_permission(interaction):
                await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
                return
            
            # Log ticket closure
            await self.log_ticket_action(interaction, "closed")
            
            await interaction.response.send_message("🔒 جاري اغلاق التكيت...")
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
    
    async def claim_ticket(self, interaction: discord.Interaction):
        """Claim ticket for admin (ADMIN ONLY)"""
        try:
            # Check permissions - admin only
            if not self.has_permission(interaction):
                await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
                return
            
            # Get channel and update permissions
            channel = interaction.channel
            guild = interaction.guild
            
            # Get ticket owner
            owner = guild.get_member(self.owner_id)
            
            # Reset permissions - only claimer and owner can see
            await channel.edit(sync_permissions=False)
            
            # Set permissions for claimer
            await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            
            # Set permissions for owner
            if owner:
                await channel.set_permissions(owner, read_messages=True, send_messages=True)
            
            # Set bot permissions
            await channel.set_permissions(guild.me, read_messages=True, send_messages=True)
            
            # Remove everyone else
            await channel.set_permissions(guild.default_role, read_messages=False)
            
            # Log ticket claim
            await self.log_ticket_action(interaction, "claimed")
            
            # Send claim message
            claim_msg = config["tickets"]["messages"].get("claim_message", "@USER استدعى الإدارة")
            claim_msg = claim_msg.replace("@USER", interaction.user.mention)
            
            claim_emoji = config["tickets"]["messages"].get("claim_emoji", "👥")
            
            await interaction.response.send_message(f"{claim_emoji} {claim_msg}")
            logger.info(f"Ticket claimed by {interaction.user}")
            
        except Exception as e:
            logger.error(f"Error claiming ticket: {e}")
            try:
                await interaction.response.send_message("❌ خطأ في الاستدعاء", ephemeral=True)
            except:
                pass
    
    async def log_ticket_action(self, interaction: discord.Interaction, action: str):
        """Log ticket actions to log channel"""
        try:
            log_channel_id = config["tickets"].get("log_channel_id")
            if not log_channel_id:
                return
            
            log_channel = bot.get_channel(log_channel_id)
            if not log_channel:
                return
            
            messages = config["tickets"]["messages"]
            
            if action == "closed":
                title = messages.get("log_ticket_closed", "🔒 Ticket Closed")
                by_label = messages.get("log_closed_by", "Closed By")
            elif action == "claimed":
                title = messages.get("log_ticket_claimed", "👥 Ticket Claimed")
                by_label = messages.get("log_claimed_by", "Claimed By")
            else:
                return
            
            embed = discord.Embed(
                title=title,
                color=parse_color(config["tickets"]["embed_color"]),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name=by_label, value=interaction.user.mention, inline=True)
            embed.add_field(name=messages.get("log_channel", "Channel"), value=interaction.channel.mention, inline=True)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging ticket action: {e}")

class TicketMenuDropdown(discord.ui.Select):
    """Dropdown menu for ticket actions"""
    def __init__(self, channel_id, owner_id):
        self.channel_id = channel_id
        self.owner_id = owner_id
        
        menu_cfg = config["tickets"].get("menu_options", {})
        
        options = [
            discord.SelectOption(
                label=menu_cfg.get("rename", {}).get("label", "Rename"),
                emoji=menu_cfg.get("rename", {}).get("emoji", "✏️"),
                description=menu_cfg.get("rename", {}).get("description", "تغيير اسم التكيت"),
                value="rename"
            ),
            discord.SelectOption(
                label=menu_cfg.get("add_user", {}).get("label", "Add User"),
                emoji=menu_cfg.get("add_user", {}).get("emoji", "👤"),
                description=menu_cfg.get("add_user", {}).get("description", "اضافة عضو للتكيت"),
                value="add_user"
            ),
            discord.SelectOption(
                label=menu_cfg.get("remove_user", {}).get("label", "Remove User"),
                emoji=menu_cfg.get("remove_user", {}).get("emoji", "🚫"),
                description=menu_cfg.get("remove_user", {}).get("description", "إزالة عضو من التكيت"),
                value="remove_user"
            ),
            discord.SelectOption(
                label=menu_cfg.get("reset", {}).get("label", "Reset Menu"),
                emoji=menu_cfg.get("reset", {}).get("emoji", "🔄"),
                description=menu_cfg.get("reset", {}).get("description", "إعادة تعيين القائمة"),
                value="reset"
            )
        ]
        
        super().__init__(
            placeholder=config["tickets"].get("menu_placeholder", "تحديل التكيت"),
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"ticket_menu_{channel_id}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle menu selection (ADMIN ONLY)"""
        try:
            # Check if user has admin permission
            user_role_ids = [role.id for role in interaction.user.roles]
            support_role_ids = config["tickets"].get("support_roles", [])
            has_permission = any(role_id in support_role_ids for role_id in user_role_ids)
            
            if not has_permission:
                await interaction.response.send_message("❌ ليس لديك صلاحية", ephemeral=True)
                return
            
            action = self.values[0]
            
            if action == "reset":
                # Reset the menu by updating the message
                await interaction.response.send_message("🔄 تم إعادة تعيين القائمة", ephemeral=True, delete_after=2)
                return
            
            elif action == "rename":
                # Show modal for renaming
                modal = RenameTicketModal(interaction.channel)
                await interaction.response.send_modal(modal)
                
            elif action == "add_user":
                # Show modal for adding user
                modal = AddUserModal(interaction.channel)
                await interaction.response.send_modal(modal)
                
            elif action == "remove_user":
                # Show modal for removing user
                modal = RemoveUserModal(interaction.channel)
                await interaction.response.send_modal(modal)
                
        except Exception as e:
            logger.error(f"Error in menu action: {e}")
            await interaction.response.send_message("❌ خطأ", ephemeral=True)

class RenameTicketModal(discord.ui.Modal):
    """Modal for renaming ticket"""
    def __init__(self, channel):
        super().__init__(title="تغيير اسم التكيت")
        self.channel = channel
        
        self.new_name = discord.ui.TextInput(
            label="الاسم الجديد",
            placeholder="ticket-new-name",
            required=True,
            max_length=100
        )
        self.add_item(self.new_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_name = self.new_name.value.strip().replace(" ", "-")
            await self.channel.edit(name=new_name)
            await interaction.response.send_message(f"✅ تم تغيير الاسم إلى: {new_name}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error renaming ticket: {e}")
            await interaction.response.send_message("❌ خطأ في تغيير الاسم", ephemeral=True)

class AddUserModal(discord.ui.Modal):
    """Modal for adding user to ticket"""
    def __init__(self, channel):
        super().__init__(title="اضافة عضو للتكيت")
        self.channel = channel
        
        self.user_input = discord.ui.TextInput(
            label="معرف العضو أو المنشن",
            placeholder="@user أو 123456789",
            required=True
        )
        self.add_item(self.user_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Try to extract user ID
            user_text = self.user_input.value.strip()
            user_id = int(''.join(filter(str.isdigit, user_text)))
            
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message("❌ لم يتم العثور على العضو", ephemeral=True)
                return
            
            await self.channel.set_permissions(member, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"✅ تمت اضافة {member.mention} للتكيت")
            
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            await interaction.response.send_message("❌ خطأ في اضافة العضو", ephemeral=True)

class RemoveUserModal(discord.ui.Modal):
    """Modal for removing user from ticket"""
    def __init__(self, channel):
        super().__init__(title="إزالة عضو من التكيت")
        self.channel = channel
        
        self.user_input = discord.ui.TextInput(
            label="معرف العضو أو المنشن",
            placeholder="@user أو 123456789",
            required=True
        )
        self.add_item(self.user_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Try to extract user ID
            user_text = self.user_input.value.strip()
            user_id = int(''.join(filter(str.isdigit, user_text)))
            
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message("❌ لم يتم العثور على العضو", ephemeral=True)
                return
            
            await self.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(f"✅ تمت إزالة {member.mention} من التكيت")
            
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            await interaction.response.send_message("❌ خطأ في إزالة العضو", ephemeral=True)


# Ticket Commands

@bot.tree.command(name="ticket_panel", description="Create ticket panel | إنشاء لوحة التكيت")
@app_commands.describe(channel="Channel to send panel | القناة لإرسال اللوحة")
async def ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """Create ticket panel"""
    try:
        target_channel = channel or interaction.channel
        
        # Create embed
        embed = discord.Embed(
            title=config["tickets"]["panel_title"],
            description=config["tickets"]["panel_description"],
            color=parse_color(config["tickets"]["embed_color"])
        )
        
        # Add main panel image (big image)
        if config["tickets"].get("panel_image") and config["tickets"]["panel_image"] != "YOUR IMAGE URL HERE":
            embed.set_image(url=config["tickets"]["panel_image"])
        
        # Add small author icon if set
        if config["tickets"].get("panel_author_icon") and config["tickets"]["panel_author_icon"] != "YOUR ICON URL HERE":
            embed.set_author(
                name=config["tickets"].get("panel_author_name", "Ticket System"),
                icon_url=config["tickets"]["panel_author_icon"]
            )
        
        embed.timestamp = discord.utils.utcnow()
        
        # Send with dropdown
        view = TicketDropdownView()
        await target_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(f"✅ Ticket panel created in {target_channel.mention}", ephemeral=True)
        logger.info(f"Ticket panel created by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error creating ticket panel: {e}", exc_info=True)
        await interaction.response.send_message(f"❌ Error creating panel: {str(e)}", ephemeral=True)

@bot.tree.command(name="ticket_category", description="Set ticket category | تعيين تصنيف التكيت")
@app_commands.describe(category="Category for tickets | التصنيف للتكيت")
async def ticket_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    """Set ticket category"""
    try:
        config["tickets"]["category_id"] = category.id
        save_config(config)
        
        await interaction.response.send_message(f"✅ Ticket category set to: {category.name}", ephemeral=True)
        logger.info(f"Ticket category set to {category.id}")
        
    except Exception as e:
        logger.error(f"Error setting category: {e}")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="ticket_log_channel", description="Set ticket log channel | تعيين قناة سجل التكيت")
@app_commands.describe(channel="Channel for ticket logs | قناة سجلات التكيت")
async def ticket_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set ticket log channel"""
    try:
        config["tickets"]["log_channel_id"] = channel.id
        save_config(config)
        
        await interaction.response.send_message(f"✅ Ticket log channel set to: {channel.mention}", ephemeral=True)
        logger.info(f"Ticket log channel set to {channel.id}")
        
    except Exception as e:
        logger.error(f"Error setting log channel: {e}")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="ticket_setup", description="Open ticket settings panel | فتح لوحة إعدادات التكيت")
async def ticket_setup(interaction: discord.Interaction):
    """Open interactive settings panel"""
    try:
        embed = discord.Embed(
            title="🎫 Ticket Settings Panel | لوحة إعدادات التكيت",
            description="**Choose a category to edit: | اختر فئة للتعديل:**\n\n"
                       "🎨 **Panel | اللوحة** - Title, description, images, colors | العنوان، الوصف، الصور، الألوان\n"
                       "📋 **Options | الخيارات** - Add/edit/remove ticket options | إضافة/تعديل/حذف خيارات التكيت\n"
                       "👥 **Roles | الأدوار** - Support & ping roles | أدوار الدعم والمنشن\n"
                       "📝 **Messages | الرسائل** - All text & placeholders | جميع النصوص والعبارات\n"
                       "🎛️ **Menu | القائمة** - Dropdown menu options | خيارات القائمة المنسدلة\n"
                       "⚙️ **View | عرض** - See current settings | عرض الإعدادات الحالية",
            color=parse_color(config["tickets"]["embed_color"])
        )
        
        view = SettingsCategoryView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error opening settings: {e}")
        await interaction.response.send_message("❌ Error", ephemeral=True)

# Settings Panel Views

class SettingsCategoryView(discord.ui.View):
    """Main settings category selector"""
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Panel | اللوحة", emoji="🎨", style=discord.ButtonStyle.primary, row=0)
    async def panel_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PanelSettingsModal(interaction.guild_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Options | الخيارات", emoji="📋", style=discord.ButtonStyle.primary, row=0)
    async def options_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = OptionsManageView()
        embed = discord.Embed(
            title="📋 Manage Ticket Options | إدارة خيارات التكيت",
            description="**Current Options: | الخيارات الحالية:**\n" + "\n".join([
                f"{i+1}. {opt.get('emoji', '🎫')} {opt['label']}"
                for i, opt in enumerate(config["tickets"]["ticket_options"])
            ]),
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Roles | الأدوار", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def roles_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RolesSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Messages | الرسائل", emoji="📝", style=discord.ButtonStyle.primary, row=1)
    async def messages_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MessagesEditView()
        embed = discord.Embed(
            title="📝 Messages & Text Settings | إعدادات الرسائل",
            description="**Edit message settings: | تعديل إعدادات الرسائل:**\n\n"
                       "• Claim message & emoji | رسالة وأيقونة الاستدعاء\n"
                       "• Button labels | نصوص الأزرار\n"
                       "• All text labels | جميع النصوص",
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Menu | القائمة", emoji="🎛️", style=discord.ButtonStyle.primary, row=1)
    async def menu_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MenuOptionsView()
        embed = discord.Embed(
            title="🎛️ Menu Options Settings | إعدادات خيارات القائمة",
            description="Edit the dropdown menu options in tickets | تعديل خيارات القائمة المنسدلة في التكيت",
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="View Settings | عرض", emoji="⚙️", style=discord.ButtonStyle.secondary, row=1)
    async def view_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        category = bot.get_channel(config["tickets"]["category_id"]) if config["tickets"]["category_id"] else None
        log_channel = bot.get_channel(config["tickets"]["log_channel_id"]) if config["tickets"].get("log_channel_id") else None
        
        embed = discord.Embed(title="⚙️ Current Settings | الإعدادات الحالية", color=parse_color(config["tickets"]["embed_color"]))
        embed.add_field(name="📁 Category | التصنيف", value=category.name if category else "Not set | غير محدد", inline=False)
        embed.add_field(name="📋 Log Channel | قناة السجلات", value=log_channel.mention if log_channel else "Not set | غير محدد", inline=False)
        embed.add_field(name="🎨 Color | اللون", value=config["tickets"]["embed_color"], inline=True)
        embed.add_field(name="🔢 Tickets Created | التكيتات المفتوحة", value=str(config["tickets"]["ticket_counter"]), inline=True)
        
        options_text = "\n".join([f"{opt.get('emoji', '🎫')} {opt['label']}" for opt in config["tickets"]["ticket_options"]])
        embed.add_field(name="📋 Options | الخيارات", value=options_text or "None | لا يوجد", inline=False)
        
        support_roles = " ".join([f"<@&{rid}>" for rid in config["tickets"].get("support_roles", [])])
        embed.add_field(name="👥 Support Roles | أدوار الدعم", value=support_roles or "None | لا يوجد", inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)

class PanelSettingsModal(discord.ui.Modal):
    """Modal for editing panel settings"""
    def __init__(self, guild_id):
        super().__init__(title="🎨 Edit Panel Settings")
        self.guild_id = guild_id
        guild_cfg = get_guild_config(guild_id)
        
        self.title_input = discord.ui.TextInput(
            label="Panel Title",
            default=guild_cfg.get("tickets", {}).get("panel_title", ""),
            max_length=256
        )
        self.add_item(self.title_input)
        
        self.desc_input = discord.ui.TextInput(
            label="Panel Description",
            default=guild_cfg.get("tickets", {}).get("panel_description", ""),
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        self.add_item(self.desc_input)
        
        self.color_input = discord.ui.TextInput(
            label="Embed Color (hex code)",
            default=guild_cfg.get("tickets", {}).get("embed_color", ""),
            max_length=6,
            required=False
        )
        self.add_item(self.color_input)
        
        self.image_input = discord.ui.TextInput(
            label="Panel Image URL",
            default=guild_cfg.get("tickets", {}).get("panel_image", ""),
            required=False
        )
        self.add_item(self.image_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(self.guild_id)
            if "tickets" not in guild_cfg:
                guild_cfg["tickets"] = {}
            
            guild_cfg["tickets"]["panel_title"] = self.title_input.value
            guild_cfg["tickets"]["panel_description"] = self.desc_input.value
            if self.color_input.value:
                guild_cfg["tickets"]["embed_color"] = self.color_input.value
            if self.image_input.value:
                guild_cfg["tickets"]["panel_image"] = self.image_input.value
            
            update_guild_config(self.guild_id, guild_cfg)
            await interaction.response.send_message("✅ Panel settings updated!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class OptionsManageView(discord.ui.View):
    """View for managing ticket options"""
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Add Option | إضافة", emoji="➕", style=discord.ButtonStyle.success)
    async def add_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddOptionModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Edit Option | تعديل", emoji="✏️", style=discord.ButtonStyle.primary)
    async def edit_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditOptionModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove Option | حذف", emoji="🗑️", style=discord.ButtonStyle.danger)
    async def remove_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveOptionModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Back | رجوع", emoji="◀️", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsCategoryView()
        embed = discord.Embed(
            title="🎫 Ticket Settings Panel | لوحة إعدادات التكيت",
            description="**Choose a category to edit: | اختر فئة للتعديل:**\n\n"
                       "🎨 **Panel | اللوحة** - Title, description, images, colors | العنوان، الوصف، الصور، الألوان\n"
                       "📋 **Options | الخيارات** - Add/edit/remove ticket options | إضافة/تعديل/حذف خيارات التكيت\n"
                       "👥 **Roles | الأدوار** - Support & ping roles | أدوار الدعم والمنشن\n"
                       "📝 **Messages | الرسائل** - All text & placeholders | جميع النصوص والعبارات\n"
                       "🎛️ **Menu | القائمة** - Dropdown menu options | خيارات القائمة المنسدلة\n"
                       "⚙️ **View | عرض** - See current settings | عرض الإعدادات الحالية",
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)

class AddOptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="➕ Add New Option")
        
        self.label = discord.ui.TextInput(label="Label", placeholder="Technical Support", max_length=100)
        self.add_item(self.label)
        
        self.emoji = discord.ui.TextInput(label="Emoji", placeholder="🛠️", max_length=50)
        self.add_item(self.emoji)
        
        self.description = discord.ui.TextInput(label="Description", placeholder="Get technical help", max_length=100)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["ticket_options"].append({
                "label": self.label.value,
                "emoji": self.emoji.value,
                "description": self.description.value
            })
            save_config(config)
            await interaction.response.send_message(f"✅ Added: {self.emoji.value} {self.label.value}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditOptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="✏️ Edit Option")
        
        self.number = discord.ui.TextInput(label="Option Number (1, 2, 3...)", placeholder="1", max_length=2)
        self.add_item(self.number)
        
        self.label = discord.ui.TextInput(label="New Label", required=False, max_length=100)
        self.add_item(self.label)
        
        self.emoji = discord.ui.TextInput(label="New Emoji", required=False, max_length=50)
        self.add_item(self.emoji)
        
        self.description = discord.ui.TextInput(label="New Description", required=False, max_length=100)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            idx = int(self.number.value) - 1
            if idx < 0 or idx >= len(config["tickets"]["ticket_options"]):
                await interaction.response.send_message(f"❌ Invalid number. Choose 1-{len(config['tickets']['ticket_options'])}", ephemeral=True)
                return
            
            if self.label.value:
                config["tickets"]["ticket_options"][idx]["label"] = self.label.value
            if self.emoji.value:
                config["tickets"]["ticket_options"][idx]["emoji"] = self.emoji.value
            if self.description.value:
                config["tickets"]["ticket_options"][idx]["description"] = self.description.value
            
            save_config(config)
            opt = config["tickets"]["ticket_options"][idx]
            await interaction.response.send_message(f"✅ Updated: {opt.get('emoji', '')} {opt['label']}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class RemoveOptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🗑️ Remove Option")
        
        self.number = discord.ui.TextInput(label="Option Number to Remove", placeholder="1", max_length=2)
        self.add_item(self.number)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            idx = int(self.number.value) - 1
            if idx < 0 or idx >= len(config["tickets"]["ticket_options"]):
                await interaction.response.send_message(f"❌ Invalid number", ephemeral=True)
                return
            
            removed = config["tickets"]["ticket_options"].pop(idx)
            save_config(config)
            await interaction.response.send_message(f"✅ Removed: {removed.get('emoji', '')} {removed['label']}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class RolesSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👥 Roles Settings")
        
        support_roles = " ".join([str(rid) for rid in config["tickets"].get("support_roles", [])])
        ping_roles = " ".join([str(rid) for rid in config["tickets"].get("ping_roles", [])])
        
        self.support = discord.ui.TextInput(
            label="Support Role IDs (space separated)",
            placeholder="123456789 987654321",
            default=support_roles,
            required=False
        )
        self.add_item(self.support)
        
        self.ping = discord.ui.TextInput(
            label="Ping Role IDs (space separated)",
            placeholder="123456789 987654321",
            default=ping_roles,
            required=False
        )
        self.add_item(self.ping)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.support.value:
                config["tickets"]["support_roles"] = [int(r) for r in self.support.value.split() if r.strip()]
            if self.ping.value:
                config["tickets"]["ping_roles"] = [int(r) for r in self.ping.value.split() if r.strip()]
            
            save_config(config)
            await interaction.response.send_message("✅ Roles updated!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class MessagesEditView(discord.ui.View):
    """View for editing messages"""
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Claim Message | رسالة الاستدعاء", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def edit_claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditClaimModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Button Labels | نصوص الأزرار", emoji="🔘", style=discord.ButtonStyle.primary, row=0)
    async def edit_buttons(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditButtonsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Text Labels | النصوص", emoji="📄", style=discord.ButtonStyle.primary, row=1)
    async def edit_labels(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditLabelsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Placeholders | العبارات", emoji="💬", style=discord.ButtonStyle.primary, row=1)
    async def edit_placeholders(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditPlaceholdersModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Button Colors | ألوان الأزرار", emoji="🎨", style=discord.ButtonStyle.primary, row=2)
    async def edit_colors(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditButtonColorsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Ping Admin | زر المنشن", emoji="📢", style=discord.ButtonStyle.primary, row=3)
    async def edit_ping_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditPingAdminModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Mention Member | منشن عضو", emoji="👥", style=discord.ButtonStyle.primary, row=3)
    async def edit_mention_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMentionMemberModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Success Message | رسالة النجاح", emoji="✅", style=discord.ButtonStyle.primary, row=4)
    async def edit_success(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditSuccessMessageModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Back | رجوع", emoji="◀️", style=discord.ButtonStyle.secondary, row=4)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsCategoryView()
        embed = discord.Embed(
            title="🎫 Ticket Settings Panel | لوحة إعدادات التكيت",
            description="**Choose a category to edit: | اختر فئة للتعديل:**\n\n"
                       "🎨 **Panel | اللوحة** - Title, description, images, colors | العنوان، الوصف، الصور، الألوان\n"
                       "📋 **Options | الخيارات** - Add/edit/remove ticket options | إضافة/تعديل/حذف خيارات التكيت\n"
                       "👥 **Roles | الأدوار** - Support & ping roles | أدوار الدعم والمنشن\n"
                       "📝 **Messages | الرسائل** - All text & placeholders | جميع النصوص والعبارات\n"
                       "🎛️ **Menu | القائمة** - Dropdown menu options | خيارات القائمة المنسدلة\n"
                       "⚙️ **View | عرض** - See current settings | عرض الإعدادات الحالية",
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)

class EditButtonColorsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🎨 Button Colors")
        
        self.close_color = discord.ui.TextInput(
            label="Close Button Color",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("close_style", "danger"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.close_color)
        
        self.claim_color = discord.ui.TextInput(
            label="Claim Button Color",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("claim_style", "primary"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.claim_color)
        
        self.ping_admin_color = discord.ui.TextInput(
            label="Ping Admin Button Color",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("ping_admin_style", "secondary"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.ping_admin_color)
        
        self.mention_member_color = discord.ui.TextInput(
            label="Mention Member Button Color",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("mention_member_style", "secondary"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.mention_member_color)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.close_color.value:
                config["tickets"]["buttons"]["close_style"] = self.close_color.value
            if self.claim_color.value:
                config["tickets"]["buttons"]["claim_style"] = self.claim_color.value
            if self.ping_admin_color.value:
                config["tickets"]["buttons"]["ping_admin_style"] = self.ping_admin_color.value
            if self.mention_member_color.value:
                config["tickets"]["buttons"]["mention_member_style"] = self.mention_member_color.value
            save_config(config)
            await interaction.response.send_message("✅ Button colors updated! | تم تحديث ألوان الأزرار", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditClaimModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👥 Claim Message")
        
        self.claim_msg = discord.ui.TextInput(
            label="Claim Message (use @USER)",
            placeholder="@USER claimed the ticket",
            default=config["tickets"]["messages"].get("claim_message", "@USER استدعى الإدارة"),
            style=discord.TextStyle.short,
            max_length=200
        )
        self.add_item(self.claim_msg)
        
        self.claim_emoji = discord.ui.TextInput(
            label="Claim Emoji",
            default=config["tickets"]["messages"].get("claim_emoji", "👥"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.claim_emoji)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["messages"]["claim_message"] = self.claim_msg.value
            config["tickets"]["messages"]["claim_emoji"] = self.claim_emoji.value
            save_config(config)
            await interaction.response.send_message("✅ Claim message updated! | تم تحديث رسالة الاستدعاء", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditPingAdminModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📢 Ping Admin Button")
        
        self.ping_admin_label = discord.ui.TextInput(
            label="Button Text",
            default=config["tickets"]["buttons"].get("ping_admin", "استدعاء الإدارة"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.ping_admin_label)
        
        self.ping_admin_emoji = discord.ui.TextInput(
            label="Button Emoji (ID or emoji)",
            default=config["tickets"]["buttons"].get("ping_admin_emoji", "📢"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.ping_admin_emoji)
        
        self.ping_admin_message = discord.ui.TextInput(
            label="Message (use @ADMIN for roles)",
            placeholder="تم استدعاء الإدارة @ADMIN",
            default=config["tickets"]["messages"].get("ping_admin_message", "تم استدعاء الإدارة @ADMIN"),
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.ping_admin_message)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["buttons"]["ping_admin"] = self.ping_admin_label.value
            config["tickets"]["buttons"]["ping_admin_emoji"] = self.ping_admin_emoji.value
            config["tickets"]["messages"]["ping_admin_message"] = self.ping_admin_message.value
            save_config(config)
            await interaction.response.send_message("✅ Ping Admin button updated! | تم تحديث زر الاستدعاء", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditMentionMemberModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👥 Mention Member Button")
        
        self.mention_member_label = discord.ui.TextInput(
            label="Button Text",
            default=config["tickets"]["buttons"].get("mention_member", "منشن العضو"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.mention_member_label)
        
        self.mention_member_emoji = discord.ui.TextInput(
            label="Button Emoji (ID or emoji)",
            default=config["tickets"]["buttons"].get("mention_member_emoji", "👤"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.mention_member_emoji)
        
        self.mention_member_message = discord.ui.TextInput(
            label="Message (use @MEMBER for user)",
            placeholder="@MEMBER تفضل",
            default=config["tickets"]["messages"].get("mention_member_message", "@MEMBER تفضل"),
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.mention_member_message)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["buttons"]["mention_member"] = self.mention_member_label.value
            config["tickets"]["buttons"]["mention_member_emoji"] = self.mention_member_emoji.value
            config["tickets"]["messages"]["mention_member_message"] = self.mention_member_message.value
            save_config(config)
            await interaction.response.send_message("✅ Mention Member button updated! | تم تحديث زر منشن العضو", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditButtonsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔘 Button Settings")
        
        self.close_btn = discord.ui.TextInput(
            label="Close Button Text",
            default=config["tickets"]["buttons"].get("close", "CLOSE"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.close_btn)
        
        self.close_emoji = discord.ui.TextInput(
            label="Close Emoji (ID or emoji)",
            default=config["tickets"]["buttons"].get("close_emoji", "🔒"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.close_emoji)
        
        self.claim_btn = discord.ui.TextInput(
            label="Claim Button Text",
            default=config["tickets"]["buttons"].get("claim", "CLAIM"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.claim_btn)
        
        self.claim_btn_emoji = discord.ui.TextInput(
            label="Claim Emoji (ID or emoji)",
            default=config["tickets"]["buttons"].get("claim_emoji", "👥"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.claim_btn_emoji)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["buttons"]["close"] = self.close_btn.value
            config["tickets"]["buttons"]["close_emoji"] = self.close_emoji.value
            config["tickets"]["buttons"]["claim"] = self.claim_btn.value
            config["tickets"]["buttons"]["claim_emoji"] = self.claim_btn_emoji.value
            save_config(config)
            await interaction.response.send_message("✅ Button settings updated! | تم تحديث إعدادات الأزرار", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditLabelsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📄 Text Labels")
        
        self.reason_field = discord.ui.TextInput(
            label="Reason Field Name",
            default=config["tickets"]["messages"].get("reason_field_name", "REASON:"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.reason_field)
        
        self.by_label = discord.ui.TextInput(
            label="By Label",
            default=config["tickets"]["messages"].get("ticket_by_label", "بواسطة"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.by_label)
        
        self.by_emoji = discord.ui.TextInput(
            label="By Emoji",
            default=config["tickets"]["messages"].get("by_emoji", "👤"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.by_emoji)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["messages"]["reason_field_name"] = self.reason_field.value
            config["tickets"]["messages"]["ticket_by_label"] = self.by_label.value
            config["tickets"]["messages"]["by_emoji"] = self.by_emoji.value
            save_config(config)
            await interaction.response.send_message("✅ Text labels updated! | تم تحديث النصوص", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditPlaceholdersModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="💬 Placeholders")
        
        self.dropdown_ph = discord.ui.TextInput(
            label="Dropdown Placeholder",
            default=config["tickets"].get("dropdown_placeholder", "إضغط لفتح التكيت"),
            style=discord.TextStyle.short,
            max_length=150
        )
        self.add_item(self.dropdown_ph)
        
        self.menu_ph = discord.ui.TextInput(
            label="Menu Placeholder",
            default=config["tickets"].get("menu_placeholder", "تحديل التكيت"),
            style=discord.TextStyle.short,
            max_length=150
        )
        self.add_item(self.menu_ph)
        
        self.modal_title = discord.ui.TextInput(
            label="Modal Title",
            default=config["tickets"]["messages"].get("modal_title", "MODAL TITLE"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.modal_title)
        
        self.ticket_desc = discord.ui.TextInput(
            label="Ticket Description",
            default=config["tickets"]["messages"].get("ticket_created_desc", "YOUR MESSAGE HERE"),
            style=discord.TextStyle.paragraph,
            max_length=500
        )
        self.add_item(self.ticket_desc)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["dropdown_placeholder"] = self.dropdown_ph.value
            config["tickets"]["menu_placeholder"] = self.menu_ph.value
            config["tickets"]["messages"]["modal_title"] = self.modal_title.value
            config["tickets"]["messages"]["ticket_created_desc"] = self.ticket_desc.value
            save_config(config)
            await interaction.response.send_message("✅ Placeholders updated! | تم تحديث العبارات", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class EditSuccessMessageModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="✅ Success Message")
        
        self.success_msg = discord.ui.TextInput(
            label="Ticket Created Message (Only you see)",
            placeholder="✅ تم فتح التكيت",
            default=config["tickets"]["messages"].get("ticket_created_success", "✅ تم فتح التكيت"),
            style=discord.TextStyle.short,
            max_length=200
        )
        self.add_item(self.success_msg)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["messages"]["ticket_created_success"] = self.success_msg.value
            save_config(config)
            await interaction.response.send_message("✅ Success message updated! | تم تحديث رسالة النجاح", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class MessagesSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📝 Messages & Text (1/2)")
        
        self.dropdown_ph = discord.ui.TextInput(
            label="Dropdown Placeholder",
            default=config["tickets"].get("dropdown_placeholder", ""),
            required=False
        )
        self.add_item(self.dropdown_ph)
        
        self.menu_ph = discord.ui.TextInput(
            label="Menu Placeholder",
            default=config["tickets"].get("menu_placeholder", ""),
            required=False
        )
        self.add_item(self.menu_ph)
        
        self.modal_title = discord.ui.TextInput(
            label="Modal Title (reason window)",
            default=config["tickets"]["messages"].get("modal_title", ""),
            required=False
        )
        self.add_item(self.modal_title)
        
        self.ticket_desc = discord.ui.TextInput(
            label="Ticket Created Description",
            default=config["tickets"]["messages"].get("ticket_created_desc", ""),
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.ticket_desc)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.dropdown_ph.value:
                config["tickets"]["dropdown_placeholder"] = self.dropdown_ph.value
            if self.menu_ph.value:
                config["tickets"]["menu_placeholder"] = self.menu_ph.value
            if self.modal_title.value:
                config["tickets"]["messages"]["modal_title"] = self.modal_title.value
            if self.ticket_desc.value:
                config["tickets"]["messages"]["ticket_created_desc"] = self.ticket_desc.value
            
            save_config(config)
            
            # Show second modal for more fields
            modal2 = MessagesSettingsModal2()
            await interaction.response.send_modal(modal2)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class MessagesSettingsModal2(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📝 Messages (2/3)")
        
        self.reason_field = discord.ui.TextInput(
            label="Reason Field Name",
            default=config["tickets"]["messages"].get("reason_field_name", "REASON:"),
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.reason_field)
        
        self.claim_msg = discord.ui.TextInput(
            label="Claim Message (use @USER)",
            placeholder="@USER claimed the ticket",
            default=config["tickets"]["messages"].get("claim_message", ""),
            style=discord.TextStyle.short,
            required=False,
            max_length=200
        )
        self.add_item(self.claim_msg)
        
        self.claim_emoji = discord.ui.TextInput(
            label="Claim Emoji",
            default=config["tickets"]["messages"].get("claim_emoji", "👥"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.claim_emoji)
        
        self.by_label = discord.ui.TextInput(
            label="By Label",
            default=config["tickets"]["messages"].get("ticket_by_label", "بواسطة"),
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.by_label)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.reason_field.value:
                config["tickets"]["messages"]["reason_field_name"] = self.reason_field.value
            if self.claim_msg.value:
                config["tickets"]["messages"]["claim_message"] = self.claim_msg.value
            if self.claim_emoji.value:
                config["tickets"]["messages"]["claim_emoji"] = self.claim_emoji.value
            if self.by_label.value:
                config["tickets"]["messages"]["ticket_by_label"] = self.by_label.value
            
            save_config(config)
            
            # Show third modal for buttons and logs
            modal3 = MessagesSettingsModal3()
            await interaction.response.send_modal(modal3)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class MessagesSettingsModal3(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📝 Buttons (3/3)")
        
        self.ticket_num_text = discord.ui.TextInput(
            label="Ticket Number Text",
            default=config["tickets"]["messages"].get("ticket_number_text", "تم فتح التكيت"),
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.ticket_num_text)
        
        self.close_btn = discord.ui.TextInput(
            label="Close Button Text",
            default=config["tickets"]["buttons"].get("close", "CLOSE"),
            style=discord.TextStyle.short,
            required=False,
            max_length=80
        )
        self.add_item(self.close_btn)
        
        self.close_emoji = discord.ui.TextInput(
            label="Close Button Emoji",
            default=config["tickets"]["buttons"].get("close_emoji", "🔒"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.close_emoji)
        
        self.claim_btn = discord.ui.TextInput(
            label="Claim Button Text",
            default=config["tickets"]["buttons"].get("claim", "CLAIM"),
            style=discord.TextStyle.short,
            required=False,
            max_length=80
        )
        self.add_item(self.claim_btn)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if self.ticket_num_text.value:
                config["tickets"]["messages"]["ticket_number_text"] = self.ticket_num_text.value
            if self.close_btn.value:
                config["tickets"]["buttons"]["close"] = self.close_btn.value
            if self.close_emoji.value:
                config["tickets"]["buttons"]["close_emoji"] = self.close_emoji.value
            if self.claim_btn.value:
                config["tickets"]["buttons"]["claim"] = self.claim_btn.value
            
            save_config(config)
            await interaction.response.send_message("✅ All settings updated! Use /ticket_log_channel to set log channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class MenuOptionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Rename", emoji="✏️", style=discord.ButtonStyle.primary, row=0)
    async def rename_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("rename")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Add User", emoji="👤", style=discord.ButtonStyle.primary, row=0)
    async def add_user_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("add_user")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove User", emoji="🚫", style=discord.ButtonStyle.primary, row=0)
    async def remove_user_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("remove_user")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Reset", emoji="🔄", style=discord.ButtonStyle.primary, row=1)
    async def reset_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("reset")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Back", emoji="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsCategoryView()
        embed = discord.Embed(
            title="🎫 Ticket Settings Panel",
            description="**Choose a category to edit:**\n\n"
                       "🎨 **Panel** - Title, description, images, colors\n"
                       "📋 **Options** - Add/edit/remove ticket options\n"
                       "👥 **Roles** - Support & ping roles\n"
                       "📝 **Messages** - All text & placeholders\n"
                       "🎛️ **Menu** - Dropdown menu options\n"
                       "⚙️ **View** - See current settings",
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)

class EditMenuOptionModal(discord.ui.Modal):
    def __init__(self, option_key):
        self.option_key = option_key
        option_name = option_key.replace("_", " ").title()
        super().__init__(title=f"Edit {option_name}")
        
        menu_cfg = config["tickets"].get("menu_options", {}).get(option_key, {})
        
        self.label = discord.ui.TextInput(
            label="Label",
            default=menu_cfg.get("label", ""),
            required=False
        )
        self.add_item(self.label)
        
        self.emoji = discord.ui.TextInput(
            label="Emoji",
            default=menu_cfg.get("emoji", ""),
            required=False
        )
        self.add_item(self.emoji)
        
        self.description = discord.ui.TextInput(
            label="Description",
            default=menu_cfg.get("description", ""),
            required=False
        )
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            if "menu_options" not in config["tickets"]:
                config["tickets"]["menu_options"] = {}
            if self.option_key not in config["tickets"]["menu_options"]:
                config["tickets"]["menu_options"][self.option_key] = {}
            
            if self.label.value:
                config["tickets"]["menu_options"][self.option_key]["label"] = self.label.value
            if self.emoji.value:
                config["tickets"]["menu_options"][self.option_key]["emoji"] = self.emoji.value
            if self.description.value:
                config["tickets"]["menu_options"][self.option_key]["description"] = self.description.value
            
            save_config(config)
            await interaction.response.send_message(f"✅ Updated {self.option_key.replace('_', ' ')}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# ============================================================
# MODERATION SYSTEM
# ============================================================

def get_mod_config(guild_id):
    """Get moderation config for guild"""
    guild_cfg = get_guild_config(guild_id)
    if "moderation" not in guild_cfg:
        guild_cfg["moderation"] = {
            "enabled": True,
            "mod_log_channel": None,
            "dm_on_action": True,
            "shortcuts": {},
            "messages": {
                "ban_dm": "You have been banned from {server}. Reason: {reason}",
                "kick_dm": "You have been kicked from {server}. Reason: {reason}",
                "warn_dm": "You have been warned in {server}. Reason: {reason}",
                "timeout_dm": "You have been timed out in {server}. Duration: {duration}. Reason: {reason}",
                "ban_log": "🔨 **User Banned**",
                "kick_log": "👢 **User Kicked**",
                "warn_log": "⚠️ **User Warned**",
                "timeout_log": "⏱️ **User Timed Out**",
                "channel_locked": "🔒 **Channel Locked**",
                "channel_unlocked": "🔓 **Channel Unlocked**"
            }
        }
    return guild_cfg["moderation"]

async def send_mod_log(guild, action, moderator, target, reason, duration=None):
    """Send moderation action to log channel"""
    try:
        mod_cfg = get_mod_config(guild.id)
        if not mod_cfg.get("mod_log_channel"):
            return
        
        channel = guild.get_channel(int(mod_cfg["mod_log_channel"]))
        if not channel:
            return
        
        embed = discord.Embed(
            title=mod_cfg["messages"].get(f"{action}_log", f"**{action.upper()}**"),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=f"{target.mention} ({target.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{moderator.mention}", inline=True)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
        embed.set_footer(text=f"Made by Depex")
        
        await channel.send(embed=embed)
    except Exception as e:
        logger.error(f"Error sending mod log: {e}")

@bot.tree.command(name="ban", description="Ban a user | حظر عضو")
@app_commands.describe(user="The user to ban", reason="Reason for ban")
async def ban_user(interaction: discord.Interaction, user: discord.Member = None, reason: str = "No reason provided"):
    """Ban a user from the server"""
    try:
        if not user:
            help_embed = discord.Embed(
                title="Command: ban",
                description="**حظر المحتجر**\n**الأختصارات**\n`#حظر -حظر- طرد- حظرتلقائي- طرد- بفك`\n**الاستخدام**\n`/ban [user] (time m/h/d/mo/y) (reason)`\n\n**أمثلة للأمر:**\n`/ban @user`\n`/ban @user spamming`\n`/ban @user 1h spamming`\n`/ban @user 1d breaking rules`\n`/ban @user 1w advertising`",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحظر الأعضاء | You don't have permission to ban members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        
        # Ban user first
        await user.ban(reason=reason)
        
        # Respond to interaction
        embed = discord.Embed(
            title="🔨 تم حظر العضو | User Banned",
            description=f"{user.mention} **تم حظره**\n**السبب:** {reason}\n\n{user.mention} **has been banned**\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        
        # Then send DM
        if mod_cfg.get("dm_on_action", True):
            try:
                ban_msg = mod_cfg.get("messages", {}).get("ban_dm", "تم حظرك من {server}. السبب: {reason}\n\nYou have been banned from {server}. Reason: {reason}")
                dm_msg = ban_msg.format(
                    server=interaction.guild.name,
                    reason=reason
                )
                await user.send(dm_msg)
            except Exception as e:
                logger.error(f"Failed to send DM to {user}: {e}")
        
        await send_mod_log(interaction.guild, "ban", interaction.user, user, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ | Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a user | طرد عضو")
@app_commands.describe(user="The user to kick", reason="Reason for kick")
async def kick_user(interaction: discord.Interaction, user: discord.Member = None, reason: str = "No reason provided"):
    """Kick a user from the server"""
    try:
        if not user:
            help_embed = discord.Embed(
                title="Command: kick",
                description="**طرد العضو**\n**الأختصارات**\n`#طرد -طرد- كيك- طرد- إطرد`\n**الاستخدام**\n`/kick [user] (reason)`\n\n**أمثلة للأمر:**\n`/kick @user`\n`/kick @user spamming`\n`/kick @user inappropriate behavior`\n`/kick @user breaking rules`",
                color=discord.Color.orange()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لطرد الأعضاء | You don't have permission to kick members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        
        # Kick user first
        await user.kick(reason=reason)
        
        # Respond to interaction
        embed = discord.Embed(
            title="👢 تم طرد العضو | User Kicked",
            description=f"{user.mention} **تم طرده**\n**السبب:** {reason}\n\n{user.mention} **has been kicked**\n**Reason:** {reason}",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        
        # Then send DM
        if mod_cfg.get("dm_on_action", True):
            try:
                kick_msg = mod_cfg.get("messages", {}).get("kick_dm", "تم طردك من {server}. السبب: {reason}\n\nYou have been kicked from {server}. Reason: {reason}")
                dm_msg = kick_msg.format(
                    server=interaction.guild.name,
                    reason=reason
                )
                await user.send(dm_msg)
            except Exception as e:
                logger.error(f"Failed to send DM to {user}: {e}")
        
        await send_mod_log(interaction.guild, "kick", interaction.user, user, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ | Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a user | مهلة عضو")
@app_commands.describe(user="The user to timeout", duration="Duration in minutes", reason="Reason")
async def timeout_user(interaction: discord.Interaction, user: discord.Member = None, duration: int = None, reason: str = "No reason provided"):
    """Timeout a user"""
    try:
        if not user or not duration:
            help_embed = discord.Embed(
                title="Command: timeout",
                description="**مهلة العضو**\n**الأختصارات**\n`#مهلة -مهلة- ميوت- كتم- صامت`\n**الاستخدام**\n`/timeout [user] [duration] (reason)`\n\n**أمثلة للأمر:**\n`/timeout @user 10` (10 minutes)\n`/timeout @user 10 spamming`\n`/timeout @user 60 trolling`\n`/timeout @user 1440 breaking rules` (1 day)\n\n**Duration in minutes**",
                color=discord.Color.yellow()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ You don't have permission to timeout members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        
        # Timeout user first
        await user.timeout(discord.utils.utcnow() + discord.timedelta(minutes=duration), reason=reason)
        
        # Respond to interaction
        embed = discord.Embed(
            title="⏱️ تم كتم العضو | User Timed Out",
            description=f"{user.mention} **تم كتمه**\n**المدة:** {duration} دقيقة\n**السبب:** {reason}\n\n{user.mention} **has been timed out**\n**Duration:** {duration} minutes\n**Reason:** {reason}",
            color=discord.Color.yellow()
        )
        await interaction.response.send_message(embed=embed)
        
        # Then send DM
        if mod_cfg.get("dm_on_action", True):
            try:
                timeout_msg = mod_cfg.get("messages", {}).get("timeout_dm", "تم كتمك في {server}. المدة: {duration}. السبب: {reason}\n\nYou have been timed out in {server}. Duration: {duration}. Reason: {reason}")
                dm_msg = timeout_msg.format(
                    server=interaction.guild.name,
                    duration=f"{duration} دقيقة | {duration} minutes",
                    reason=reason
                )
                await user.send(dm_msg)
            except Exception as e:
                logger.error(f"Failed to send DM to {user}: {e}")
        
        await send_mod_log(interaction.guild, "timeout", interaction.user, user, reason, f"{duration} minutes")
        
        embed = discord.Embed(
            title="✅ User Timed Out",
            description=f"{user.mention} has been timed out\n**Duration:** {duration} minutes\n**Reason:** {reason}",
            color=discord.Color.yellow()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a user | تحذير عضو")
@app_commands.describe(user="The user to warn", reason="Reason for warning")
async def warn_user(interaction: discord.Interaction, user: discord.Member = None, reason: str = "No reason provided"):
    """Warn a user"""
    try:
        if not user:
            help_embed = discord.Embed(
                title="Command: warn",
                description="**تحذير العضو**\n**الأختصارات**\n`#تحذير -تحذير- وارن- انذار- إنذار`\n**الاستخدام**\n`/warn [user] (reason)`\n\n**أمثلة للأمر:**\n`/warn @user`\n`/warn @user be respectful`\n`/warn @user stop spamming`\n`/warn @user read the rules`",
                color=discord.Color.gold()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لتحذير الأعضاء | You don't have permission to warn members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        
        # Respond first to avoid timeout
        embed = discord.Embed(
            title="⚠️ تم تحذير العضو | User Warned",
            description=f"{user.mention} **تم تحذيره**\n**السبب:** {reason}\n\n{user.mention} **has been warned**\n**Reason:** {reason}",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)
        
        # Then send DM
        if mod_cfg.get("dm_on_action", True):
            try:
                warn_msg = mod_cfg.get("messages", {}).get("warn_dm", "تم تحذيرك في {server}. السبب: {reason}\n\nYou have been warned in {server}. Reason: {reason}")
                dm_msg = warn_msg.format(
                    server=interaction.guild.name,
                    reason=reason
                )
                await user.send(dm_msg)
            except Exception as e:
                logger.error(f"Failed to send DM to {user}: {e}")
                await interaction.followup.send(f"⚠️ تم التحذير لكن لم يتم إرسال رسالة خاصة (ربما الرسائل معطلة)\n\nWarning sent but couldn't DM user (they may have DMs disabled)", ephemeral=True)
        
        await send_mod_log(interaction.guild, "warn", interaction.user, user, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ | Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="lock", description="Lock a channel | قفل قناة")
@app_commands.describe(channel="Channel to lock", reason="Reason")
async def lock_channel(interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
    """Lock a channel"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لإدارة القنوات | You don't have permission to manage channels", ephemeral=True)
        
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False, reason=reason)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        embed = discord.Embed(
            title="🔒 تم قفل القناة | Channel Locked",
            description=f"{channel.mention} **تم قفلها**\n**السبب:** {reason}\n\n{channel.mention} **has been locked**\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        await send_mod_log(interaction.guild, "channel_locked", interaction.user, channel, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ | Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock a channel | فتح قناة")
@app_commands.describe(channel="Channel to unlock", reason="Reason")
async def unlock_channel(interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = "No reason provided"):
    """Unlock a channel"""
    try:
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لإدارة القنوات | You don't have permission to manage channels", ephemeral=True)
        
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=True, reason=reason)
        
        embed = discord.Embed(
            title="🔓 تم فتح القناة | Channel Unlocked",
            description=f"{channel.mention} **تم فتحها**\n**السبب:** {reason}\n\n{channel.mention} **has been unlocked**\n**Reason:** {reason}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        await send_mod_log(interaction.guild, "channel_unlocked", interaction.user, channel, reason)
    except Exception as e:
        await interaction.response.send_message(f"❌ خطأ | Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="clear", description="Delete messages | حذف رسائل")
@app_commands.describe(amount="Number of messages to delete")
async def clear_messages(interaction: discord.Interaction, amount: int):
    """Delete messages"""
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لإدارة الرسائل | You don't have permission to manage messages", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ تم حذف {len(deleted)} رسالة | Deleted {len(deleted)} messages", ephemeral=True)
        await interaction.followup.send(f"✅ Deleted {len(deleted)} messages", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

# Shortcut command handler
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Check for shortcuts
    if message.guild:
        mod_cfg = get_mod_config(message.guild.id)
        shortcuts = mod_cfg.get("shortcuts", {})
        
        for shortcut, action_data in shortcuts.items():
            # Check if message starts with shortcut followed by space or is exactly the shortcut
            if message.content == shortcut or message.content.startswith(shortcut + " "):
                if not message.author.guild_permissions.manage_messages:
                    continue
                
                try:
                    action = action_data.get("action")
                    
                    # Handle delete messages shortcut
                    if action == "delete":
                        # Extract number from message (e.g., "m10" -> 10)
                        parts = message.content[len(shortcut):]
                        amount = int(parts) if parts.isdigit() else int(action_data.get("default_amount", 5))
                        
                        await message.delete()
                        deleted = await message.channel.purge(limit=amount)
                        
                        notify = await message.channel.send(f"✅ Deleted {len(deleted)} messages")
                        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=3))
                        await notify.delete()
                    
                    # Handle moderation shortcuts (ban, kick, warn, timeout)
                    elif action in ["ban", "kick", "warn", "timeout"]:
                        # Parse: shortcut @user reason or shortcut @user duration reason
                        content = message.content[len(shortcut):].strip()
                        
                        if not message.mentions:
                            # Show help message
                            if action == "ban":
                                help_embed = discord.Embed(
                                    title="Command: ban",
                                    description="**حظر المحتجر**\n**الأختصارات**\n`#حظر -حظر- طرد- حظرتلقائي- طرد- بفك`\n**الاستخدام**\n`/ban [user] (time m/h/d/mo/y) (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user`\n`" + shortcut + " @user spamming`\n`" + shortcut + " @user 1h spamming`\n`" + shortcut + " @user 1d breaking rules`\n`" + shortcut + " @user 1w advertising`",
                                    color=discord.Color.red()
                                )
                            elif action == "kick":
                                help_embed = discord.Embed(
                                    title="Command: kick",
                                    description="**طرد العضو**\n**الأختصارات**\n`#طرد -طرد- كيك- طرد- إطرد`\n**الاستخدام**\n`/kick [user] (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user`\n`" + shortcut + " @user spamming`\n`" + shortcut + " @user inappropriate behavior`\n`" + shortcut + " @user breaking rules`",
                                    color=discord.Color.orange()
                                )
                            elif action == "warn":
                                help_embed = discord.Embed(
                                    title="Command: warn",
                                    description="**تحذير العضو**\n**الأختصارات**\n`#تحذير -تحذير- وارن- انذار- إنذار`\n**الاستخدام**\n`/warn [user] (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user`\n`" + shortcut + " @user be respectful`\n`" + shortcut + " @user stop spamming`\n`" + shortcut + " @user read the rules`",
                                    color=discord.Color.gold()
                                )
                            elif action == "timeout":
                                help_embed = discord.Embed(
                                    title="Command: timeout",
                                    description="**مهلة العضو**\n**الأختصارات**\n`#مهلة -مهلة- ميوت- كتم- صامت`\n**الاستخدام**\n`/timeout [user] [duration] (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user 10m`\n`" + shortcut + " @user 10m spamming`\n`" + shortcut + " @user 1h trolling`\n`" + shortcut + " @user 1d breaking rules`\n\n**Duration format:** 10s, 5m, 2h, 1d",
                                    color=discord.Color.yellow()
                                )
                            await message.channel.send(embed=help_embed, delete_after=15)
                            continue
                        
                        target = message.mentions[0]
                        
                        # Remove mention from content to get reason/duration
                        rest = content.replace(f"<@{target.id}>", "").replace(f"<@!{target.id}>", "").strip()
                        
                        if action == "ban":
                            reason = rest if rest else "No reason provided"
                            
                            # Ban user
                            await target.ban(reason=reason)
                            
                            # Send bilingual response
                            embed = discord.Embed(
                                title="🔨 تم حظر العضو | User Banned",
                                description=f"{target.mention} **تم حظره**\n**السبب:** {reason}\n\n{target.mention} **has been banned**\n**Reason:** {reason}",
                                color=discord.Color.red()
                            )
                            await message.channel.send(embed=embed, delete_after=10)
                            
                            # Send DM
                            if mod_cfg.get("dm_on_action", True):
                                try:
                                    ban_msg = mod_cfg.get("messages", {}).get("ban_dm", "تم حظرك من {server}. السبب: {reason}\n\nYou have been banned from {server}. Reason: {reason}")
                                    dm_msg = ban_msg.format(
                                        server=message.guild.name,
                                        reason=reason
                                    )
                                    await target.send(dm_msg)
                                except Exception as e:
                                    logger.error(f"Failed to send DM: {e}")
                            
                            await send_mod_log(message.guild, "ban", message.author, target, reason)
                        
                        elif action == "kick":
                            reason = rest if rest else "No reason provided"
                            
                            # Kick user
                            await target.kick(reason=reason)
                            
                            # Send bilingual response
                            embed = discord.Embed(
                                title="👢 تم طرد العضو | User Kicked",
                                description=f"{target.mention} **تم طرده**\n**السبب:** {reason}\n\n{target.mention} **has been kicked**\n**Reason:** {reason}",
                                color=discord.Color.orange()
                            )
                            await message.channel.send(embed=embed, delete_after=10)
                            
                            # Send DM
                            if mod_cfg.get("dm_on_action", True):
                                try:
                                    kick_msg = mod_cfg.get("messages", {}).get("kick_dm", "تم طردك من {server}. السبب: {reason}\n\nYou have been kicked from {server}. Reason: {reason}")
                                    dm_msg = kick_msg.format(
                                        server=message.guild.name,
                                        reason=reason
                                    )
                                    await target.send(dm_msg)
                                except Exception as e:
                                    logger.error(f"Failed to send DM: {e}")
                            
                            await send_mod_log(message.guild, "kick", message.author, target, reason)
                        
                        elif action == "warn":
                            reason = rest if rest else "No reason provided"
                            
                            # Send bilingual response
                            embed = discord.Embed(
                                title="⚠️ تم تحذير العضو | User Warned",
                                description=f"{target.mention} **تم تحذيره**\n**السبب:** {reason}\n\n{target.mention} **has been warned**\n**Reason:** {reason}",
                                color=discord.Color.gold()
                            )
                            await message.channel.send(embed=embed, delete_after=10)
                            
                            # Send DM
                            if mod_cfg.get("dm_on_action", True):
                                try:
                                    warn_msg = mod_cfg.get("messages", {}).get("warn_dm", "تم تحذيرك في {server}. السبب: {reason}\n\nYou have been warned in {server}. Reason: {reason}")
                                    dm_msg = warn_msg.format(
                                        server=message.guild.name,
                                        reason=reason
                                    )
                                    await target.send(dm_msg)
                                except Exception as e:
                                    logger.error(f"Failed to send DM: {e}")
                            
                            await send_mod_log(message.guild, "warn", message.author, target, reason)
                        
                        elif action == "timeout":
                            # Parse duration and reason
                            parts = rest.split(" ", 1)
                            duration_str = parts[0] if parts else "10m"
                            reason = parts[1] if len(parts) > 1 else "No reason provided"
                            
                            # Parse duration (e.g., "10m", "1h", "30s")
                            import re
                            match = re.match(r"(\d+)([smhd])", duration_str)
                            if match:
                                value, unit = match.groups()
                                value = int(value)
                                if unit == 's':
                                    duration = discord.timedelta(seconds=value)
                                    duration_minutes = value / 60
                                elif unit == 'm':
                                    duration = discord.timedelta(minutes=value)
                                    duration_minutes = value
                                elif unit == 'h':
                                    duration = discord.timedelta(hours=value)
                                    duration_minutes = value * 60
                                elif unit == 'd':
                                    duration = discord.timedelta(days=value)
                                    duration_minutes = value * 1440
                            else:
                                duration = discord.timedelta(minutes=10)
                                duration_minutes = 10
                            
                            # Timeout user
                            await target.timeout(duration, reason=reason)
                            
                            # Send bilingual response
                            embed = discord.Embed(
                                title="⏱️ تم كتم العضو | User Timed Out",
                                description=f"{target.mention} **تم كتمه**\n**المدة:** {duration_str}\n**السبب:** {reason}\n\n{target.mention} **has been timed out**\n**Duration:** {duration_str}\n**Reason:** {reason}",
                                color=discord.Color.yellow()
                            )
                            await message.channel.send(embed=embed, delete_after=10)
                            
                            # Send DM
                            if mod_cfg.get("dm_on_action", True):
                                try:
                                    timeout_msg = mod_cfg.get("messages", {}).get("timeout_dm", "تم كتمك في {server}. المدة: {duration}. السبب: {reason}\n\nYou have been timed out in {server}. Duration: {duration}. Reason: {reason}")
                                    dm_msg = timeout_msg.format(
                                        server=message.guild.name,
                                        duration=duration_str,
                                        reason=reason
                                    )
                                    await target.send(dm_msg)
                                except Exception as e:
                                    logger.error(f"Failed to send DM: {e}")
                            
                            await send_mod_log(message.guild, "timeout", message.author, target, reason, duration_str)
                        
                        await message.delete()
                    
                except Exception as e:
                    logger.error(f"Shortcut error: {e}")
                    await message.channel.send(f"❌ Error: {str(e)}", delete_after=5)
    
    await bot.process_commands(message)

class ModSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Ban", emoji="🔨", style=discord.ButtonStyle.danger, row=0)
    async def ban_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BanSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Kick", emoji="👢", style=discord.ButtonStyle.danger, row=0)
    async def kick_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = KickSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Warn", emoji="⚠️", style=discord.ButtonStyle.primary, row=0)
    async def warn_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WarnSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Timeout", emoji="⏱️", style=discord.ButtonStyle.primary, row=0)
    async def timeout_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TimeoutSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Log Channel", emoji="📝", style=discord.ButtonStyle.secondary, row=1)
    async def log_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModLogModal()
        await interaction.response.send_modal(modal)

class BanSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔨 Ban Settings")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Message (use {server}, {reason})",
            placeholder="You have been banned from {server}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut (optional, e.g., 'b', 'ban')",
            placeholder="b",
            style=discord.TextStyle.short,
            required=False,
            max_length=20
        )
        self.add_item(self.shortcut)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "messages" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["messages"] = {}
            if "shortcuts" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["shortcuts"] = {}
            
            if self.dm_msg.value:
                guild_cfg["moderation"]["messages"]["ban_dm"] = self.dm_msg.value
            
            if self.shortcut.value:
                guild_cfg["moderation"]["shortcuts"][self.shortcut.value] = {
                    "action": "ban",
                    "command": "ban"
                }
            
            update_guild_config(interaction.guild_id, guild_cfg)
            msg = f"✅ Ban settings updated!"
            if self.shortcut.value:
                msg += f"\n**Shortcut:** Type `{self.shortcut.value}` + mention user (e.g., `{self.shortcut.value} @user reason`)"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class KickSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👢 Kick Settings")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Message (use {server}, {reason})",
            placeholder="You have been kicked from {server}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut (optional, e.g., 'k', 'kick')",
            placeholder="k",
            style=discord.TextStyle.short,
            required=False,
            max_length=20
        )
        self.add_item(self.shortcut)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "messages" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["messages"] = {}
            if "shortcuts" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["shortcuts"] = {}
            
            if self.dm_msg.value:
                guild_cfg["moderation"]["messages"]["kick_dm"] = self.dm_msg.value
            
            if self.shortcut.value:
                guild_cfg["moderation"]["shortcuts"][self.shortcut.value] = {
                    "action": "kick",
                    "command": "kick"
                }
            
            update_guild_config(interaction.guild_id, guild_cfg)
            msg = f"✅ Kick settings updated!"
            if self.shortcut.value:
                msg += f"\n**Shortcut:** Type `{self.shortcut.value}` + mention user (e.g., `{self.shortcut.value} @user reason`)"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class WarnSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="⚠️ Warn Settings")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Message (use {server}, {reason})",
            placeholder="You have been warned in {server}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut (optional, e.g., 'w', 'warn')",
            placeholder="w",
            style=discord.TextStyle.short,
            required=False,
            max_length=20
        )
        self.add_item(self.shortcut)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "messages" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["messages"] = {}
            if "shortcuts" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["shortcuts"] = {}
            
            if self.dm_msg.value:
                guild_cfg["moderation"]["messages"]["warn_dm"] = self.dm_msg.value
            
            if self.shortcut.value:
                guild_cfg["moderation"]["shortcuts"][self.shortcut.value] = {
                    "action": "warn",
                    "command": "warn"
                }
            
            update_guild_config(interaction.guild_id, guild_cfg)
            msg = f"✅ Warn settings updated!"
            if self.shortcut.value:
                msg += f"\n**Shortcut:** Type `{self.shortcut.value}` + mention user (e.g., `{self.shortcut.value} @user reason`)"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class TimeoutSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="⏱️ Timeout Settings")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Message (use {server}, {reason}, {duration})",
            placeholder="You have been timed out. Duration: {duration}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut (optional, e.g., 't', 'mute')",
            placeholder="t",
            style=discord.TextStyle.short,
            required=False,
            max_length=20
        )
        self.add_item(self.shortcut)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "messages" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["messages"] = {}
            if "shortcuts" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["shortcuts"] = {}
            
            if self.dm_msg.value:
                guild_cfg["moderation"]["messages"]["timeout_dm"] = self.dm_msg.value
            
            if self.shortcut.value:
                guild_cfg["moderation"]["shortcuts"][self.shortcut.value] = {
                    "action": "timeout",
                    "command": "timeout"
                }
            
            update_guild_config(interaction.guild_id, guild_cfg)
            msg = f"✅ Timeout settings updated!"
            if self.shortcut.value:
                msg += f"\n**Shortcut:** Type `{self.shortcut.value}` + mention user + duration (e.g., `{self.shortcut.value} @user 10m reason`)"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class ModMessagesModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Moderation Messages")
        guild_cfg = get_guild_config(None)
        mod_cfg = guild_cfg.get("moderation", {})
        msgs = mod_cfg.get("messages", {})
        
        self.ban_dm = discord.ui.TextInput(label="Ban DM Message", default=msgs.get("ban_dm", ""), style=discord.TextStyle.paragraph, required=False)
        self.add_item(self.ban_dm)
        
        self.kick_dm = discord.ui.TextInput(label="Kick DM Message", default=msgs.get("kick_dm", ""), style=discord.TextStyle.paragraph, required=False)
        self.add_item(self.kick_dm)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "messages" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["messages"] = {}
            
            if self.ban_dm.value:
                guild_cfg["moderation"]["messages"]["ban_dm"] = self.ban_dm.value
            if self.kick_dm.value:
                guild_cfg["moderation"]["messages"]["kick_dm"] = self.kick_dm.value
            
            update_guild_config(interaction.guild_id, guild_cfg)
            await interaction.response.send_message("✅ Moderation messages updated!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

class ModLogModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Set Log Channel")
        
        self.channel = discord.ui.TextInput(label="Log Channel ID", placeholder="1234567890", required=False)
        self.add_item(self.channel)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            
            guild_cfg["moderation"]["mod_log_channel"] = self.channel.value
            update_guild_config(interaction.guild_id, guild_cfg)
            await interaction.response.send_message(f"✅ Log channel set to <#{self.channel.value}>", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="mod_setup", description="Open moderation settings panel | فتح لوحة إعدادات الإشراف")
async def mod_setup(interaction: discord.Interaction):
    """Open moderation settings panel"""
    try:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ You need Administrator permission", ephemeral=True)
        
        view = ModSettingsView()
        embed = discord.Embed(
            title="⚙️ Moderation Settings Panel",
            description="**Configure each action with custom shortcuts:**\n\n"
                       "🔨 **Ban** - Message & shortcut\n"
                       "👢 **Kick** - Message & shortcut\n"
                       "⚠️ **Warn** - Message & shortcut\n"
                       "⏱️ **Timeout** - Message & shortcut\n"
                       "📝 **Log Channel** - Set mod log channel\n\n"
                       "**Shortcut Usage:**\n"
                       "• Set any text as shortcut (e.g., `k`, `ban`, `w`)\n"
                       "• Type: `shortcut @user reason`\n"
                       "• Example: `k @user spamming`\n\n"
                       "**Available Slash Commands:**\n"
                       "`/ban` `/kick` `/timeout` `/warn` `/lock` `/unlock` `/clear`",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Made by Depex © 2026")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

# Run the bot
try:
    # Use environment variable for token
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    bot.run(token)
except Exception as e:
    logger.error(f"Bot error: {e}", exc_info=True)
