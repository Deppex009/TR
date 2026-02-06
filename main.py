import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
import asyncio
import random
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Deploy marker (helps confirm Discloud pulled latest code)
DEPLOY_MARKER = "2026-02-05T00:00Z"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Presence rotation
PRESENCE_ROTATE_SECONDS = 10
PRESENCE_ROTATE_TEXTS = [
    "By Dep-A7",
    "https://discord.gg/0tr",
]
# Discord doesn't support smooth animations; this is a tiny in-between text.
PRESENCE_TRANSITION_ENABLED = True
PRESENCE_TRANSITION_SECONDS = 0.7

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
                },
                "voice_247": {
                    "enabled": False,
                    "channel_id": None,
                    "self_mute": True,
                    "self_deaf": True,
                },
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
            },
            "voice_247": {
                "enabled": False,
                "channel_id": None,
                "self_mute": True,
                "self_deaf": True,
            },
        }
    
    # Update with new values
    full_config["servers"][guild_id_str].update(updates)
    save_config(full_config)


def get_ticket_config(guild_id: int):
    """Get ticket config for a guild and ensure required defaults exist."""
    guild_cfg = get_guild_config(guild_id)

    changed = False
    if "tickets" not in guild_cfg or not isinstance(guild_cfg.get("tickets"), dict):
        guild_cfg["tickets"] = {}
        changed = True

    tcfg = guild_cfg["tickets"]

    def _set_default(key, value):
        nonlocal changed
        if key not in tcfg:
            tcfg[key] = value
            changed = True

    _set_default("category_id", None)
    _set_default("log_channel_id", None)
    _set_default("admin_role_id", None)
    _set_default("embed_color", "#9B59B6")
    _set_default("panel_embed_color", "#9B59B6")
    _set_default("ticket_embed_color", "#9B59B6")
    _set_default("panel_title", "🎫 Tickets | التكيت")
    _set_default("panel_description", "اختر نوع التكيت من القائمة أدناه | Choose a ticket type below")
    _set_default("dropdown_placeholder", "إضغط لفتح التكيت")
    _set_default("menu_placeholder", "تعديل التكيت")
    _set_default("panel_image", "")
    _set_default("panel_author_icon", "")
    _set_default("panel_author_name", "Ticket System")
    _set_default("ticket_image", "")
    _set_default("reason_image", "")
    _set_default("ticket_counter", 0)
    _set_default("support_roles", [])
    _set_default("ping_roles", [])

    if "ticket_options" not in tcfg or not isinstance(tcfg.get("ticket_options"), list) or not tcfg.get("ticket_options"):
        tcfg["ticket_options"] = [
            {"label": "Support | دعم", "description": "الدعم الفني والمساعدة", "emoji": "🎫"},
            {"label": "Report | بلاغ", "description": "الإبلاغ عن مشكلة أو عضو", "emoji": "🚨"},
        ]
        changed = True

    if "buttons" not in tcfg or not isinstance(tcfg.get("buttons"), dict):
        tcfg["buttons"] = {}
        changed = True
    if "messages" not in tcfg or not isinstance(tcfg.get("messages"), dict):
        tcfg["messages"] = {}
        changed = True
    if "menu_options" not in tcfg or not isinstance(tcfg.get("menu_options"), dict):
        tcfg["menu_options"] = {}
        changed = True

    # Buttons defaults
    btn = tcfg["buttons"]
    btn_defaults = {
        "close": "CLOSE",
        "close_emoji": "🔒",
        "close_style": "danger",
        "claim": "CLAIM",
        "claim_emoji": "👥",
        "claim_style": "primary",
        "ping_admin": "استدعاء الإدارة",
        "ping_admin_emoji": "📢",
        "ping_admin_style": "secondary",
        "mention_member": "منشن العضو",
        "mention_member_emoji": "👤",
        "mention_member_style": "secondary",
    }
    for k, v in btn_defaults.items():
        if k not in btn:
            btn[k] = v
            changed = True

    # Messages defaults
    msg = tcfg["messages"]
    msg_defaults = {
        "modal_title": "فتح تذكرة",
        "reason_label": "السبب",
        "modal_placeholder": "اذكر سبب فتح للتذكره :",
        "ticket_created_title": "فتح تذكرة",
        "ticket_created_desc": "✅ تم فتح التكيت بنجاح",
        "ticket_created_success": "✅ تم فتح التكيت",
        "ticket_by_label": "بواسطة",
        "by_emoji": "👤",
        "reason_field_name": "السبب:",
        "footer_text": "",
        "ping_admin_message": "تم استدعاء الإدارة @ADMIN",
        "mention_member_message": "@MEMBER تفضل",
        "claim_message": "@USER استدعى الإدارة",
        "claim_emoji": "👥",
        "log_ticket_opened": "📬 Ticket Opened",
        "log_opened_by": "Opened By",
        "log_channel": "Channel",
        "log_reason": "Reason",
        "log_ticket_closed": "🔒 Ticket Closed",
        "log_closed_by": "Closed By",
        "log_ticket_claimed": "👥 Ticket Claimed",
        "log_claimed_by": "Claimed By",
    }
    for k, v in msg_defaults.items():
        if k not in msg:
            msg[k] = v
            changed = True

    # Menu option defaults
    menu = tcfg["menu_options"]
    menu_defaults = {
        "rename": {"label": "Rename", "emoji": "✏️", "description": "تغيير اسم التكيت"},
        "add_user": {"label": "Add User", "emoji": "👤", "description": "اضافة عضو للتكيت"},
        "remove_user": {"label": "Remove User", "emoji": "🚫", "description": "إزالة عضو من التكيت"},
        "reset": {"label": "Reset Menu", "emoji": "🔄", "description": "إعادة تعيين القائمة"},
    }
    for k, v in menu_defaults.items():
        if k not in menu:
            menu[k] = v
            changed = True

    if changed:
        update_guild_config(guild_id, guild_cfg)

    return tcfg

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

def _coerce_component_emoji(value):
    """Accept unicode emoji, custom emoji strings, or raw IDs for UI components."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    # Normalize common wrappers like <a:name:id> or <:name:id>
    candidate = raw.strip()
    if candidate.startswith("<") and candidate.endswith(">"):
        candidate = candidate[1:-1].strip()

    # Try custom emoji formats: a:name:id, name:id
    if ":" in candidate:
        parts = candidate.split(":")
        if len(parts) == 3 and parts[0] == "a":
            name, emoji_id = parts[1], parts[2]
            if emoji_id.isdigit():
                return discord.PartialEmoji(name=name or "emoji", id=int(emoji_id), animated=True)
        if len(parts) == 2:
            name, emoji_id = parts[0], parts[1]
            if emoji_id.isdigit():
                return discord.PartialEmoji(name=name or "emoji", id=int(emoji_id), animated=False)

    # Raw emoji ID
    if re.fullmatch(r"\d{15,25}", candidate):
        return discord.PartialEmoji(name="emoji", id=int(candidate))

    # If it looks like a custom emoji but failed parsing, drop it.
    if ":" in raw or raw.startswith("<"):
        return None

    # Fallback to unicode emoji
    return raw


def _parse_bool_text(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    v = str(value).strip().lower()
    if v in ("1", "true", "yes", "y", "on", "enable", "enabled"):
        return True
    if v in ("0", "false", "no", "n", "off", "disable", "disabled"):
        return False
    return default


def get_auto_replies_config(guild_id: int) -> list[dict]:
    guild_cfg = get_guild_config(guild_id)
    changed = False
    if "auto_replies" not in guild_cfg or not isinstance(guild_cfg.get("auto_replies"), list):
        guild_cfg["auto_replies"] = []
        changed = True
    if changed:
        update_guild_config(guild_id, guild_cfg)
    return guild_cfg["auto_replies"]


def get_channel_auto_config(guild_id: int) -> list[dict]:
    guild_cfg = get_guild_config(guild_id)
    changed = False
    if "channel_auto" not in guild_cfg or not isinstance(guild_cfg.get("channel_auto"), list):
        guild_cfg["channel_auto"] = []
        changed = True
    if changed:
        update_guild_config(guild_id, guild_cfg)
    return guild_cfg["channel_auto"]


def _matches_trigger(message_content: str, trigger: str, *, match_type: str, case_sensitive: bool) -> bool:
    message_content = (message_content or "").strip()
    trigger = (trigger or "").strip()

    if not case_sensitive:
        message_content = message_content.lower()
        trigger = trigger.lower()

    match_type = (match_type or "contains").strip().lower()
    if match_type == "exact":
        return message_content == trigger
    if match_type == "startswith":
        return message_content.startswith(trigger)
    if match_type == "endswith":
        return message_content.endswith(trigger)
    # default: contains
    return trigger in message_content


def _normalize_match_type(value: str | None) -> str:
    v = (value or "contains").strip().lower()
    if v in ("contains", "exact", "startswith", "endswith"):
        return v
    return "contains"


def _normalize_reply_mode(value: str | None) -> str:
    v = (value or "send").strip().lower()
    if v in ("send", "reply"):
        return v
    return "send"


def _parse_role_ids_from_text(text: str | None) -> list[int]:
    """Parse role IDs from a string.

    Accepts role mentions (<@&id>) or raw IDs. Separators: space/comma/semicolon.
    """
    if not text:
        return []
    raw = str(text)
    ids: list[int] = []

    # Mentions
    for m in re.findall(r"<@&(?P<id>\d{5,25})>", raw):
        try:
            ids.append(int(m))
        except Exception:
            pass

    # Raw IDs
    for m in re.findall(r"\b\d{5,25}\b", raw):
        try:
            ids.append(int(m))
        except Exception:
            pass

    # Unique, keep order
    seen: set[int] = set()
    out: list[int] = []
    for rid in ids:
        if rid in seen:
            continue
        seen.add(rid)
        out.append(rid)
    return out


def _member_has_any_role(member: discord.Member, role_ids: list[int]) -> bool:
    if not role_ids:
        return True
    try:
        role_set = set(int(x) for x in role_ids)
        return any(r.id in role_set for r in getattr(member, "roles", []))
    except Exception:
        return False


def _build_autoreply_panel_embed(guild: discord.Guild, items: list[dict], *, page: int = 0, page_size: int = 8) -> discord.Embed:
    embed = discord.Embed(
        title="💬 Auto Replies Panel | لوحة الردود التلقائية",
        description=(
            "Manage auto replies for this server.\n"
            "- **Trigger** = word/sentence\n"
            "- **Mode** = `send` (normal message) or `reply` (reply to user)\n\n"
            "- **Roles** = limit replies to specific roles (set via Options)\n\n"
            "إدارة الردود التلقائية لهذا السيرفر.\n"
            "- **Roles | الرتب** = تحديد الرد لرتب معينة (من خانة Options)"
        ),
        color=discord.Color.blurple(),
    )
    if not items:
        embed.add_field(name="No auto replies | لا يوجد", value="Use **Add** to create one | استخدم **إضافة**", inline=False)
        return embed

    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(int(page), total_pages - 1))

    start = page * page_size
    end = min(total, start + page_size)

    lines: list[str] = []
    for idx in range(start, end):
        r = items[idx] or {}
        enabled = "✅" if r.get("enabled", True) else "❌"
        match_type = _normalize_match_type(r.get("match"))
        mode = _normalize_reply_mode(r.get("mode"))
        mention = "@" if r.get("mention", False) else "-"
        case = "Aa" if r.get("case_sensitive", False) else "aa"
        allowed_roles = r.get("allowed_role_ids")
        if not isinstance(allowed_roles, list):
            allowed_roles = []
        role_tag = "all" if not allowed_roles else str(len(allowed_roles))
        trig = str(r.get("trigger", "")).strip() or "(empty)"
        rep = str(r.get("reply", "")).strip() or "(empty)"
        if len(rep) > 140:
            rep = rep[:137] + "..."
        lines.append(f"`{idx+1}` {enabled} `[{match_type} | {mode} | {mention} | {case} | R:{role_tag}]`\n**{trig}** → {rep}")

    embed.add_field(
        name=f"Rules | القواعد ({start+1}-{end} / {total})",
        value="\n\n".join(lines),
        inline=False,
    )
    embed.set_footer(text=f"Server: {guild.name} • Page {page+1}/{total_pages}")
    return embed


class AutoReplyAddModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Add Auto Reply | إضافة رد")
        self.guild_id = int(guild_id)

        self.trigger = discord.ui.TextInput(
            label="Trigger | كلمة",
            placeholder="hi / مرحبا",
            required=True,
            max_length=200,
        )
        self.add_item(self.trigger)

        self.reply = discord.ui.TextInput(
            label="Reply | رد",
            placeholder="welcome! / اهلاً",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
        )
        self.add_item(self.reply)

        self.match = discord.ui.TextInput(
            label="Match | مطابقة",
            placeholder="contains / exact / startswith / endswith",
            required=False,
            max_length=20,
        )
        self.add_item(self.match)

        self.mode = discord.ui.TextInput(
            label="Mode | وضع",
            placeholder="send / reply",
            required=False,
            max_length=10,
        )
        self.add_item(self.mode)

        # NOTE: Discord modals allow max 5 inputs.
        # Put mention + case_sensitive + roles in one field.
        self.options = discord.ui.TextInput(
            label="Options | خيارات",
            placeholder="mention=no case=no roles=all",
            required=False,
            max_length=60,
        )
        self.add_item(self.options)

    async def on_submit(self, interaction: discord.Interaction):
        opt = (self.options.value or "").strip().lower()
        mention = _parse_bool_text("yes" if "mention=yes" in opt else "no" if "mention=no" in opt else None, False)
        case_sensitive = _parse_bool_text("yes" if "case=yes" in opt else "no" if "case=no" in opt else None, False)

        role_ids: list[int] = []
        m = re.search(r"roles\s*=\s*(.+)", opt, flags=re.IGNORECASE)
        if m:
            roles_value = (m.group(1) or "").strip()
            if roles_value and roles_value not in ("all", "any", "none"):
                role_ids = _parse_role_ids_from_text(roles_value)

        items = get_auto_replies_config(interaction.guild_id)
        items.append(
            {
                "trigger": self.trigger.value.strip(),
                "reply": self.reply.value.strip(),
                "match": _normalize_match_type(self.match.value),
                "mode": _normalize_reply_mode(self.mode.value),
                "mention": mention,
                "case_sensitive": case_sensitive,
                "allowed_role_ids": role_ids,
                "enabled": True,
            }
        )
        update_guild_config(interaction.guild_id, {"auto_replies": items})
        await interaction.response.send_message("✅ Auto reply added | تم إضافة الرد", ephemeral=True)


class AutoReplyEditModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Edit Auto Reply | تعديل رد")
        self.guild_id = int(guild_id)

        self.index = discord.ui.TextInput(
            label="Rule # | رقم",
            placeholder="1",
            required=True,
            max_length=5,
        )
        self.add_item(self.index)

        self.trigger = discord.ui.TextInput(
            label="Trigger | كلمة",
            placeholder="(blank = keep) / (اتركه فارغ)",
            required=False,
            max_length=200,
        )
        self.add_item(self.trigger)

        self.reply = discord.ui.TextInput(
            label="Reply | رد",
            placeholder="(blank = keep) / (اتركه فارغ)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1500,
        )
        self.add_item(self.reply)

        self.options = discord.ui.TextInput(
            label="Options | خيارات",
            placeholder="match=contains mode=send mention=no case=no roles=all",
            required=False,
            max_length=120,
        )
        self.add_item(self.options)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            items = get_auto_replies_config(interaction.guild_id)
            try:
                idx = int(self.index.value.strip())
            except Exception:
                return await interaction.response.send_message("❌ Invalid number.", ephemeral=True)

            if idx < 1 or idx > len(items):
                return await interaction.response.send_message("❌ Out of range.", ephemeral=True)

            i = idx - 1
            rule = items[i] or {}

            if self.trigger.value and self.trigger.value.strip():
                rule["trigger"] = self.trigger.value.strip()
            if self.reply.value and self.reply.value.strip():
                rule["reply"] = self.reply.value.strip()

            opt = (self.options.value or "").strip()
            if opt:
                # very small parser: key=value pairs
                pairs = re.findall(r"(match|mode|mention|case)\s*=\s*([^\s]+)", opt, flags=re.IGNORECASE)
                kv = {k.lower(): v for k, v in pairs}
                if "match" in kv:
                    rule["match"] = _normalize_match_type(kv.get("match"))
                if "mode" in kv:
                    rule["mode"] = _normalize_reply_mode(kv.get("mode"))
                if "mention" in kv:
                    rule["mention"] = _parse_bool_text(kv.get("mention"), bool(rule.get("mention", False)))
                if "case" in kv:
                    rule["case_sensitive"] = _parse_bool_text(kv.get("case"), bool(rule.get("case_sensitive", False)))

                # roles: should be last if using spaces; commas recommended
                m = re.search(r"roles\s*=\s*(.+)", opt, flags=re.IGNORECASE)
                if m:
                    roles_value = (m.group(1) or "").strip()
                    if not roles_value or roles_value.lower() in ("all", "any", "none"):
                        rule["allowed_role_ids"] = []
                    else:
                        rule["allowed_role_ids"] = _parse_role_ids_from_text(roles_value)

            # Ensure defaults exist
            rule["match"] = _normalize_match_type(rule.get("match"))
            rule["mode"] = _normalize_reply_mode(rule.get("mode"))
            rule["enabled"] = bool(rule.get("enabled", True))
            if not isinstance(rule.get("allowed_role_ids"), list):
                rule["allowed_role_ids"] = []

            items[i] = rule
            update_guild_config(interaction.guild_id, {"auto_replies": items})
            await interaction.response.send_message(f"✅ Updated rule {idx} | تم التعديل", ephemeral=True)
        except Exception as e:
            logger.error(f"AutoReplyEditModal error: {e}")
            try:
                await interaction.response.send_message("❌ Error while editing | خطأ أثناء التعديل", ephemeral=True)
            except Exception:
                pass


class AutoReplyTestModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Test Auto Reply | اختبار")
        self.guild_id = int(guild_id)
        self.text = discord.ui.TextInput(
            label="Test text | نص",
            placeholder="type... / اكتب...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            items = get_auto_replies_config(interaction.guild_id)
            content = self.text.value

            for idx, rule in enumerate(items, start=1):
                if not rule or not rule.get("enabled", True):
                    continue

                allowed_roles = rule.get("allowed_role_ids")
                if isinstance(allowed_roles, list) and allowed_roles:
                    if not _member_has_any_role(interaction.user, allowed_roles):
                        continue
                trigger = str(rule.get("trigger", "")).strip()
                reply = str(rule.get("reply", "")).strip()
                if not trigger or not reply:
                    continue

                if _matches_trigger(
                    content,
                    trigger,
                    match_type=_normalize_match_type(rule.get("match")),
                    case_sensitive=bool(rule.get("case_sensitive", False)),
                ):
                    mention = bool(rule.get("mention", False))
                    mode = _normalize_reply_mode(rule.get("mode"))
                    preview = f"{interaction.user.mention} {reply}" if mention else reply
                    embed = discord.Embed(
                        title="✅ Match Found | تم العثور",
                        description=f"Rule | رقم: `{idx}`\nOptions | خيارات: `{rule.get('match','contains')}` / `{mode}` / mention={mention}",
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Trigger | كلمة", value=trigger[:1024], inline=False)
                    embed.add_field(name="Bot would send | سيرسل", value=preview[:1024], inline=False)
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

            await interaction.response.send_message("❌ No match | لا يوجد تطابق", ephemeral=True)
        except Exception as e:
            logger.error(f"AutoReplyTestModal error: {e}")
            try:
                await interaction.response.send_message("❌ Error while testing | خطأ أثناء الاختبار", ephemeral=True)
            except Exception:
                pass


class AutoReplyIndexModal(discord.ui.Modal):
    def __init__(self, guild_id: int, mode: str):
        title_map = {
            "remove": "Remove | حذف",
            "toggle": "Toggle | تفعيل",
        }
        super().__init__(title=f"Auto Reply | رد: {title_map.get(mode, mode.title())}")
        self.guild_id = int(guild_id)
        self.mode = mode

        self.index = discord.ui.TextInput(
            label="Rule # | رقم",
            placeholder="1",
            required=True,
            max_length=5,
        )
        self.add_item(self.index)

    async def on_submit(self, interaction: discord.Interaction):
        items = get_auto_replies_config(interaction.guild_id)
        try:
            idx = int(self.index.value)
        except Exception:
            return await interaction.response.send_message("❌ Invalid number | رقم خطأ", ephemeral=True)

        if idx < 1 or idx > len(items):
            return await interaction.response.send_message("❌ Out of range | خارج النطاق", ephemeral=True)

        i = idx - 1
        if self.mode == "remove":
            removed = items.pop(i)
            update_guild_config(interaction.guild_id, {"auto_replies": items})
            return await interaction.response.send_message(f"✅ Removed | تم الحذف: {removed.get('trigger')}", ephemeral=True)

        if self.mode == "toggle":
            items[i]["enabled"] = not items[i].get("enabled", True)
            update_guild_config(interaction.guild_id, {"auto_replies": items})
            state = "enabled" if items[i]["enabled"] else "disabled"
            return await interaction.response.send_message(f"✅ Toggled | تم التفعيل {idx} ({state})", ephemeral=True)

        await interaction.response.send_message("❌ Unknown action | أمر غير معروف", ephemeral=True)


class AutoReplyRolesModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Roles | الرتب")
        self.guild_id = int(guild_id)

        self.index = discord.ui.TextInput(
            label="Rule # | رقم",
            placeholder="1",
            required=True,
            max_length=5,
        )
        self.add_item(self.index)

        self.roles = discord.ui.TextInput(
            label="Roles | رتب",
            placeholder="all  OR  123,456  OR  <@&123>,<@&456>",
            required=True,
            max_length=180,
        )
        self.add_item(self.roles)

    async def on_submit(self, interaction: discord.Interaction):
        items = get_auto_replies_config(interaction.guild_id)
        try:
            idx = int(self.index.value.strip())
        except Exception:
            return await interaction.response.send_message("❌ Invalid number | رقم خطأ", ephemeral=True)

        if idx < 1 or idx > len(items):
            return await interaction.response.send_message("❌ Out of range | خارج النطاق", ephemeral=True)

        value = (self.roles.value or "").strip()
        rule = items[idx - 1] or {}
        if not value or value.lower() in ("all", "any", "none"):
            rule["allowed_role_ids"] = []
        else:
            rule["allowed_role_ids"] = _parse_role_ids_from_text(value)

        if not isinstance(rule.get("allowed_role_ids"), list):
            rule["allowed_role_ids"] = []

        items[idx - 1] = rule
        update_guild_config(interaction.guild_id, {"auto_replies": items})
        role_tag = "all" if not rule.get("allowed_role_ids") else str(len(rule.get("allowed_role_ids")))
        await interaction.response.send_message(f"✅ Roles updated | تم تحديث الرتب ({idx}) (R:{role_tag})", ephemeral=True)


class AutoReplyPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        # Longer timeout to avoid 'Interaction failed' from expired panels.
        super().__init__(timeout=3600)
        self.guild_id = int(guild_id)
        self.page = 0

    async def _refresh(self, interaction: discord.Interaction):
        items = get_auto_replies_config(interaction.guild_id)
        embed = _build_autoreply_panel_embed(interaction.guild, items, page=self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Add | إضافة", style=discord.ButtonStyle.success, row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(AutoReplyAddModal(self.guild_id))

    @discord.ui.button(label="Edit | تعديل", style=discord.ButtonStyle.primary, row=0)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(AutoReplyEditModal(self.guild_id))

    @discord.ui.button(label="Roles | رتب", style=discord.ButtonStyle.secondary, row=0)
    async def roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(AutoReplyRolesModal(self.guild_id))

    @discord.ui.button(label="Remove | حذف", style=discord.ButtonStyle.danger, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(AutoReplyIndexModal(self.guild_id, "remove"))

    @discord.ui.button(label="Toggle | تفعيل", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(AutoReplyIndexModal(self.guild_id, "toggle"))

    @discord.ui.button(label="Test | تجربة", style=discord.ButtonStyle.secondary, row=1)
    async def test_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(AutoReplyTestModal(self.guild_id))

    @discord.ui.button(label="Prev | السابق", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await self._refresh(interaction)

    @discord.ui.button(label="Next | التالي", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        items = get_auto_replies_config(interaction.guild_id)
        total_pages = max(1, (len(items) + 8 - 1) // 8)
        self.page = min(total_pages - 1, self.page + 1)
        await self._refresh(interaction)

    @discord.ui.button(label="Refresh | تحديث", style=discord.ButtonStyle.secondary, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)


def _build_channel_auto_panel_embed(guild: discord.Guild, items: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="📌 Channel Auto Panel | لوحة الردود في القنوات",
        description=(
            "When someone sends a message in a configured channel, the bot replies and can react.\n\n"
            "عند إرسال رسالة في قناة محددة، البوت يرد ويمكنه إضافة تفاعلات."
        ),
        color=discord.Color.green(),
    )
    if not items:
        embed.add_field(
            name="No channel rules | لا توجد قواعد",
            value="Use **Add | إضافة** to create one. | استخدم **Add | إضافة** لإضافة قاعدة.",
            inline=False,
        )
        return embed

    lines = []
    for i, r in enumerate(items[:25], start=1):
        enabled = "✅" if r.get("enabled", True) else "❌"
        channel_id = r.get("channel_id")
        mention = "@" if r.get("mention", False) else "-"
        reactions = " ".join(r.get("reactions", []) or [])
        rep = str(r.get("reply", ""))
        if len(rep) > 60:
            rep = rep[:57] + "..."
        ch_text = f"<#{channel_id}>" if channel_id else "(no channel | بدون قناة)"
        lines.append(f"`{i}` {enabled} [{mention}] {ch_text} → {rep} | {reactions}")
    embed.add_field(name="Rules", value="\n".join(lines), inline=False)
    embed.set_footer(text=f"Server: {guild.name}")
    return embed


class ChannelAutoAddModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Add Rule | إضافة قاعدة")
        self.guild_id = int(guild_id)

        self.channel = discord.ui.TextInput(
            label="Channel mention/ID | منشن/معرف",
            placeholder="#general أو 1234567890",
            required=True,
            max_length=60,
        )
        self.add_item(self.channel)

        self.reply = discord.ui.TextInput(
            label="Reply text | نص الرد",
            placeholder="Thanks! | شكرًا!",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
        )
        self.add_item(self.reply)

        self.reactions = discord.ui.TextInput(
            label="Reactions (space) | تفاعلات",
            placeholder="✅ 🔥",
            required=False,
            max_length=200,
        )
        self.add_item(self.reactions)

        self.mention = discord.ui.TextInput(
            label="Mention? yes/no | منشن؟",
            placeholder="no",
            required=False,
            max_length=10,
        )
        self.add_item(self.mention)

        self.enabled = discord.ui.TextInput(
            label="Enabled? yes/no | مفعل؟",
            placeholder="yes",
            required=False,
            max_length=10,
        )
        self.add_item(self.enabled)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Server only | للسيرفر فقط", ephemeral=True)

        raw = self.channel.value.strip()
        m = re.search(r"(\d{5,})", raw)
        if not m:
            return await interaction.response.send_message("❌ Invalid channel | قناة غير صحيحة", ephemeral=True)
        channel_id = int(m.group(1))
        channel_obj = interaction.guild.get_channel(channel_id)
        if not channel_obj:
            return await interaction.response.send_message(
                "❌ Channel not found | القناة غير موجودة في هذا السيرفر",
                ephemeral=True,
            )

        items = get_channel_auto_config(interaction.guild_id)
        reactions = [e.strip() for e in (self.reactions.value or "").split() if e.strip()]
        items.append(
            {
                "channel_id": channel_id,
                "reply": self.reply.value.strip(),
                "mention": _parse_bool_text(self.mention.value, False),
                "reactions": reactions,
                "enabled": _parse_bool_text(self.enabled.value, True),
            }
        )
        update_guild_config(interaction.guild_id, {"channel_auto": items})
        await interaction.response.send_message("✅ Rule added | تم إضافة القاعدة", ephemeral=True)


class ChannelAutoIndexModal(discord.ui.Modal):
    def __init__(self, guild_id: int, mode: str):
        ar = {"remove": "حذف", "toggle": "تفعيل"}.get(str(mode).lower(), "إجراء")
        super().__init__(title=f"{mode.title()} | {ar}")
        self.guild_id = int(guild_id)
        self.mode = mode

        self.index = discord.ui.TextInput(
            label="Rule # (panel) | رقم القاعدة",
            placeholder="1",
            required=True,
            max_length=5,
        )
        self.add_item(self.index)

    async def on_submit(self, interaction: discord.Interaction):
        items = get_channel_auto_config(interaction.guild_id)
        try:
            idx = int(self.index.value)
        except Exception:
            return await interaction.response.send_message("❌ Invalid number | رقم غير صحيح", ephemeral=True)

        if idx < 1 or idx > len(items):
            return await interaction.response.send_message("❌ Out of range | خارج النطاق", ephemeral=True)

        i = idx - 1
        if self.mode == "remove":
            removed = items.pop(i)
            update_guild_config(interaction.guild_id, {"channel_auto": items})
            return await interaction.response.send_message(
                f"✅ Removed | تم الحذف: <#{removed.get('channel_id')}>",
                ephemeral=True,
            )

        if self.mode == "toggle":
            items[i]["enabled"] = not items[i].get("enabled", True)
            update_guild_config(interaction.guild_id, {"channel_auto": items})
            state = "enabled | مفعل" if items[i]["enabled"] else "disabled | معطل"
            return await interaction.response.send_message(
                f"✅ Toggled | تم التفعيل/التعطيل: {idx} ({state})",
                ephemeral=True,
            )

        await interaction.response.send_message("❌ Unknown action | إجراء غير معروف", ephemeral=True)


class ChannelAutoPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = int(guild_id)

    async def _refresh(self, interaction: discord.Interaction):
        items = get_channel_auto_config(interaction.guild_id)
        embed = _build_channel_auto_panel_embed(interaction.guild, items)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Add | إضافة", style=discord.ButtonStyle.success, row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(ChannelAutoAddModal(self.guild_id))

    @discord.ui.button(label="Remove | حذف", style=discord.ButtonStyle.danger, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(ChannelAutoIndexModal(self.guild_id, "remove"))

    @discord.ui.button(label="Toggle | تفعيل", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(ChannelAutoIndexModal(self.guild_id, "toggle"))

    @discord.ui.button(label="Refresh | تحديث", style=discord.ButtonStyle.secondary, row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)

# Giveaway helpers
GIVEAWAY_DURATION_REGEX = re.compile(r"^(\d+)(s|m|h|d|w)$", re.IGNORECASE)
_giveaway_watcher_task: asyncio.Task | None = None


def _parse_giveaway_duration_seconds(duration_str: str | None) -> int | None:
    if not duration_str:
        return None
    duration_str = str(duration_str).strip().lower()
    match = GIVEAWAY_DURATION_REGEX.match(duration_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return amount * multipliers[unit]
    if duration_str.isdigit():
        return int(duration_str) * 60
    return None


def get_giveaway_config(guild_id: int) -> dict:
    guild_cfg = get_guild_config(guild_id)
    gw = guild_cfg.get("giveaway")
    if not isinstance(gw, dict):
        gw = {}

    changed = False
    defaults = {
        "channel_id": None,
        "host_role_ids": [],
        "reaction_emoji": "🎉",
        "embed_color": gw.get("color") if isinstance(gw.get("color"), str) else "#5865F2",
        "image_url": gw.get("image_url") if isinstance(gw.get("image_url"), str) else "",
        # Optional content shown above the embed (same message content)
        "above_message": "",
        # Optional user shortcut word (type it in chat). Empty = disabled.
        "shortcut_word": "",
        "title_template": "🎁 {guild} Giveaways | سحوبات {guild}",
        "react_line_template": "✨ React With {reaction} To Enter | تفاعل بـ {reaction} للدخول",
        "prize_line_template": "🎁 Prize : {prize} | الجائزة : {prize}",
        "host_line_template": "👑 Hosted By : {host} | المستضيف : {host}",
        "end_line_template": "Winner(s): {winners} • Ends: {ends_at} | الفائزون: {winners} • ينتهي: {ends_at}",
        "ended_line_template": "Winner(s): {winners} • Ended: {ended_at} | الفائزون: {winners} • انتهى: {ended_at}",
        "winners_line_template": "Winners: {winner_mentions} | الفائزون: {winner_mentions}",
        "active": [],
    }

    for k, v in defaults.items():
        if k not in gw:
            gw[k] = v
            changed = True

    # Back-compat keys
    if "emoji" in gw and "reaction_emoji" not in gw:
        gw["reaction_emoji"] = gw.get("emoji")
        changed = True
    if "color" in gw and "embed_color" not in gw and isinstance(gw.get("color"), str):
        gw["embed_color"] = gw.get("color")
        changed = True

    # Migrate old shortcut toggle -> shortcut word
    if "shortcut_word" not in gw:
        if gw.get("shortcut_enabled", True):
            gw["shortcut_word"] = "gstart"
        else:
            gw["shortcut_word"] = ""
        changed = True
    if "shortcut_enabled" in gw:
        # keep config clean
        try:
            gw.pop("shortcut_enabled", None)
        except Exception:
            pass
        changed = True

    # Ensure types
    if not isinstance(gw.get("host_role_ids"), list):
        gw["host_role_ids"] = []
        changed = True
    if not isinstance(gw.get("active"), list):
        gw["active"] = []
        changed = True

    if changed:
        update_guild_config(guild_id, {"giveaway": gw})
    return gw


def _safe_format(template: str, **kwargs) -> str:
    try:
        return str(template).format(**kwargs)
    except Exception:
        return str(template)


def build_giveaway_embed(
    *,
    guild: discord.Guild,
    giveaway_cfg: dict,
    prize: str,
    host_mention: str,
    end_ts: int,
    winners_count: int,
    ended: bool = False,
    winner_mentions: str | None = None,
) -> discord.Embed:
    reaction = giveaway_cfg.get("reaction_emoji", "🎉")
    title = _safe_format(giveaway_cfg.get("title_template"), guild=guild.name)

    ends_at = f"<t:{int(end_ts)}:F> (<t:{int(end_ts)}:R>)"
    ended_at = f"<t:{int(end_ts)}:F>"

    react_line = _safe_format(giveaway_cfg.get("react_line_template"), reaction=reaction)
    prize_line = _safe_format(giveaway_cfg.get("prize_line_template"), prize=prize)
    host_line = _safe_format(giveaway_cfg.get("host_line_template"), host=host_mention)

    if ended:
        end_line = _safe_format(
            giveaway_cfg.get("ended_line_template"),
            winners=winners_count,
            ended_at=ended_at,
        )
    else:
        end_line = _safe_format(
            giveaway_cfg.get("end_line_template"),
            winners=winners_count,
            ends_at=ends_at,
        )

    lines = [react_line, prize_line, host_line, "", end_line]
    if ended:
        winners_line = _safe_format(
            giveaway_cfg.get("winners_line_template"),
            winner_mentions=(winner_mentions or "—"),
        )
        lines += [winners_line]

    embed = discord.Embed(
        title=title,
        description="\n".join(lines),
        color=parse_color(giveaway_cfg.get("embed_color", "#5865F2")),
    )
    if giveaway_cfg.get("image_url"):
        embed.set_image(url=str(giveaway_cfg.get("image_url")))
    embed.set_footer(text=guild.name)
    return embed


async def _giveaway_end_one(guild_id: int, record: dict):
    try:
        channel_id = int(record.get("channel_id"))
        message_id = int(record.get("message_id"))
        end_ts = int(record.get("end_ts"))
        prize = str(record.get("prize", ""))
        winners_count = int(record.get("winners", 1))
        host_id = int(record.get("host_id"))
        reaction_emoji = str(record.get("reaction_emoji") or "🎉")
    except Exception:
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            return

    try:
        message = await channel.fetch_message(message_id)
    except Exception:
        return

    guild = message.guild
    giveaway_cfg = get_giveaway_config(guild_id)
    giveaway_cfg["reaction_emoji"] = reaction_emoji

    # Gather entries from reactions
    entries: list[int] = []
    try:
        target_reaction = None
        for r in message.reactions:
            if str(r.emoji) == reaction_emoji:
                target_reaction = r
                break

        if target_reaction is not None:
            async for user in target_reaction.users(limit=None):
                if user.bot:
                    continue
                entries.append(int(user.id))
    except Exception:
        entries = []

    # Dedup while preserving order
    seen: set[int] = set()
    entries = [x for x in entries if not (x in seen or seen.add(x))]

    if not entries:
        winners_ids: list[int] = []
    else:
        winners_ids = random.sample(entries, k=min(max(1, winners_count), len(entries)))

    winner_mentions = " ".join(f"<@{uid}>" for uid in winners_ids) if winners_ids else "—"
    host_member = guild.get_member(host_id) or guild.me
    host_mention = host_member.mention if host_member else f"<@{host_id}>"

    ended_embed = build_giveaway_embed(
        guild=guild,
        giveaway_cfg=giveaway_cfg,
        prize=prize,
        host_mention=host_mention,
        end_ts=end_ts,
        winners_count=winners_count,
        ended=True,
        winner_mentions=winner_mentions,
    )

    try:
        await message.edit(embed=ended_embed)
    except Exception:
        pass

    try:
        if winners_ids:
            await channel.send(
                f"🎉 **Winners | الفائزون:** {winner_mentions}\n"
                f"**Prize | الجائزة:** {prize}"
            )
        else:
            await channel.send(
                f"❌ No valid entries | لا توجد مشاركات صحيحة\n"
                f"**Prize | الجائزة:** {prize}"
            )
    except Exception:
        pass


async def _giveaway_watcher_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now_ts = int(datetime.utcnow().timestamp())
        for g in list(getattr(bot, "guilds", []) or []):
            try:
                gw = get_giveaway_config(g.id)
                active = list(gw.get("active") or [])
                if not active:
                    continue

                remaining: list[dict] = []
                changed = False
                for record in active:
                    try:
                        end_ts = int(record.get("end_ts"))
                    except Exception:
                        end_ts = 0

                    if end_ts and end_ts <= now_ts:
                        await _giveaway_end_one(g.id, record)
                        changed = True
                    else:
                        remaining.append(record)

                if changed:
                    gw["active"] = remaining
                    update_guild_config(g.id, {"giveaway": gw})
            except Exception:
                continue

        await asyncio.sleep(15)


def _giveaway_user_can_host(member: discord.Member, giveaway_cfg: dict) -> bool:
    role_ids = giveaway_cfg.get("host_role_ids") or []
    if role_ids:
        return _member_has_any_role(member, [int(x) for x in role_ids])
    return bool(member.guild_permissions.manage_guild)


def _build_giveaway_settings_embed(guild: discord.Guild, giveaway_cfg: dict) -> discord.Embed:
    host_roles = giveaway_cfg.get("host_role_ids") or []
    if host_roles:
        host_roles_text = " ".join(f"<@&{int(rid)}>" for rid in host_roles)
    else:
        host_roles_text = "Manage Server | إدارة السيرفر"

    channel_id = giveaway_cfg.get("channel_id")
    channel_text = f"<#{int(channel_id)}>" if channel_id else "Current channel | نفس القناة"

    embed = discord.Embed(
        title="🎁 Giveaway Settings | إعدادات السحب",
        description="Configure giveaway style + hosting permissions.\n\nإعداد شكل السحب وصلاحيات الاستضافة.",
        color=parse_color(giveaway_cfg.get("embed_color", "#5865F2")),
    )
    embed.add_field(name="Host Roles | رتب الاستضافة", value=host_roles_text, inline=False)
    embed.add_field(name="Default Channel | القناة", value=channel_text, inline=False)
    embed.add_field(name="Reaction Emoji | ايموجي التفاعل", value=str(giveaway_cfg.get("reaction_emoji", "🎉")), inline=True)
    embed.add_field(name="Embed Color | اللون", value=str(giveaway_cfg.get("embed_color", "#5865F2")), inline=True)

    img = str(giveaway_cfg.get("image_url") or "")
    embed.add_field(name="Image | الصورة", value=(img if img else "(none) | لا يوجد"), inline=False)

    above = str(giveaway_cfg.get("above_message") or "").strip()
    embed.add_field(name="Above Message | رسالة فوق", value=(above if above else "(none) | لا يوجد"), inline=False)

    shortcut_word = str(giveaway_cfg.get("shortcut_word") or "").strip()
    embed.add_field(
        name="Shortcut Word | كلمة اختصار",
        value=(f"`{shortcut_word}`" if shortcut_word else "(disabled) | معطل"),
        inline=False,
    )

    embed.add_field(
        name="Templates | التنسيق",
        value=(
            "Use {guild} {reaction} {prize} {host} {winners} {ends_at}\n"
            "استخدم {guild} {reaction} {prize} {host} {winners} {ends_at}"
        ),
        inline=False,
    )
    embed.set_footer(text=guild.name)
    return embed


class GiveawayHostRolesModal(discord.ui.Modal, title="Host Roles | رتب الاستضافة"):
    roles = discord.ui.TextInput(
        label="Roles (mentions/IDs) | الرتب",
        placeholder="@Role1 @Role2 أو 123...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        gw["host_role_ids"] = _parse_role_ids_from_text(self.roles.value)
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawayReactionEmojiModal(discord.ui.Modal, title="Reaction Emoji | ايموجي التفاعل"):
    emoji = discord.ui.TextInput(
        label="Emoji | ايموجي",
        placeholder="🎉 or <:name:id>",
        required=True,
        max_length=64,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        gw["reaction_emoji"] = str(self.emoji.value).strip()
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawayTemplatesModal(discord.ui.Modal, title="Templates | التنسيق"):
    title_template = discord.ui.TextInput(
        label="Title | العنوان",
        default="🎁 {guild} Giveaways | سحوبات {guild}",
        required=False,
        max_length=200,
    )
    react_line = discord.ui.TextInput(
        label="React line | سطر التفاعل",
        default="✨ React With {reaction} To Enter | تفاعل بـ {reaction} للدخول",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=400,
    )
    prize_line = discord.ui.TextInput(
        label="Prize line | سطر الجائزة",
        default="🎁 Prize : {prize} | الجائزة : {prize}",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=400,
    )
    host_line = discord.ui.TextInput(
        label="Host line | سطر المستضيف",
        default="👑 Hosted By : {host} | المستضيف : {host}",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=400,
    )
    end_line = discord.ui.TextInput(
        label="End line | سطر النهاية",
        default="Winner(s): {winners} • Ends: {ends_at} | الفائزون: {winners} • ينتهي: {ends_at}",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=400,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        if str(self.title_template.value or "").strip():
            gw["title_template"] = str(self.title_template.value)
        if str(self.react_line.value or "").strip():
            gw["react_line_template"] = str(self.react_line.value)
        if str(self.prize_line.value or "").strip():
            gw["prize_line_template"] = str(self.prize_line.value)
        if str(self.host_line.value or "").strip():
            gw["host_line_template"] = str(self.host_line.value)
        if str(self.end_line.value or "").strip():
            gw["end_line_template"] = str(self.end_line.value)
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawayAboveMessageModal(discord.ui.Modal, title="Above Message | رسالة فوق"):
    message = discord.ui.TextInput(
        label="Message (optional) | الرسالة",
        placeholder="@everyone ...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=1500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        gw["above_message"] = str(self.message.value or "").strip()
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawayShortcutWordModal(discord.ui.Modal, title="Shortcut Word | كلمة اختصار"):
    word = discord.ui.TextInput(
        label="Word (empty = disable) | كلمة (فارغ لتعطيل)",
        placeholder="giveaway / سحب / gstart",
        required=False,
        max_length=30,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        raw = str(self.word.value or "").strip()
        # Basic validation: no spaces, no leading '/', keep it simple.
        if raw and (" " in raw or raw.startswith("/")):
            return await interaction.response.send_message(
                "❌ Invalid shortcut word (no spaces, no /) | كلمة غير صالحة",
                ephemeral=True,
            )
        gw["shortcut_word"] = raw
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawayOpenFormView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Giveaway Form | فتح النموذج",
        style=discord.ButtonStyle.success,
        emoji="🎁",
        custom_id="giveaway:open_form",
    )
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw = get_giveaway_config(interaction.guild_id)
        if not _giveaway_user_can_host(interaction.user, gw):
            return await interaction.response.send_message(
                "❌ You can't host giveaways | لا يمكنك استضافة سحوبات",
                ephemeral=True,
            )
        await interaction.response.send_modal(GiveawayCreateModal())


class GiveawayEmbedModal(discord.ui.Modal, title="Embed Settings | إعدادات الإيمبد"):
    color = discord.ui.TextInput(
        label="Color (#RRGGBB) | اللون",
        placeholder="#5865F2",
        required=False,
        max_length=32,
    )
    image_url = discord.ui.TextInput(
        label="Image URL | رابط الصورة",
        placeholder="https://...",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=400,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        if self.color.value and str(self.color.value).strip():
            gw["embed_color"] = str(self.color.value).strip()
        if self.image_url.value is not None:
            gw["image_url"] = str(self.image_url.value).strip()
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawayChannelModal(discord.ui.Modal, title="Default Channel | القناة الافتراضية"):
    channel = discord.ui.TextInput(
        label="Channel mention/ID | منشن/ايدي",
        placeholder="#giveaways or 123...",
        required=False,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        val = str(self.channel.value or "").strip()
        channel_id = None
        if val:
            m = re.search(r"<#(?P<id>\d{5,25})>", val)
            if m:
                channel_id = int(m.group("id"))
            else:
                m2 = re.search(r"\b\d{5,25}\b", val)
                if m2:
                    channel_id = int(m2.group(0))

        gw["channel_id"] = channel_id
        update_guild_config(interaction.guild_id, {"giveaway": gw})
        await interaction.response.send_message("✅ Updated | تم التحديث", ephemeral=True)


class GiveawaySettingsView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = int(guild_id)

    async def _refresh(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        settings_embed = _build_giveaway_settings_embed(interaction.guild, gw)
        preview_embed = build_giveaway_embed(
            guild=interaction.guild,
            giveaway_cfg=gw,
            prize="2M",
            host_mention=interaction.user.mention,
            end_ts=int(datetime.utcnow().timestamp()) + 3600,
            winners_count=1,
            ended=False,
        )
        await interaction.response.edit_message(embeds=[settings_embed, preview_embed], view=self)

    @discord.ui.button(label="Host Roles | رتب", style=discord.ButtonStyle.primary, row=0)
    async def host_roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayHostRolesModal())

    @discord.ui.button(label="Reaction | تفاعل", style=discord.ButtonStyle.primary, row=0)
    async def reaction_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayReactionEmojiModal())

    @discord.ui.button(label="Templates | تنسيق", style=discord.ButtonStyle.secondary, row=0)
    async def templates_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayTemplatesModal())

    @discord.ui.button(label="Embed | إيمبد", style=discord.ButtonStyle.secondary, row=1)
    async def embed_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayEmbedModal())

    @discord.ui.button(label="Channel | قناة", style=discord.ButtonStyle.secondary, row=1)
    async def channel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayChannelModal())

    @discord.ui.button(label="Upload Image | رفع", style=discord.ButtonStyle.success, row=1)
    async def upload_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)

        await interaction.response.send_message(
            "📷 Send an image **now** in this channel (60s) | ارسل الصورة الآن في نفس القناة (60 ثانية)",
            ephemeral=True,
        )

        def check(msg: discord.Message):
            return (
                msg.guild
                and msg.guild.id == interaction.guild_id
                and msg.author.id == interaction.user.id
                and msg.channel.id == interaction.channel_id
                and msg.attachments
            )

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            return

        att = msg.attachments[0]
        gw = get_giveaway_config(interaction.guild_id)
        gw["image_url"] = att.url
        update_guild_config(interaction.guild_id, {"giveaway": gw})

        try:
            await interaction.followup.send("✅ Image updated | تم تحديث الصورة", ephemeral=True)
        except Exception:
            pass

    @discord.ui.button(label="Message | رسالة", style=discord.ButtonStyle.success, row=2)
    async def message_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayAboveMessageModal())

    @discord.ui.button(label="Shortcut Word | اختصار", style=discord.ButtonStyle.primary, row=2)
    async def shortcut_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        await interaction.response.send_modal(GiveawayShortcutWordModal())

    @discord.ui.button(label="Refresh | تحديث", style=discord.ButtonStyle.secondary, row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)


class GiveawayCreateModal(discord.ui.Modal, title="Giveaway | سحب"):
    prize = discord.ui.TextInput(label="Prize | الجائزة", placeholder="Nitro / 2M / Role", max_length=200)
    winners = discord.ui.TextInput(label="Winners | عدد الفائزين", default="1", max_length=3)
    duration = discord.ui.TextInput(label="Duration (10m,2h,1d) | المدة", default="1h", max_length=20)
    channel = discord.ui.TextInput(
        label="Channel (optional) | قناة (اختياري)",
        required=False,
        placeholder="#giveaways or 123...",
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        gw = get_giveaway_config(interaction.guild_id)
        if not _giveaway_user_can_host(interaction.user, gw):
            return await interaction.response.send_message(
                "❌ You can't host giveaways | لا يمكنك استضافة سحوبات",
                ephemeral=True,
            )

        seconds = _parse_giveaway_duration_seconds(self.duration.value)
        if not seconds or seconds <= 0:
            return await interaction.response.send_message(
                "❌ Duration format: 10s, 5m, 2h, 1d | صيغة المدة: 10s 5m 2h 1d",
                ephemeral=True,
            )

        try:
            winners_count = int(str(self.winners.value).strip())
        except Exception:
            winners_count = 1
        winners_count = max(1, min(50, winners_count))

        # Resolve channel
        target_channel = None
        val = str(self.channel.value or "").strip()
        if val:
            m = re.search(r"<#(?P<id>\d{5,25})>", val)
            if m:
                target_channel = interaction.guild.get_channel(int(m.group("id")))
            else:
                m2 = re.search(r"\b\d{5,25}\b", val)
                if m2:
                    target_channel = interaction.guild.get_channel(int(m2.group(0)))

        if target_channel is None and gw.get("channel_id"):
            target_channel = interaction.guild.get_channel(int(gw.get("channel_id")))
        if target_channel is None:
            target_channel = interaction.channel

        reaction_emoji = str(gw.get("reaction_emoji", "🎉"))
        end_ts = int(datetime.utcnow().timestamp()) + int(seconds)
        embed = build_giveaway_embed(
            guild=interaction.guild,
            giveaway_cfg=gw,
            prize=str(self.prize.value),
            host_mention=interaction.user.mention,
            end_ts=end_ts,
            winners_count=winners_count,
            ended=False,
        )

        above = str(gw.get("above_message") or "").strip()
        if above:
            above = _safe_format(
                above,
                guild=interaction.guild.name,
                reaction=reaction_emoji,
                prize=str(self.prize.value),
                host=interaction.user.mention,
                winners=winners_count,
            )

        message = await target_channel.send(content=(above if above else None), embed=embed)
        try:
            await message.add_reaction(reaction_emoji)
        except Exception:
            try:
                await message.add_reaction("🎉")
                reaction_emoji = "🎉"
            except Exception:
                pass

        active = list(gw.get("active") or [])
        active.append(
            {
                "message_id": int(message.id),
                "channel_id": int(target_channel.id),
                "end_ts": int(end_ts),
                "winners": int(winners_count),
                "prize": str(self.prize.value),
                "host_id": int(interaction.user.id),
                "reaction_emoji": str(reaction_emoji),
            }
        )
        gw["active"] = active
        update_guild_config(interaction.guild_id, {"giveaway": gw})

        await interaction.response.send_message("✅ Giveaway started | تم بدء السحب", ephemeral=True)


@bot.tree.command(name="giveaway", description="Start a giveaway (form) | بدء سحب (نموذج)")
async def giveaway_cmd(interaction: discord.Interaction):
    gw = get_giveaway_config(interaction.guild_id)
    if not _giveaway_user_can_host(interaction.user, gw):
        return await interaction.response.send_message(
            "❌ You can't host giveaways | لا يمكنك استضافة سحوبات",
            ephemeral=True,
        )
    await interaction.response.send_modal(GiveawayCreateModal())


@bot.tree.command(name="givaway", description="Start a giveaway (form) | بدء سحب (نموذج)")
async def givaway_cmd(interaction: discord.Interaction):
    await giveaway_cmd(interaction)


@bot.tree.command(name="gstart", description="Giveaway shortcut (form) | اختصار السحب")
async def gstart_cmd(interaction: discord.Interaction):
    return await giveaway_cmd(interaction)


@bot.tree.command(name="giveaway_panel", description="Open giveaway settings panel | فتح لوحة إعدادات السحب")
async def giveaway_panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)

    gw = get_giveaway_config(interaction.guild_id)
    settings_embed = _build_giveaway_settings_embed(interaction.guild, gw)
    preview_embed = build_giveaway_embed(
        guild=interaction.guild,
        giveaway_cfg=gw,
        prize="2M",
        host_mention=interaction.user.mention,
        end_ts=int(datetime.utcnow().timestamp()) + 3600,
        winners_count=1,
        ended=False,
    )
    await interaction.response.send_message(
        embeds=[settings_embed, preview_embed],
        view=GiveawaySettingsView(interaction.guild_id),
        ephemeral=True,
    )


# ---------------- Voice 24/7 (AFK) ----------------

_voice247_task: asyncio.Task | None = None
_voice247_locks: dict[int, asyncio.Lock] = {}
_voice247_next_attempt_at: dict[int, float] = {}
_voice247_backoff_seconds: dict[int, float] = {}
_voice247_suppress_until: dict[int, float] = {}
_voice247_manual_until: dict[int, float] = {}


def _voice247_lock_for(guild_id: int) -> asyncio.Lock:
    gid = int(guild_id)
    if gid not in _voice247_locks:
        _voice247_locks[gid] = asyncio.Lock()
    return _voice247_locks[gid]


def _voice247_now() -> float:
    try:
        return asyncio.get_running_loop().time()
    except Exception:
        return 0.0


def _voice247_clear_retry_state(guild_id: int):
    gid = int(guild_id)
    _voice247_next_attempt_at.pop(gid, None)
    _voice247_backoff_seconds.pop(gid, None)


def _voice247_set_manual_window(guild_id: int, seconds: float = 6.0):
    gid = int(guild_id)
    now = _voice247_now()
    if not now:
        return
    _voice247_manual_until[gid] = now + float(seconds)


def get_voice247_config(guild_id: int) -> dict:
    guild_cfg = get_guild_config(guild_id)
    v = guild_cfg.get("voice_247")
    if not isinstance(v, dict):
        v = {}

    changed = False
    defaults = {
        "enabled": False,
        "channel_id": None,
        # "mic" in UI: mic ON => self_mute False
        "self_mute": True,
        "self_deaf": True,
    }
    for k, dv in defaults.items():
        if k not in v:
            v[k] = dv
            changed = True

    if changed:
        update_guild_config(guild_id, {"voice_247": v})
    return v


async def _voice247_ensure_connected(guild: discord.Guild, *, force: bool = False, reason: str = ""):
    gid = int(guild.id)
    now = _voice247_now()

    # If we explicitly suppressed attempts (e.g. after Disable), do nothing.
    if not force and now and now < float(_voice247_suppress_until.get(gid, 0.0)):
        return

    # If a user just pressed Join/Disable, avoid the loop/event fighting it.
    if not force and now and now < float(_voice247_manual_until.get(gid, 0.0)):
        return

    cfg = get_voice247_config(guild.id)
    if not cfg.get("enabled"):
        _voice247_clear_retry_state(gid)
        return

    channel_id = cfg.get("channel_id")
    if not channel_id:
        return

    channel = guild.get_channel(int(channel_id))
    if channel is None or not isinstance(channel, discord.VoiceChannel):
        return

    # Respect backoff to prevent join/leave spam on handshake failures.
    if not force:
        next_at = float(_voice247_next_attempt_at.get(gid, 0.0))
        if now and now < next_at:
            return

    lock = _voice247_lock_for(gid)
    async with lock:
        now = _voice247_now()
        if not force:
            next_at = float(_voice247_next_attempt_at.get(gid, 0.0))
            if now and now < next_at:
                return

        cfg = get_voice247_config(guild.id)
        if not cfg.get("enabled"):
            _voice247_clear_retry_state(gid)
            return

        # channel can be deleted/changed while we wait on the lock; re-resolve.
        channel_id = cfg.get("channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(int(channel_id))
        if channel is None or not isinstance(channel, discord.VoiceChannel):
            return

        vc = guild.voice_client

        # If a VoiceClient exists but is stale/disconnected, discord.py may block connect()
        # with "Already connected". Clean it up first.
        if vc is not None:
            try:
                if vc.is_connected():
                    if vc.channel and int(vc.channel.id) != int(channel.id):
                        try:
                            await vc.move_to(channel)
                        except Exception:
                            try:
                                await vc.disconnect(force=True)
                            except Exception:
                                pass
                            vc = None

                    # Enforce mute/deaf (best-effort)
                    try:
                        await guild.change_voice_state(
                            channel=channel,
                            self_mute=bool(cfg.get("self_mute", True)),
                            self_deaf=bool(cfg.get("self_deaf", True)),
                        )
                    except Exception:
                        pass

                    # If we were able to stay connected (or moved), we're done.
                    if guild.voice_client and guild.voice_client.is_connected():
                        _voice247_clear_retry_state(gid)
                        return

                # Stale/connecting client -> force disconnect so connect() works
                try:
                    await vc.disconnect(force=True)
                except Exception:
                    pass
                vc = None
            except Exception:
                pass

        try:
            await channel.connect(
                self_mute=bool(cfg.get("self_mute", True)),
                self_deaf=bool(cfg.get("self_deaf", True)),
            )
            _voice247_clear_retry_state(gid)
            return
        except discord.ClientException as e:
            # Fallback: if discord.py still thinks we're connected, try move_to
            if "already connected" in str(e).lower():
                try:
                    vc2 = guild.voice_client
                    if vc2 and vc2.channel and int(vc2.channel.id) != int(channel.id):
                        await vc2.move_to(channel)
                    _voice247_clear_retry_state(gid)
                    return
                except Exception:
                    pass

            backoff = float(_voice247_backoff_seconds.get(gid, 10.0))
            backoff = min(300.0, max(10.0, backoff * 1.7))
            _voice247_backoff_seconds[gid] = backoff
            _voice247_next_attempt_at[gid] = _voice247_now() + backoff
            logger.error(f"Voice247 connect error (guild {guild.id}) [{reason}]: {e}")
        except Exception as e:
            backoff = float(_voice247_backoff_seconds.get(gid, 10.0))
            backoff = min(300.0, max(10.0, backoff * 1.7))
            _voice247_backoff_seconds[gid] = backoff
            _voice247_next_attempt_at[gid] = _voice247_now() + backoff
            logger.error(f"Voice247 connect error (guild {guild.id}) [{reason}]: {e}")


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Keep the bot in the configured 24/7 voice channel even if kicked/moved."""
    try:
        if not bot.user or int(member.id) != int(bot.user.id):
            return
        if not member.guild:
            return

        cfg = get_voice247_config(member.guild.id)
        if not cfg.get("enabled"):
            return

        target_id = cfg.get("channel_id")
        if not target_id:
            return

        # If kicked/disconnected OR moved to another channel, go back (but respect backoff).
        moved_or_kicked = (after.channel is None) or (int(after.channel.id) != int(target_id))
        if moved_or_kicked:
            await asyncio.sleep(1.0)
            await _voice247_ensure_connected(member.guild, force=False, reason="voice_state")
    except Exception:
        pass


async def _voice247_loop():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            for g in list(getattr(bot, "guilds", []) or []):
                try:
                    await _voice247_ensure_connected(g)
                except Exception:
                    continue
        except Exception:
            pass
        await asyncio.sleep(30)


def _voice247_panel_embed(guild: discord.Guild, cfg: dict) -> discord.Embed:
    channel_id = cfg.get("channel_id")
    channel_text = f"<#{int(channel_id)}>" if channel_id else "❌ Not set | غير محدد"
    enabled = "✅ ON | شغال" if cfg.get("enabled") else "⛔ OFF | متوقف"
    mic = "✅ ON | شغال" if not cfg.get("self_mute", True) else "❌ OFF | مطفي"
    deaf = "✅ ON | شغال" if cfg.get("self_deaf", True) else "❌ OFF | مطفي"

    embed = discord.Embed(
        title="🔊 Voice 24/7 Panel | لوحة فويس 24/7",
        description=(
            "Choose the voice room + mic/deafen, then press **Join**.\n"
            "The bot will stay 24/7 and auto-reconnect.\n\n"
            "اختر روم الفويس + المايك/الديفن ثم اضغط **Join**.\n"
            "البوت سيبقى 24/7 ويعيد الاتصال تلقائياً."
        ),
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Status | الحالة", value=enabled, inline=False)
    embed.add_field(name="Room | الروم", value=channel_text, inline=False)
    embed.add_field(name="Mic | المايك", value=mic, inline=True)
    embed.add_field(name="Deafen | ديفن", value=deaf, inline=True)
    embed.set_footer(text=guild.name)
    return embed


class Voice247View(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = int(guild_id)

    async def _refresh(self, interaction: discord.Interaction):
        cfg = get_voice247_config(interaction.guild_id)
        await interaction.response.edit_message(embed=_voice247_panel_embed(interaction.guild, cfg), view=self)

    @discord.ui.select(
        placeholder="Select voice room | اختر روم",
        min_values=0,
        max_values=1,
        row=0,
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.voice],
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        cfg = get_voice247_config(interaction.guild_id)
        if select.values:
            ch = select.values[0]
            cfg["channel_id"] = int(ch.id)
        else:
            cfg["channel_id"] = None
        update_guild_config(interaction.guild_id, {"voice_247": cfg})
        await self._refresh(interaction)

    @discord.ui.button(label="Mic | مايك", style=discord.ButtonStyle.secondary, row=1)
    async def mic_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_voice247_config(interaction.guild_id)
        cfg["self_mute"] = not bool(cfg.get("self_mute", True))
        update_guild_config(interaction.guild_id, {"voice_247": cfg})
        await self._refresh(interaction)

    @discord.ui.button(label="Deafen | ديفن", style=discord.ButtonStyle.secondary, row=1)
    async def deaf_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_voice247_config(interaction.guild_id)
        cfg["self_deaf"] = not bool(cfg.get("self_deaf", True))
        update_guild_config(interaction.guild_id, {"voice_247": cfg})
        await self._refresh(interaction)

    @discord.ui.button(label="Join 24/7 | دخول", style=discord.ButtonStyle.success, row=1)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)

        cfg = get_voice247_config(interaction.guild_id)
        if not cfg.get("channel_id"):
            return await interaction.response.send_message("❌ Choose a voice room first | اختر روم أولاً", ephemeral=True)

        cfg["enabled"] = True
        update_guild_config(interaction.guild_id, {"voice_247": cfg})

        # Clear backoff and attempt immediately
        _voice247_suppress_until.pop(int(interaction.guild_id), None)
        _voice247_clear_retry_state(int(interaction.guild_id))
        _voice247_set_manual_window(int(interaction.guild_id), 8.0)

        await interaction.response.send_message("✅ Joining... | جاري الدخول...", ephemeral=True)
        try:
            await _voice247_ensure_connected(interaction.guild, force=True, reason="panel_join")
        except Exception:
            pass

    @discord.ui.button(label="Disable | إيقاف", style=discord.ButtonStyle.danger, row=2)
    async def disable_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
        cfg = get_voice247_config(interaction.guild_id)
        cfg["enabled"] = False
        update_guild_config(interaction.guild_id, {"voice_247": cfg})

        gid = int(interaction.guild_id)
        # Suppress reconnects for a moment (disconnect triggers voice_state_update)
        _voice247_set_manual_window(gid, 10.0)
        _voice247_suppress_until[gid] = _voice247_now() + 30.0
        _voice247_clear_retry_state(gid)
        try:
            vc = interaction.guild.voice_client
            if vc:
                await vc.disconnect(force=True)
        except Exception:
            pass
        await interaction.response.send_message("✅ Disabled | تم الإيقاف", ephemeral=True)

    @discord.ui.button(label="Refresh | تحديث", style=discord.ButtonStyle.primary, row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)


@bot.tree.command(name="voice_panel", description="Voice 24/7 panel | لوحة فويس 24/7")
async def voice_panel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("❌ Manage Server required | تحتاج إدارة السيرفر", ephemeral=True)
    cfg = get_voice247_config(interaction.guild_id)
    await interaction.response.send_message(embed=_voice247_panel_embed(interaction.guild, cfg), view=Voice247View(interaction.guild_id), ephemeral=True)

@bot.event
async def on_ready():
    """Bot is ready"""
    try:
        async def _presence_rotator():
            await bot.wait_until_ready()
            idx = 0
            while not bot.is_closed():
                current_text = PRESENCE_ROTATE_TEXTS[idx % len(PRESENCE_ROTATE_TEXTS)]
                next_text = PRESENCE_ROTATE_TEXTS[(idx + 1) % len(PRESENCE_ROTATE_TEXTS)]

                try:
                    await bot.change_presence(
                        activity=discord.Activity(
                            type=discord.ActivityType.playing,
                            name=str(current_text),
                        )
                    )
                except Exception as e:
                    logger.error(f"Presence update error: {e}")

                # Optional mini-transition right before switching
                if PRESENCE_TRANSITION_ENABLED:
                    hold = max(0.0, float(PRESENCE_ROTATE_SECONDS) - float(PRESENCE_TRANSITION_SECONDS))
                    await asyncio.sleep(hold)
                    try:
                        await bot.change_presence(
                            activity=discord.Activity(
                                type=discord.ActivityType.playing,
                                name=f"{current_text} → {next_text}",
                            )
                        )
                    except Exception as e:
                        logger.error(f"Presence transition error: {e}")
                    await asyncio.sleep(float(PRESENCE_TRANSITION_SECONDS))
                else:
                    await asyncio.sleep(float(PRESENCE_ROTATE_SECONDS))

                idx += 1

        # Register persistent views once so old panels keep working after restarts.
        if not getattr(bot, "_persistent_views_added", False):
            bot.add_view(ModSettingsView())
            bot.add_view(GiveawayOpenFormView())
            bot._persistent_views_added = True

        await bot.tree.sync()
        # Start rotating presence once
        if not getattr(bot, "_presence_task_started", False):
            bot._presence_task_started = True
            asyncio.create_task(_presence_rotator())

        # Start giveaway watcher once
        global _giveaway_watcher_task
        if _giveaway_watcher_task is None or _giveaway_watcher_task.done():
            _giveaway_watcher_task = asyncio.create_task(_giveaway_watcher_loop())

        # Start voice 24/7 loop once
        global _voice247_task
        if _voice247_task is None or _voice247_task.done():
            _voice247_task = asyncio.create_task(_voice247_loop())


        # Restart enabled auto-clear workers after reboot
        for g in bot.guilds:
            try:
                if get_autoclear_config(g.id).get("enabled"):
                    _autoclear_start_task(g.id)
            except Exception:
                pass

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
        updates = {"show_image": enabled}
        if url:
            updates["image_url"] = url
        update_guild_config(interaction.guild_id, updates)

        guild_cfg = get_guild_config(interaction.guild_id)
        
        status = "✅ Enabled | مُفعَّلة" if enabled else "❌ Disabled | معطَّلة"
        embed = discord.Embed(
            title="🖼️ Image Settings | إعدادات الصور",
            description=f"Status: {status}\n\nالحالة: {status}",
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
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
    guild_cfg = get_guild_config(interaction.guild_id)
    color_list = ", ".join(COLOR_NAMES.keys())
    embed = discord.Embed(
        title="🎨 Available Colors | الألوان المتاحة",
        description=f"**Colors:** {color_list}\n\n**Hex Codes:** Use #FF0000 or 0xFF0000 format\n\n**الألوان:** {color_list}\n\n**أكواد سادس عشر:** استخدم صيغة #FF0000 أو 0xFF0000",
        color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="upload_image", description="Upload image by attachment | أرفع صورة")
@app_commands.describe(image="Upload image file | أرفع ملف الصورة")
async def upload_image(interaction: discord.Interaction, image: discord.Attachment):
    """Upload image via attachment"""
    try:
        # Check if it's an image
        if not (image.content_type or "").startswith('image'):
            await interaction.response.send_message("❌ Please upload an image file | الرجاء رفع ملف صورة", ephemeral=True)
            return

        update_guild_config(interaction.guild_id, {"image_url": image.url})
        guild_cfg = get_guild_config(interaction.guild_id)
        
        embed = discord.Embed(
            title="✅ Image Uploaded | تم رفع الصورة",
            description="Your image is now set as the poem decoration\n\nتم تعيين صورتك كزينة الأشعار",
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
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
        updates = {"auto_react": enabled}
        if emojis:
            emoji_list = [e.strip() for e in emojis.split() if e.strip()]
            updates["react_emojis"] = emoji_list
        update_guild_config(interaction.guild_id, updates)

        guild_cfg = get_guild_config(interaction.guild_id)
        current_reacts = guild_cfg.get("react_emojis", ["❤️", "🔥"])
        
        status = "✅ Enabled | مُفعَّلة" if enabled else "❌ Disabled | معطَّلة"
        embed = discord.Embed(
            title="😊 Auto React Settings | إعدادات التفاعلات التلقائية",
            description=f"Status: {status}\n\nالحالة: {status}\n\n✨ **You can use MULTIPLE emojis!**\nJust separate them with spaces: ❤️ 🔥 😍 💜 👏\n\n**Works with:** Unicode emojis, Custom emojis, emoji IDs",
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
        )
        
        if emojis:
            embed.add_field(
                name="Reactions | التفاعلات",
                value=" ".join(current_reacts),
                inline=False
            )
        else:
            embed.add_field(
                name="Current Reactions | التفاعلات الحالية",
                value=" ".join(current_reacts),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Auto react settings updated - enabled: {enabled}, emojis: {current_reacts}")
    except Exception as e:
        logger.error(f"Auto react command error: {e}")
        await interaction.response.send_message("❌ Error updating reactions", ephemeral=True)

@bot.tree.command(name="help", description="Show all commands | عرض جميع الأوامر")
async def help_command(interaction: discord.Interaction):
    """Show all available commands"""
    try:
        guild_cfg = get_guild_config(interaction.guild_id)
        embed = discord.Embed(
            title="📚 Available Commands | الأوامر المتاحة",
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
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
        guild_cfg = get_guild_config(interaction.guild_id)
        channel = bot.get_channel(guild_cfg.get("poem_channel")) if guild_cfg.get("poem_channel") else None
        
        embed = discord.Embed(
            title="⚙️ Bot Settings | إعدادات البوت",
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
        )
        
        embed.add_field(
            name="📍 Poem Channel | قناة الأشعار",
            value=f"{channel.mention if channel else 'Not set | لم يتم التعيين'}",
            inline=False
        )
        embed.add_field(
            name="🎨 Embed Color | لون الإطار",
            value=f"`{guild_cfg.get('embed_color', '#9B59B6')}`",
            inline=True
        )
        embed.add_field(
            name="🖼️ Image Display | عرض الصور",
            value=f"{'Enabled ✅ | مُفعَّلة' if guild_cfg.get('show_image', True) else 'Disabled ❌ | معطَّلة'}",
            inline=True
        )
        embed.add_field(
            name="🔗 Image URL | رابط الصورة",
            value=f"{guild_cfg.get('image_url', '')}",
            inline=False
        )
        embed.add_field(
            name="😊 Auto React | التفاعلات التلقائية",
            value=f"{'Enabled ✅ | مُفعَّلة' if guild_cfg.get('auto_react', False) else 'Disabled ❌ | معطَّلة'}",
            inline=True
        )
        embed.add_field(
            name="Reactions | التفاعلات",
            value=" ".join(guild_cfg.get("react_emojis", ["❤️", "🔥"])),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        logger.error(f"Info command error: {e}")
        await interaction.response.send_message("❌ Error | خطأ أثناء جلب الإعدادات", ephemeral=True)

@bot.tree.command(name="poem_setup", description="Open poem settings panel | فتح لوحة إعدادات الأشعار")
async def poem_setup(interaction: discord.Interaction):
    """Open poem settings panel"""
    try:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Administrator required | تحتاج صلاحية المدير",
                ephemeral=True,
            )
        
        guild_cfg = get_guild_config(interaction.guild_id)
        view = PoemSettingsView()
        embed = discord.Embed(
            title="📝 Poem Settings Panel | لوحة إعدادات الأشعار",
            description=(
                "**Configure poem system | إعداد نظام الشعر:**\n\n"
                "📍 **Channel | القناة** - Set poem channel | تحديد قناة الشعر\n"
                "🎨 **Appearance | المظهر** - Colors/images/reactions | ألوان/صور/تفاعلات\n\n"
                "Use the dashboard for full control | استخدم لوحة التحكم للتحكم الكامل:\n"
                "http://localhost:5000"
            ),
            color=parse_color(guild_cfg.get("embed_color", "#9B59B6"))
        )
        embed.set_footer(text=interaction.guild.name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

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
        super().__init__(title="📍 Poem Channel | قناة الشعر")
        
        self.channel = discord.ui.TextInput(label="Channel ID | معرف القناة", placeholder="1234567890", required=True)
        self.add_item(self.channel)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel_id = int(self.channel.value)
            update_guild_config(interaction.guild_id, {"poem_channel": channel_id})
            channel = bot.get_channel(channel_id)
            await interaction.response.send_message(
                f"✅ Poem channel set | تم تعيين قناة الشعر: {channel.mention if channel else channel_id}",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class PoemAppearanceModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🎨 Poem Appearance | المظهر")
        
        self.color = discord.ui.TextInput(label="Embed Color | لون الامبد", placeholder="#9B59B6 أو 9B59B6", required=False)
        self.add_item(self.color)
        
        self.image_url = discord.ui.TextInput(label="Image URL | رابط الصورة", placeholder="https://...", required=False)
        self.add_item(self.image_url)
        
        self.show_image = discord.ui.TextInput(label="Show image? yes/no | عرض؟", placeholder="yes", required=False)
        self.add_item(self.show_image)
        
        self.auto_react = discord.ui.TextInput(label="Auto react? yes/no | تفاعل؟", placeholder="no", required=False)
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
            await interaction.response.send_message("✅ Updated | تم تحديث المظهر", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

# Error handling
@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    logger.error(f"Error in {event}: {args}", exc_info=True)

# ============= TICKET SYSTEM =============

class TicketDropdown(discord.ui.Select):
    """Dropdown for ticket options"""
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        options = []
        for option in tcfg.get("ticket_options", []):
            emoji_value = _coerce_component_emoji(option.get("emoji")) or "🎫"
            options.append(
                discord.SelectOption(
                    label=option["label"],
                    emoji=emoji_value,
                    description=option.get("description", ""),
                    value=option["label"],
                )
            )
        super().__init__(
            placeholder=tcfg.get("dropdown_placeholder", "إضغط لفتح التكيت"),
            min_values=1, 
            max_values=1, 
            options=options,
            custom_id="ticket_dropdown_persistent"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle ticket creation"""
        # Show modal for reason
        modal = TicketReasonModal(self.guild_id, self.values[0])
        await interaction.response.send_modal(modal)

class TicketDropdownView(discord.ui.View):
    """View with dropdown"""
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown(guild_id))

class TicketReasonModal(discord.ui.Modal):
    """Modal to ask for ticket reason"""
    def __init__(self, guild_id: int, ticket_type: str):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title=tcfg.get("messages", {}).get("modal_title", "فتح تذكرة"))
        self.ticket_type = ticket_type
        
        self.reason = discord.ui.TextInput(
            label=tcfg.get("messages", {}).get("reason_label", "السبب"),
            placeholder=tcfg.get("messages", {}).get("modal_placeholder", "اذكر سبب فتح للتذكره :"),
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

            tcfg = get_ticket_config(interaction.guild_id)
            
            # Increment ticket counter
            tcfg["ticket_counter"] = int(tcfg.get("ticket_counter", 0)) + 1
            ticket_num = tcfg["ticket_counter"]
            update_guild_config(interaction.guild_id, {"tickets": tcfg})
            
            # Get category
            category = None
            if tcfg.get("category_id"):
                category = bot.get_channel(int(tcfg.get("category_id")))
            
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
            for role_id in tcfg.get("support_roles", []):
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
            for role_id in tcfg.get("ping_roles", []):
                role = guild.get_role(role_id)
                if role:
                    ping_mentions += f" {role.mention}"
            
            # Create ticket embed
            embed = discord.Embed(
                title=tcfg.get("messages", {}).get("ticket_created_title") or self.ticket_type,
                description=tcfg.get("messages", {}).get("ticket_created_desc", "✅ تم فتح التكيت بنجاح"),
                color=parse_color(tcfg.get("ticket_embed_color", tcfg.get("embed_color", "#9B59B6")))
            )
            
            # Add ticket image
            if tcfg.get("panel_image") and str(tcfg.get("panel_image")).strip():
                embed.set_image(url=str(tcfg.get("panel_image")).strip())
            if tcfg.get("ticket_image") and str(tcfg.get("ticket_image")).strip():
                embed.set_image(url=str(tcfg.get("ticket_image")).strip())
            
            # Add fields
            by_label = tcfg.get("messages", {}).get("ticket_by_label", "بواسطة")
            by_emoji = tcfg.get("messages", {}).get("by_emoji", "👤")
            embed.add_field(name=f"{by_emoji} {by_label}", value=interaction.user.mention, inline=False)
            
            # Use custom footer - only show time
            footer_text = tcfg.get("messages", {}).get("footer_text", "")
            if footer_text:
                embed.set_footer(text=f"{footer_text} • {interaction.created_at.strftime('%I:%M %p')}")
            else:
                embed.set_footer(text=interaction.created_at.strftime('%I:%M %p'))
            
            # Create reason embed
            reason_field_name = tcfg.get("messages", {}).get("reason_field_name", "REASON:")
            reason_embed = discord.Embed(
                description=f"**{reason_field_name}**\n{self.reason.value}",
                color=parse_color(tcfg.get("ticket_embed_color", tcfg.get("embed_color", "#9B59B6")))
            )
            if tcfg.get("reason_image") and str(tcfg.get("reason_image")).strip():
                reason_embed.set_image(url=str(tcfg.get("reason_image")).strip())
            
            # Send both embeds together with buttons (reason will appear between embed and buttons)
            view = TicketControlView(interaction.guild_id, ticket_channel.id, interaction.user.id)
            content = f"{interaction.user.mention}{ping_mentions}"
            await ticket_channel.send(content=content, embeds=[embed, reason_embed], view=view)
            
            # Log ticket creation
            await self.log_ticket_creation(interaction, ticket_channel, ticket_num, self.reason.value)
            
            # Follow up with success message
            success_msg = tcfg.get("messages", {}).get("ticket_created_success", "✅ تم فتح التكيت")
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
            tcfg = get_ticket_config(interaction.guild_id)
            log_channel_id = tcfg.get("log_channel_id")
            if not log_channel_id:
                return
            
            log_channel = bot.get_channel(log_channel_id)
            if not log_channel:
                return
            
            messages = tcfg.get("messages", {})
            
            embed = discord.Embed(
                title=messages.get("log_ticket_opened", "📬 Ticket Opened | فتح تذكرة"),
                color=parse_color(tcfg.get("embed_color", "#9B59B6")),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name=messages.get("log_opened_by", "Opened By | بواسطة"), value=interaction.user.mention, inline=True)
            embed.add_field(name=messages.get("log_channel", "Channel | القناة"), value=ticket_channel.mention, inline=True)
            embed.add_field(name="#", value=str(ticket_num), inline=True)
            embed.add_field(name=messages.get("log_reason", "Reason | السبب"), value=reason, inline=False)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging ticket creation: {e}")

class TicketControlView(discord.ui.View):
    """Buttons for ticket control"""
    def __init__(self, guild_id: int, channel_id, owner_id):
        super().__init__(timeout=None)
        self.guild_id = int(guild_id)
        self.channel_id = channel_id
        self.owner_id = owner_id

        tcfg = get_ticket_config(self.guild_id)
        
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
        close_style = style_map.get(tcfg.get("buttons", {}).get("close_style", "danger").lower(), discord.ButtonStyle.danger)
        close_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("close", "Close | إغلاق"),
            emoji=_coerce_component_emoji(tcfg.get("buttons", {}).get("close_emoji", "🔒")) or "🔒",
            style=close_style,
            custom_id=f"ticket_close_{channel_id}"
        )
        close_btn.callback = self.close_ticket
        self.add_item(close_btn)
        
        # Claim button (ADMIN ONLY)
        claim_style = style_map.get(tcfg.get("buttons", {}).get("claim_style", "primary").lower(), discord.ButtonStyle.primary)
        claim_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("claim", "Claim | استلام"),
            emoji=_coerce_component_emoji(tcfg.get("buttons", {}).get("claim_emoji", "👥")) or "👥",
            style=claim_style,
            custom_id=f"ticket_claim_{channel_id}"
        )
        claim_btn.callback = self.claim_ticket
        self.add_item(claim_btn)
        
        # Ping Admin button (MEMBER CAN USE)
        ping_admin_style = style_map.get(tcfg.get("buttons", {}).get("ping_admin_style", "secondary").lower(), discord.ButtonStyle.secondary)
        ping_admin_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("ping_admin", "Ping Admin | منشن الإدارة"),
            emoji=_coerce_component_emoji(tcfg.get("buttons", {}).get("ping_admin_emoji", "📢")) or "📢",
            style=ping_admin_style,
            custom_id=f"ticket_ping_admin_{channel_id}"
        )
        ping_admin_btn.callback = self.ping_admin
        self.add_item(ping_admin_btn)
        
        # Mention Member button (ADMIN ONLY)
        mention_member_style = style_map.get(tcfg.get("buttons", {}).get("mention_member_style", "secondary").lower(), discord.ButtonStyle.secondary)
        mention_member_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("mention_member", "Mention Member | منشن العضو"),
            emoji=_coerce_component_emoji(tcfg.get("buttons", {}).get("mention_member_emoji", "👤")) or "👤",
            style=mention_member_style,
            custom_id=f"ticket_mention_member_{channel_id}"
        )
        mention_member_btn.callback = self.mention_member
        self.add_item(mention_member_btn)
        
        # Add dropdown for menu options (ADMIN ONLY)
        self.add_item(TicketMenuDropdown(self.guild_id, channel_id, owner_id))
    
    def has_permission(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin permission (support roles only)"""
        tcfg = get_ticket_config(interaction.guild_id)
        if interaction.user.guild_permissions.administrator:
            return True

        admin_role_id = tcfg.get("admin_role_id")
        if admin_role_id:
            try:
                if any(r.id == int(admin_role_id) for r in interaction.user.roles):
                    return True
            except Exception:
                pass

        user_role_ids = [role.id for role in interaction.user.roles]
        support_role_ids = tcfg.get("support_roles", [])
        if support_role_ids:
            return any(role_id in support_role_ids for role_id in user_role_ids)

        # Fallback if no roles configured yet
        return interaction.user.guild_permissions.manage_channels
    
    async def ping_admin(self, interaction: discord.Interaction):
        """Ping admin roles (anyone can use)"""
        try:
            tcfg = get_ticket_config(interaction.guild_id)
            # Build ping mentions
            ping_mentions = ""
            for role_id in tcfg.get("ping_roles", []) or tcfg.get("support_roles", []):
                role = interaction.guild.get_role(role_id)
                if role:
                    ping_mentions += f" {role.mention}"
            
            if not ping_mentions:
                await interaction.response.send_message("❌ لا توجد أدوار إدارية محددة", ephemeral=True)
                return
            
            # Get custom message
            message = tcfg.get("messages", {}).get("ping_admin_message", "تم استدعاء الإدارة @ADMIN")
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
                tcfg = get_ticket_config(interaction.guild_id)
                message = tcfg.get("messages", {}).get("mention_member_message", "@MEMBER تفضل")
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
            tcfg = get_ticket_config(interaction.guild_id)
            claim_msg = tcfg.get("messages", {}).get("claim_message", "@USER استدعى الإدارة")
            claim_msg = claim_msg.replace("@USER", interaction.user.mention)
            
            claim_emoji = tcfg.get("messages", {}).get("claim_emoji", "👥")
            
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
            tcfg = get_ticket_config(interaction.guild_id)
            log_channel_id = tcfg.get("log_channel_id")
            if not log_channel_id:
                return
            
            log_channel = bot.get_channel(log_channel_id)
            if not log_channel:
                return
            
            messages = tcfg.get("messages", {})
            
            if action == "closed":
                title = messages.get("log_ticket_closed", "🔒 Ticket Closed | إغلاق تذكرة")
                by_label = messages.get("log_closed_by", "Closed By | بواسطة")
            elif action == "claimed":
                title = messages.get("log_ticket_claimed", "👥 Ticket Claimed | استلام تذكرة")
                by_label = messages.get("log_claimed_by", "Claimed By | بواسطة")
            else:
                return
            
            embed = discord.Embed(
                title=title,
                color=parse_color(tcfg.get("embed_color", "#9B59B6")),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name=by_label, value=interaction.user.mention, inline=True)
            embed.add_field(name=messages.get("log_channel", "Channel | القناة"), value=interaction.channel.mention, inline=True)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error logging ticket action: {e}")

class TicketMenuDropdown(discord.ui.Select):
    """Dropdown menu for ticket actions"""
    def __init__(self, guild_id: int, channel_id, owner_id):
        self.guild_id = int(guild_id)
        self.channel_id = channel_id
        self.owner_id = owner_id

        tcfg = get_ticket_config(self.guild_id)
        menu_cfg = tcfg.get("menu_options", {})
        
        options = [
            discord.SelectOption(
                label=menu_cfg.get("rename", {}).get("label", "Rename | تغيير الاسم"),
                emoji=_coerce_component_emoji(menu_cfg.get("rename", {}).get("emoji", "✏️")) or "✏️",
                description=menu_cfg.get("rename", {}).get("description", "Rename the ticket | تغيير اسم التكيت"),
                value="rename"
            ),
            discord.SelectOption(
                label=menu_cfg.get("add_user", {}).get("label", "Add User | إضافة عضو"),
                emoji=_coerce_component_emoji(menu_cfg.get("add_user", {}).get("emoji", "👤")) or "👤",
                description=menu_cfg.get("add_user", {}).get("description", "Add member | إضافة عضو للتكيت"),
                value="add_user"
            ),
            discord.SelectOption(
                label=menu_cfg.get("remove_user", {}).get("label", "Remove User | إزالة عضو"),
                emoji=_coerce_component_emoji(menu_cfg.get("remove_user", {}).get("emoji", "🚫")) or "🚫",
                description=menu_cfg.get("remove_user", {}).get("description", "Remove member | إزالة عضو من التكيت"),
                value="remove_user"
            ),
            discord.SelectOption(
                label=menu_cfg.get("reset", {}).get("label", "Reset | إعادة ضبط"),
                emoji=_coerce_component_emoji(menu_cfg.get("reset", {}).get("emoji", "🔄")) or "🔄",
                description=menu_cfg.get("reset", {}).get("description", "Reset menu | إعادة تعيين القائمة"),
                value="reset"
            )
        ]
        
        super().__init__(
            placeholder=tcfg.get("menu_placeholder", "Edit Ticket | تعديل التكيت"),
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"ticket_menu_{channel_id}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle menu selection (ADMIN ONLY)"""
        try:
            # Check if user has admin permission
            control_view = TicketControlView(interaction.guild_id, interaction.channel_id, interaction.user.id)
            if not control_view.has_permission(interaction):
                await interaction.response.send_message("❌ No permission | ليس لديك صلاحية", ephemeral=True)
                return
            
            action = self.values[0]
            
            if action == "reset":
                # Reset the menu by updating the message
                await interaction.response.send_message("🔄 Menu reset | تم إعادة تعيين القائمة", ephemeral=True, delete_after=2)
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
            await interaction.response.send_message("❌ Error | خطأ", ephemeral=True)

class RenameTicketModal(discord.ui.Modal):
    """Modal for renaming ticket"""
    def __init__(self, channel):
        super().__init__(title="Rename Ticket | تغيير الاسم")
        self.channel = channel
        
        self.new_name = discord.ui.TextInput(
            label="New name | الاسم الجديد",
            placeholder="ticket-new-name",
            required=True,
            max_length=100
        )
        self.add_item(self.new_name)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_name = self.new_name.value.strip().replace(" ", "-")
            await self.channel.edit(name=new_name)
            await interaction.response.send_message(f"✅ Renamed | تم تغيير الاسم إلى: {new_name}", ephemeral=True)
        except Exception as e:
            logger.error(f"Error renaming ticket: {e}")
            await interaction.response.send_message("❌ Rename failed | خطأ في تغيير الاسم", ephemeral=True)

class AddUserModal(discord.ui.Modal):
    """Modal for adding user to ticket"""
    def __init__(self, channel):
        super().__init__(title="Add User | إضافة عضو")
        self.channel = channel
        
        self.user_input = discord.ui.TextInput(
            label="User mention/ID | منشن/معرف العضو",
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
                await interaction.response.send_message("❌ Member not found | لم يتم العثور على العضو", ephemeral=True)
                return
            
            await self.channel.set_permissions(member, read_messages=True, send_messages=True)
            await interaction.response.send_message(f"✅ Added | تمت إضافة {member.mention} للتكيت")
            
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            await interaction.response.send_message("❌ Add failed | خطأ في إضافة العضو", ephemeral=True)

class RemoveUserModal(discord.ui.Modal):
    """Modal for removing user from ticket"""
    def __init__(self, channel):
        super().__init__(title="Remove User | إزالة عضو")
        self.channel = channel
        
        self.user_input = discord.ui.TextInput(
            label="User mention/ID | منشن/معرف العضو",
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
                await interaction.response.send_message("❌ Member not found | لم يتم العثور على العضو", ephemeral=True)
                return
            
            await self.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(f"✅ Removed | تمت إزالة {member.mention} من التكيت")
            
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            await interaction.response.send_message("❌ Remove failed | خطأ في إزالة العضو", ephemeral=True)


# Ticket Commands

@bot.tree.command(name="ticket_panel", description="Create ticket panel | إنشاء لوحة التكيت")
@app_commands.describe(channel="Channel to send panel | القناة لإرسال اللوحة")
async def ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """Create ticket panel"""
    try:
        target_channel = channel or interaction.channel

        tcfg = get_ticket_config(interaction.guild_id)
        
        # Create embed
        embed = discord.Embed(
            title=tcfg.get("panel_title", "🎫 Tickets | التكيت"),
            description=tcfg.get("panel_description", "اختر نوع التكيت من القائمة أدناه | Choose a ticket type below"),
            color=parse_color(tcfg.get("panel_embed_color", tcfg.get("embed_color", "#9B59B6")))
        )
        
        # Add main panel image (big image)
        if tcfg.get("panel_image") and str(tcfg.get("panel_image")).strip():
            embed.set_image(url=str(tcfg.get("panel_image")).strip())
        
        # Add small author icon if set
        if tcfg.get("panel_author_icon") and str(tcfg.get("panel_author_icon")).strip():
            embed.set_author(
                name=tcfg.get("panel_author_name", "Ticket System"),
                icon_url=str(tcfg.get("panel_author_icon")).strip()
            )
        
        embed.timestamp = discord.utils.utcnow()
        
        # Send with dropdown
        view = TicketDropdownView(interaction.guild_id)
        await target_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Ticket panel created | تم إنشاء لوحة التكيت في {target_channel.mention}",
            ephemeral=True,
        )
        logger.info(f"Ticket panel created by {interaction.user}")
        
    except Exception as e:
        logger.error(f"Error creating ticket panel: {e}", exc_info=True)
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

@bot.tree.command(name="ticket_category", description="Set ticket category | تعيين تصنيف التكيت")
@app_commands.describe(category="Category for tickets | التصنيف للتكيت")
async def ticket_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    """Set ticket category"""
    try:
        tcfg = get_ticket_config(interaction.guild_id)
        tcfg["category_id"] = category.id
        update_guild_config(interaction.guild_id, {"tickets": tcfg})
        
        await interaction.response.send_message(
            f"✅ Category set | تم تعيين التصنيف إلى: {category.name}",
            ephemeral=True,
        )
        logger.info(f"Ticket category set to {category.id}")
        
    except Exception as e:
        logger.error(f"Error setting category: {e}")
        await interaction.response.send_message("❌ Error | خطأ", ephemeral=True)

@bot.tree.command(name="ticket_log_channel", description="Set ticket log channel | تعيين قناة سجل التكيت")
@app_commands.describe(channel="Channel for ticket logs | قناة سجلات التكيت")
async def ticket_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set ticket log channel"""
    try:
        tcfg = get_ticket_config(interaction.guild_id)
        tcfg["log_channel_id"] = channel.id
        update_guild_config(interaction.guild_id, {"tickets": tcfg})
        
        await interaction.response.send_message(
            f"✅ Log channel set | تم تعيين قناة السجلات إلى: {channel.mention}",
            ephemeral=True,
        )
        logger.info(f"Ticket log channel set to {channel.id}")
        
    except Exception as e:
        logger.error(f"Error setting log channel: {e}")
        await interaction.response.send_message("❌ Error | خطأ", ephemeral=True)

@bot.tree.command(name="ticket_setup", description="Open ticket settings panel | فتح لوحة إعدادات التكيت")
async def ticket_setup(interaction: discord.Interaction):
    """Open interactive settings panel"""
    try:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                "❌ You need Manage Server permission | تحتاج صلاحية إدارة السيرفر",
                ephemeral=True,
            )

        tcfg = get_ticket_config(interaction.guild_id)
        embed = _build_ticket_setup_embed(interaction.guild, tcfg)
        await interaction.response.send_message(
            embed=embed,
            view=TicketSetupPanelView(interaction.guild_id),
            ephemeral=True,
        )
        
    except Exception as e:
        logger.error(f"Error opening settings: {e}")
        await interaction.response.send_message("❌ Error", ephemeral=True)


def _extract_int_ids(text: str) -> list[int]:
    if not text:
        return []
    ids = re.findall(r"\d{5,}", str(text))
    out: list[int] = []
    for raw in ids:
        try:
            out.append(int(raw))
        except Exception:
            continue
    return out


def _build_ticket_setup_embed(guild: discord.Guild, tcfg: dict) -> discord.Embed:
    category = guild.get_channel(int(tcfg["category_id"])) if tcfg.get("category_id") else None
    log_channel = guild.get_channel(int(tcfg["log_channel_id"])) if tcfg.get("log_channel_id") else None

    embed = discord.Embed(
        title="🎫 Ticket Setup | إعدادات التكيت",
        description=(
            "Manage ticket settings for this server.\n\n"
            "إدارة إعدادات التكيت لهذا السيرفر."
        ),
        color=parse_color(tcfg.get("embed_color", "#9B59B6")),
    )

    embed.add_field(
        name="📁 Category | التصنيف",
        value=category.mention if category else "Not set | غير محدد",
        inline=False,
    )
    embed.add_field(
        name="📋 Log Channel | قناة السجلات",
        value=log_channel.mention if log_channel else "Not set | غير محدد",
        inline=False,
    )
    embed.add_field(
        name="👥 Support Roles | أدوار الدعم",
        value=" ".join(f"<@&{rid}>" for rid in (tcfg.get("support_roles") or [])) or "None | لا يوجد",
        inline=False,
    )
    embed.add_field(
        name="📢 Ping Roles | أدوار المنشن",
        value=" ".join(f"<@&{rid}>" for rid in (tcfg.get("ping_roles") or [])) or "None | لا يوجد",
        inline=False,
    )

    options = tcfg.get("ticket_options", []) or []
    options_text = "\n".join(
        f"{i+1}. {opt.get('emoji', '🎫')} {opt.get('label', '')}"
        for i, opt in enumerate(options)
    )
    embed.add_field(
        name="🎟️ Options | الخيارات",
        value=options_text or "None | لا يوجد",
        inline=False,
    )

    embed.set_footer(text=guild.name)
    return embed


class NextModalView(discord.ui.View):
    def __init__(self, label: str, modal_factory):
        super().__init__(timeout=300)
        self._label = label
        self._modal_factory = modal_factory

    @discord.ui.button(label="Next | التالي", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(self._modal_factory())


class TicketSetupPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = int(guild_id)

    @discord.ui.button(label="Panel | اللوحة", emoji="🎨", style=discord.ButtonStyle.primary, row=0)
    async def panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupPanelModal1(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Channels | القنوات", emoji="📁", style=discord.ButtonStyle.primary, row=0)
    async def channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupChannelsModal(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Roles | الأدوار", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupRolesModal(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Add Option | إضافة خيار", emoji="➕", style=discord.ButtonStyle.success, row=1)
    async def add_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupAddOptionModal(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Remove Option | حذف خيار", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def remove_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupRemoveOptionModal(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Messages | الرسائل", emoji="📝", style=discord.ButtonStyle.primary, row=2)
    async def messages(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupMessagesModal1(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Buttons | الأزرار", emoji="🔘", style=discord.ButtonStyle.primary, row=2)
    async def buttons(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupButtonsModal1(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Embeds | الإمبد", emoji="🎨", style=discord.ButtonStyle.secondary, row=2)
    async def embeds(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupEmbedsModal(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Menu | القائمة", emoji="🎛️", style=discord.ButtonStyle.secondary, row=3)
    async def menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_modal(TicketSetupMenuModal(self.guild_id))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"❌ Error | خطأ: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Error | خطأ: {e}", ephemeral=True)

    @discord.ui.button(label="Refresh | تحديث", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        tcfg = get_ticket_config(self.guild_id)
        embed = _build_ticket_setup_embed(interaction.guild, tcfg)
        await interaction.response.edit_message(embed=embed, view=self)


class TicketSetupPanelModal1(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="🎨 Panel | اللوحة (1/2)")

        self.title_input = discord.ui.TextInput(
            label="Panel title | عنوان اللوحة",
            default=str(tcfg.get("panel_title", ""))[:256],
            max_length=256,
            required=False,
        )
        self.desc_input = discord.ui.TextInput(
            label="Description | الوصف",
            default=str(tcfg.get("panel_description", ""))[:2000],
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.color_input = discord.ui.TextInput(
            label="Panel embed color | لون امبد اللوحة",
            default=str(tcfg.get("panel_embed_color", tcfg.get("embed_color", "#9B59B6")))[:64],
            max_length=64,
            required=False,
        )
        self.panel_image = discord.ui.TextInput(
            label="Panel image URL | رابط صورة اللوحة",
            default=str(tcfg.get("panel_image", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.panel_author_name = discord.ui.TextInput(
            label="Panel author name | اسم الكاتب",
            default=str(tcfg.get("panel_author_name", ""))[:256],
            max_length=256,
            required=False,
        )
        self.panel_author_icon = discord.ui.TextInput(
            label="Panel author icon URL | رابط أيقونة الكاتب",
            default=str(tcfg.get("panel_author_icon", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.panel_image)
        self.add_item(self.panel_author_name)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        if self.title_input.value.strip():
            tcfg["panel_title"] = self.title_input.value.strip()
        if self.desc_input.value.strip():
            tcfg["panel_description"] = self.desc_input.value.strip()
        if self.color_input.value.strip():
            tcfg["panel_embed_color"] = self.color_input.value.strip()
        if self.panel_image.value.strip():
            tcfg["panel_image"] = self.panel_image.value.strip()
        if self.panel_author_name.value.strip():
            tcfg["panel_author_name"] = self.panel_author_name.value.strip()
        if self.panel_author_icon.value.strip():
            tcfg["panel_author_icon"] = self.panel_author_icon.value.strip()
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message(
            "✅ Saved (1/2) | تم الحفظ (1/2)",
            ephemeral=True,
            view=NextModalView("Next | التالي", lambda: TicketSetupPanelModal2(self.guild_id)),
        )


class TicketSetupPanelModal2(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="🎨 Panel | اللوحة (2/2)")

        self.panel_author_icon = discord.ui.TextInput(
            label="Panel author icon URL | رابط أيقونة الكاتب",
            default=str(tcfg.get("panel_author_icon", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.dropdown_ph = discord.ui.TextInput(
            label="Dropdown placeholder | عبارة القائمة",
            default=str(tcfg.get("dropdown_placeholder", ""))[:100],
            max_length=100,
            required=False,
        )
        self.menu_ph = discord.ui.TextInput(
            label="Menu placeholder | عبارة القائمة",
            default=str(tcfg.get("menu_placeholder", ""))[:100],
            max_length=100,
            required=False,
        )

        self.add_item(self.panel_author_icon)
        self.add_item(self.dropdown_ph)
        self.add_item(self.menu_ph)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        if self.panel_author_icon.value.strip():
            tcfg["panel_author_icon"] = self.panel_author_icon.value.strip()
        if self.dropdown_ph.value.strip():
            tcfg["dropdown_placeholder"] = self.dropdown_ph.value.strip()
        if self.menu_ph.value.strip():
            tcfg["menu_placeholder"] = self.menu_ph.value.strip()

        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث إعدادات اللوحة", ephemeral=True)


class TicketSetupChannelsModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="📁 Channels | القنوات")

        self.category_id = discord.ui.TextInput(
            label="Category ID (opt) | معرف التصنيف",
            default=str(tcfg.get("category_id") or ""),
            required=False,
            max_length=25,
        )
        self.log_channel_id = discord.ui.TextInput(
            label="Log channel ID (opt) | معرف السجل",
            default=str(tcfg.get("log_channel_id") or ""),
            required=False,
            max_length=25,
        )
        self.add_item(self.category_id)
        self.add_item(self.log_channel_id)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)

        cat_ids = _extract_int_ids(self.category_id.value)
        log_ids = _extract_int_ids(self.log_channel_id.value)
        tcfg["category_id"] = cat_ids[0] if cat_ids else None
        tcfg["log_channel_id"] = log_ids[0] if log_ids else None

        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث القنوات", ephemeral=True)


class TicketSetupMessagesModal1(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        msg = tcfg.get("messages", {})
        super().__init__(title="📝 Messages | الرسائل (1/3)")

        self.ticket_title = discord.ui.TextInput(
            label="Ticket title | عنوان التذكرة",
            default=str(msg.get("ticket_created_title", ""))[:256],
            max_length=256,
            required=False,
        )
        self.ticket_desc = discord.ui.TextInput(
            label="Ticket description | وصف التذكرة",
            default=str(msg.get("ticket_created_desc", ""))[:2000],
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.modal_title = discord.ui.TextInput(
            label="Modal title | عنوان المودال",
            default=str(msg.get("modal_title", ""))[:256],
            max_length=256,
            required=False,
        )
        self.modal_placeholder = discord.ui.TextInput(
            label="Modal placeholder | نص المودال",
            default=str(msg.get("modal_placeholder", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.reason_label = discord.ui.TextInput(
            label="Reason label | اسم السبب",
            default=str(msg.get("reason_label", ""))[:256],
            max_length=256,
            required=False,
        )

        self.add_item(self.ticket_title)
        self.add_item(self.ticket_desc)
        self.add_item(self.modal_title)
        self.add_item(self.modal_placeholder)
        self.add_item(self.reason_label)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        msg = tcfg.get("messages", {})

        if self.ticket_title.value.strip():
            msg["ticket_created_title"] = self.ticket_title.value.strip()
        if self.ticket_desc.value.strip():
            msg["ticket_created_desc"] = self.ticket_desc.value.strip()
        if self.modal_title.value.strip():
            msg["modal_title"] = self.modal_title.value.strip()
        if self.modal_placeholder.value.strip():
            msg["modal_placeholder"] = self.modal_placeholder.value.strip()
        if self.reason_label.value.strip():
            msg["reason_label"] = self.reason_label.value.strip()

        tcfg["messages"] = msg
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message(
            "✅ Saved (1/3) | تم الحفظ (1/3)",
            ephemeral=True,
            view=NextModalView("Next | التالي", lambda: TicketSetupMessagesModal2(self.guild_id)),
        )


class TicketSetupMessagesModal2(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        msg = tcfg.get("messages", {})
        super().__init__(title="📝 Messages | الرسائل (2/3)")

        self.reason_field_name = discord.ui.TextInput(
            label="Reason field name | عنوان السبب",
            default=str(msg.get("reason_field_name", ""))[:256],
            max_length=256,
            required=False,
        )
        self.by_label = discord.ui.TextInput(
            label="By label | بواسطة",
            default=str(msg.get("ticket_by_label", ""))[:256],
            max_length=256,
            required=False,
        )
        self.by_emoji = discord.ui.TextInput(
            label="By emoji | ايموجي بواسطة",
            default=str(msg.get("by_emoji", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.footer_text = discord.ui.TextInput(
            label="Footer text | نص الفوتر",
            default=str(msg.get("footer_text", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.claim_message = discord.ui.TextInput(
            label="Claim message | رسالة الاستدعاء",
            default=str(msg.get("claim_message", ""))[:4000],
            max_length=4000,
            required=False,
        )

        self.add_item(self.reason_field_name)
        self.add_item(self.by_label)
        self.add_item(self.by_emoji)
        self.add_item(self.footer_text)
        self.add_item(self.claim_message)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        msg = tcfg.get("messages", {})

        if self.reason_field_name.value.strip():
            msg["reason_field_name"] = self.reason_field_name.value.strip()
        if self.by_label.value.strip():
            msg["ticket_by_label"] = self.by_label.value.strip()
        if self.by_emoji.value.strip():
            msg["by_emoji"] = self.by_emoji.value.strip()
        if self.footer_text.value.strip():
            msg["footer_text"] = self.footer_text.value.strip()
        if self.claim_message.value.strip():
            msg["claim_message"] = self.claim_message.value.strip()

        tcfg["messages"] = msg
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message(
            "✅ Saved (2/3) | تم الحفظ (2/3)",
            ephemeral=True,
            view=NextModalView("Next | التالي", lambda: TicketSetupMessagesModal3(self.guild_id)),
        )


class TicketSetupMessagesModal3(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        msg = tcfg.get("messages", {})
        super().__init__(title="📝 Messages | الرسائل (3/3)")

        self.claim_emoji = discord.ui.TextInput(
            label="Claim emoji | ايموجي الاستدعاء",
            default=str(msg.get("claim_emoji", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.ping_admin_message = discord.ui.TextInput(
            label="Ping admin message | رسالة استدعاء الإدارة",
            default=str(msg.get("ping_admin_message", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.mention_member_message = discord.ui.TextInput(
            label="Mention member message | رسالة منشن العضو",
            default=str(msg.get("mention_member_message", ""))[:4000],
            max_length=4000,
            required=False,
        )

        self.add_item(self.claim_emoji)
        self.add_item(self.ping_admin_message)
        self.add_item(self.mention_member_message)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        msg = tcfg.get("messages", {})

        if self.claim_emoji.value.strip():
            msg["claim_emoji"] = self.claim_emoji.value.strip()
        if self.ping_admin_message.value.strip():
            msg["ping_admin_message"] = self.ping_admin_message.value.strip()
        if self.mention_member_message.value.strip():
            msg["mention_member_message"] = self.mention_member_message.value.strip()

        tcfg["messages"] = msg
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث الرسائل", ephemeral=True)


class TicketSetupButtonsModal1(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        btn = tcfg.get("buttons", {})
        super().__init__(title="🔘 Buttons | الأزرار (1/3)")

        self.close_label = discord.ui.TextInput(
            label="Close label | نص الإغلاق",
            default=str(btn.get("close", ""))[:256],
            max_length=256,
            required=False,
        )
        self.close_emoji = discord.ui.TextInput(
            label="Close emoji | ايموجي الإغلاق",
            default=str(btn.get("close_emoji", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.close_style = discord.ui.TextInput(
            label="Close color | لون الإغلاق",
            default=str(btn.get("close_style", ""))[:50],
            max_length=50,
            required=False,
        )
        self.claim_label = discord.ui.TextInput(
            label="Claim label | نص الاستلام",
            default=str(btn.get("claim", ""))[:256],
            max_length=256,
            required=False,
        )
        self.claim_emoji = discord.ui.TextInput(
            label="Claim emoji | ايموجي الاستلام",
            default=str(btn.get("claim_emoji", ""))[:4000],
            max_length=4000,
            required=False,
        )

        self.add_item(self.close_label)
        self.add_item(self.close_emoji)
        self.add_item(self.close_style)
        self.add_item(self.claim_label)
        self.add_item(self.claim_emoji)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        btn = tcfg.get("buttons", {})

        if self.close_label.value.strip():
            btn["close"] = self.close_label.value.strip()
        if self.close_emoji.value.strip():
            btn["close_emoji"] = self.close_emoji.value.strip()
        if self.close_style.value.strip():
            btn["close_style"] = self.close_style.value.strip()
        if self.claim_label.value.strip():
            btn["claim"] = self.claim_label.value.strip()
        if self.claim_emoji.value.strip():
            btn["claim_emoji"] = self.claim_emoji.value.strip()

        tcfg["buttons"] = btn
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message(
            "✅ Saved (1/3) | تم الحفظ (1/3)",
            ephemeral=True,
            view=NextModalView("Next | التالي", lambda: TicketSetupButtonsModal2(self.guild_id)),
        )


class TicketSetupButtonsModal2(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        btn = tcfg.get("buttons", {})
        super().__init__(title="🔘 Buttons | الأزرار (2/3)")

        self.claim_style = discord.ui.TextInput(
            label="Claim color | لون الاستلام",
            default=str(btn.get("claim_style", ""))[:50],
            max_length=50,
            required=False,
        )
        self.ping_label = discord.ui.TextInput(
            label="Ping admin label | نص الاستدعاء",
            default=str(btn.get("ping_admin", ""))[:256],
            max_length=256,
            required=False,
        )
        self.ping_emoji = discord.ui.TextInput(
            label="Ping admin emoji | ايموجي الاستدعاء",
            default=str(btn.get("ping_admin_emoji", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.ping_style = discord.ui.TextInput(
            label="Ping admin color | لون الاستدعاء",
            default=str(btn.get("ping_admin_style", ""))[:50],
            max_length=50,
            required=False,
        )
        self.mention_label = discord.ui.TextInput(
            label="Mention member label | نص منشن العضو",
            default=str(btn.get("mention_member", ""))[:256],
            max_length=256,
            required=False,
        )

        self.add_item(self.claim_style)
        self.add_item(self.ping_label)
        self.add_item(self.ping_emoji)
        self.add_item(self.ping_style)
        self.add_item(self.mention_label)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        btn = tcfg.get("buttons", {})

        if self.claim_style.value.strip():
            btn["claim_style"] = self.claim_style.value.strip()
        if self.ping_label.value.strip():
            btn["ping_admin"] = self.ping_label.value.strip()
        if self.ping_emoji.value.strip():
            btn["ping_admin_emoji"] = self.ping_emoji.value.strip()
        if self.ping_style.value.strip():
            btn["ping_admin_style"] = self.ping_style.value.strip()
        if self.mention_label.value.strip():
            btn["mention_member"] = self.mention_label.value.strip()

        tcfg["buttons"] = btn
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message(
            "✅ Saved (2/3) | تم الحفظ (2/3)",
            ephemeral=True,
            view=NextModalView("Next | التالي", lambda: TicketSetupButtonsModal3(self.guild_id)),
        )


class TicketSetupButtonsModal3(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        btn = tcfg.get("buttons", {})
        super().__init__(title="🔘 Buttons | الأزرار (3/3)")

        self.mention_emoji = discord.ui.TextInput(
            label="Mention member emoji | ايموجي منشن العضو",
            default=str(btn.get("mention_member_emoji", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.mention_style = discord.ui.TextInput(
            label="Mention member color | لون منشن العضو",
            default=str(btn.get("mention_member_style", ""))[:50],
            max_length=50,
            required=False,
        )

        self.add_item(self.mention_emoji)
        self.add_item(self.mention_style)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        btn = tcfg.get("buttons", {})

        if self.mention_emoji.value.strip():
            btn["mention_member_emoji"] = self.mention_emoji.value.strip()
        if self.mention_style.value.strip():
            btn["mention_member_style"] = self.mention_style.value.strip()

        tcfg["buttons"] = btn
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث الأزرار", ephemeral=True)


class TicketSetupEmbedsModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="🎨 Embeds | الإمبد")

        self.ticket_color = discord.ui.TextInput(
            label="Ticket embed color | لون امبد التذكرة",
            default=str(tcfg.get("ticket_embed_color", tcfg.get("embed_color", "#9B59B6")))[:64],
            max_length=64,
            required=False,
        )
        self.ticket_image = discord.ui.TextInput(
            label="Ticket image URL | رابط صورة التذكرة",
            default=str(tcfg.get("ticket_image", ""))[:4000],
            max_length=4000,
            required=False,
        )
        self.reason_image = discord.ui.TextInput(
            label="Reason image URL | رابط صورة السبب",
            default=str(tcfg.get("reason_image", ""))[:4000],
            max_length=4000,
            required=False,
        )

        self.add_item(self.ticket_color)
        self.add_item(self.ticket_image)
        self.add_item(self.reason_image)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        if self.ticket_color.value.strip():
            tcfg["ticket_embed_color"] = self.ticket_color.value.strip()
        if self.ticket_image.value.strip():
            tcfg["ticket_image"] = self.ticket_image.value.strip()
        if self.reason_image.value.strip():
            tcfg["reason_image"] = self.reason_image.value.strip()

        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث الإمبد", ephemeral=True)


class TicketSetupMenuModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="🎛️ Menu Options | خيارات القائمة")

        self.option_key = discord.ui.TextInput(
            label="Option key | المفتاح (rename/add_user/remove_user/reset)",
            placeholder="rename",
            max_length=20,
            required=True,
        )
        self.label = discord.ui.TextInput(
            label="Label | الاسم",
            default="",
            max_length=256,
            required=False,
        )
        self.emoji = discord.ui.TextInput(
            label="Emoji | ايموجي",
            default="",
            max_length=4000,
            required=False,
        )
        self.description = discord.ui.TextInput(
            label="Description | الوصف",
            default="",
            max_length=4000,
            required=False,
        )

        self.add_item(self.option_key)
        self.add_item(self.label)
        self.add_item(self.emoji)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        menu = tcfg.get("menu_options", {})

        raw_key = self.option_key.value.strip().lower()
        key_map = {
            "rename": "rename",
            "add_user": "add_user",
            "add": "add_user",
            "remove_user": "remove_user",
            "remove": "remove_user",
            "reset": "reset",
        }
        key = key_map.get(raw_key)
        if not key:
            return await interaction.response.send_message(
                "❌ Invalid key | مفتاح غير صحيح",
                ephemeral=True,
            )

        current = menu.get(key, {})
        if self.label.value.strip():
            current["label"] = self.label.value.strip()
        if self.emoji.value.strip():
            current["emoji"] = self.emoji.value.strip()
        if self.description.value.strip():
            current["description"] = self.description.value.strip()

        menu[key] = current
        tcfg["menu_options"] = menu
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث خيارات القائمة", ephemeral=True)


class TicketSetupRolesModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="👥 Roles | الأدوار")

        self.support_roles = discord.ui.TextInput(
            label="Support roles | أدوار الدعم",
            default=" ".join(str(rid) for rid in (tcfg.get("support_roles") or []))[:400],
            required=False,
            max_length=400,
        )
        self.ping_roles = discord.ui.TextInput(
            label="Ping roles | أدوار المنشن",
            default=" ".join(str(rid) for rid in (tcfg.get("ping_roles") or []))[:400],
            required=False,
            max_length=400,
        )
        self.add_item(self.support_roles)
        self.add_item(self.ping_roles)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        tcfg["support_roles"] = _extract_int_ids(self.support_roles.value)
        tcfg["ping_roles"] = _extract_int_ids(self.ping_roles.value)
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated | تم تحديث الأدوار", ephemeral=True)


class TicketSetupAddOptionModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        super().__init__(title="➕ Add Option | إضافة خيار")

        self.label_input = discord.ui.TextInput(label="Label | الاسم", placeholder="Support | دعم", max_length=100)
        self.emoji_input = discord.ui.TextInput(label="Emoji (opt) | ايموجي", required=False, max_length=4000)
        self.desc_input = discord.ui.TextInput(
            label="Description (opt) | الوصف",
            required=False,
            style=discord.TextStyle.paragraph,
            max_length=100,
        )
        self.add_item(self.label_input)
        self.add_item(self.emoji_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        options = tcfg.get("ticket_options", []) or []
        options.append(
            {
                "label": self.label_input.value.strip(),
                "description": self.desc_input.value.strip() if self.desc_input.value else "",
                "emoji": self.emoji_input.value.strip() if self.emoji_input.value else "🎫",
            }
        )
        tcfg["ticket_options"] = options
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Added | تمت إضافة الخيار", ephemeral=True)


class TicketSetupRemoveOptionModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        super().__init__(title="🗑️ Remove | حذف")
        self.index_input = discord.ui.TextInput(label="Option # | رقم الخيار", placeholder="1", max_length=4)
        self.add_item(self.index_input)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        options = tcfg.get("ticket_options", []) or []
        try:
            idx = int(self.index_input.value.strip()) - 1
        except Exception:
            return await interaction.response.send_message("❌ Invalid number | رقم غير صحيح", ephemeral=True)

        if idx < 0 or idx >= len(options):
            return await interaction.response.send_message("❌ Out of range | خارج النطاق", ephemeral=True)

        options.pop(idx)
        tcfg["ticket_options"] = options
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Removed | تم حذف الخيار", ephemeral=True)

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
        super().__init__(title="🎨 Panel | اللوحة")
        self.guild_id = guild_id
        guild_cfg = get_guild_config(guild_id)
        
        self.title_input = discord.ui.TextInput(
            label="Title | العنوان",
            default=guild_cfg.get("tickets", {}).get("panel_title", ""),
            max_length=256
        )
        self.add_item(self.title_input)
        
        self.desc_input = discord.ui.TextInput(
            label="Description | الوصف",
            default=guild_cfg.get("tickets", {}).get("panel_description", ""),
            style=discord.TextStyle.paragraph,
            max_length=2000
        )
        self.add_item(self.desc_input)
        
        self.color_input = discord.ui.TextInput(
            label="Embed color | لون الامبد",
            default=guild_cfg.get("tickets", {}).get("embed_color", ""),
            max_length=6,
            required=False
        )
        self.add_item(self.color_input)
        
        self.image_input = discord.ui.TextInput(
            label="Image URL | رابط الصورة",
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
            await interaction.response.send_message("✅ Updated | تم تحديث إعدادات اللوحة", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

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
        super().__init__(title="➕ Add Option | إضافة خيار")
        
        self.label = discord.ui.TextInput(label="Label | الاسم", placeholder="Technical Support | دعم فني", max_length=100)
        self.add_item(self.label)
        
        self.emoji = discord.ui.TextInput(label="Emoji | ايموجي", placeholder="🛠️", max_length=4000)
        self.add_item(self.emoji)
        
        self.description = discord.ui.TextInput(label="Description | الوصف", placeholder="Get help | للحصول على مساعدة", max_length=100)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["ticket_options"].append({
                "label": self.label.value,
                "emoji": self.emoji.value,
                "description": self.description.value
            })
            save_config(config)
            await interaction.response.send_message(f"✅ Added | تمت الإضافة: {self.emoji.value} {self.label.value}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditOptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="✏️ Edit Option | تعديل خيار")
        
        self.number = discord.ui.TextInput(label="Option # | رقم الخيار", placeholder="1", max_length=3)
        self.add_item(self.number)
        
        self.label = discord.ui.TextInput(label="New label | اسم جديد", required=False, max_length=100)
        self.add_item(self.label)
        
        self.emoji = discord.ui.TextInput(label="New emoji | ايموجي جديد", required=False, max_length=4000)
        self.add_item(self.emoji)
        
        self.description = discord.ui.TextInput(label="New desc | وصف جديد", required=False, max_length=100)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            idx = int(self.number.value) - 1
            if idx < 0 or idx >= len(config["tickets"]["ticket_options"]):
                await interaction.response.send_message(
                    f"❌ Invalid number | رقم غير صحيح. Choose 1-{len(config['tickets']['ticket_options'])}",
                    ephemeral=True,
                )
                return
            
            if self.label.value:
                config["tickets"]["ticket_options"][idx]["label"] = self.label.value
            if self.emoji.value:
                config["tickets"]["ticket_options"][idx]["emoji"] = self.emoji.value
            if self.description.value:
                config["tickets"]["ticket_options"][idx]["description"] = self.description.value
            
            save_config(config)
            opt = config["tickets"]["ticket_options"][idx]
            await interaction.response.send_message(f"✅ Updated | تم التحديث: {opt.get('emoji', '')} {opt['label']}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class RemoveOptionModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🗑️ Remove | حذف")
        
        self.number = discord.ui.TextInput(label="Option # | رقم الخيار", placeholder="1", max_length=3)
        self.add_item(self.number)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            idx = int(self.number.value) - 1
            if idx < 0 or idx >= len(config["tickets"]["ticket_options"]):
                await interaction.response.send_message("❌ Invalid number | رقم غير صحيح", ephemeral=True)
                return
            
            removed = config["tickets"]["ticket_options"].pop(idx)
            save_config(config)
            await interaction.response.send_message(f"✅ Removed | تم الحذف: {removed.get('emoji', '')} {removed['label']}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class RolesSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👥 Roles | الأدوار")
        
        support_roles = " ".join([str(rid) for rid in config["tickets"].get("support_roles", [])])
        ping_roles = " ".join([str(rid) for rid in config["tickets"].get("ping_roles", [])])
        
        self.support = discord.ui.TextInput(
            label="Support roles | أدوار الدعم",
            placeholder="123456789 987654321",
            default=support_roles,
            required=False
        )
        self.add_item(self.support)
        
        self.ping = discord.ui.TextInput(
            label="Ping roles | أدوار المنشن",
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
            await interaction.response.send_message("✅ Roles updated | تم تحديث الأدوار", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

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
        super().__init__(title="🎨 Colors | ألوان")
        
        self.close_color = discord.ui.TextInput(
            label="Close color | لون الإغلاق",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("close_style", "danger"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.close_color)
        
        self.claim_color = discord.ui.TextInput(
            label="Claim color | لون الاستلام",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("claim_style", "primary"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.claim_color)
        
        self.ping_admin_color = discord.ui.TextInput(
            label="Ping color | لون المنشن",
            placeholder="danger, success, secondary, primary",
            default=config["tickets"]["buttons"].get("ping_admin_style", "secondary"),
            style=discord.TextStyle.short,
            max_length=20,
            required=False
        )
        self.add_item(self.ping_admin_color)
        
        self.mention_member_color = discord.ui.TextInput(
            label="Mention color | لون المنشن",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditClaimModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👥 Claim | الاستدعاء")
        
        self.claim_msg = discord.ui.TextInput(
            label="Message (@USER) | الرسالة",
            placeholder="@USER claimed the ticket | @USER استلم التكيت",
            default=config["tickets"]["messages"].get("claim_message", "@USER استدعى الإدارة"),
            style=discord.TextStyle.short,
            max_length=200
        )
        self.add_item(self.claim_msg)
        
        self.claim_emoji = discord.ui.TextInput(
            label="Emoji | ايموجي",
            default=config["tickets"]["messages"].get("claim_emoji", "👥"),
            style=discord.TextStyle.short,
            max_length=4000
        )
        self.add_item(self.claim_emoji)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            config["tickets"]["messages"]["claim_message"] = self.claim_msg.value
            config["tickets"]["messages"]["claim_emoji"] = self.claim_emoji.value
            save_config(config)
            await interaction.response.send_message("✅ Claim message updated! | تم تحديث رسالة الاستدعاء", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditPingAdminModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📢 Ping Admin | زر المنشن")
        
        self.ping_admin_label = discord.ui.TextInput(
            label="Button text | نص الزر",
            default=config["tickets"]["buttons"].get("ping_admin", "استدعاء الإدارة"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.ping_admin_label)
        
        self.ping_admin_emoji = discord.ui.TextInput(
            label="Emoji | ايموجي",
            default=config["tickets"]["buttons"].get("ping_admin_emoji", "📢"),
            style=discord.TextStyle.short,
            max_length=4000
        )
        self.add_item(self.ping_admin_emoji)
        
        self.ping_admin_message = discord.ui.TextInput(
            label="Message (@ADMIN) | الرسالة",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditMentionMemberModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👥 Mention | منشن العضو")
        
        self.mention_member_label = discord.ui.TextInput(
            label="Button text | نص الزر",
            default=config["tickets"]["buttons"].get("mention_member", "منشن العضو"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.mention_member_label)
        
        self.mention_member_emoji = discord.ui.TextInput(
            label="Emoji | ايموجي",
            default=config["tickets"]["buttons"].get("mention_member_emoji", "👤"),
            style=discord.TextStyle.short,
            max_length=4000
        )
        self.add_item(self.mention_member_emoji)
        
        self.mention_member_message = discord.ui.TextInput(
            label="Message (@MEMBER) | الرسالة",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditButtonsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔘 Buttons | الأزرار")
        
        self.close_btn = discord.ui.TextInput(
            label="Close text | نص الإغلاق",
            default=config["tickets"]["buttons"].get("close", "CLOSE"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.close_btn)
        
        self.close_emoji = discord.ui.TextInput(
            label="Close emoji | ايموجي الإغلاق",
            default=config["tickets"]["buttons"].get("close_emoji", "🔒"),
            style=discord.TextStyle.short,
            max_length=4000
        )
        self.add_item(self.close_emoji)
        
        self.claim_btn = discord.ui.TextInput(
            label="Claim text | نص الاستلام",
            default=config["tickets"]["buttons"].get("claim", "CLAIM"),
            style=discord.TextStyle.short,
            max_length=80
        )
        self.add_item(self.claim_btn)
        
        self.claim_btn_emoji = discord.ui.TextInput(
            label="Claim emoji | ايموجي الاستلام",
            default=config["tickets"]["buttons"].get("claim_emoji", "👥"),
            style=discord.TextStyle.short,
            max_length=4000
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditLabelsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📄 Text | النصوص")
        
        self.reason_field = discord.ui.TextInput(
            label="Reason name | اسم السبب",
            default=config["tickets"]["messages"].get("reason_field_name", "REASON:"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.reason_field)
        
        self.by_label = discord.ui.TextInput(
            label="By label | بواسطة",
            default=config["tickets"]["messages"].get("ticket_by_label", "بواسطة"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.by_label)
        
        self.by_emoji = discord.ui.TextInput(
            label="By emoji | ايموجي",
            default=config["tickets"]["messages"].get("by_emoji", "👤"),
            style=discord.TextStyle.short,
            max_length=4000
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditPlaceholdersModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="💬 Placeholders | العبارات")
        
        self.dropdown_ph = discord.ui.TextInput(
            label="Dropdown placeholder | عبارة القائمة",
            default=config["tickets"].get("dropdown_placeholder", "إضغط لفتح التكيت"),
            style=discord.TextStyle.short,
            max_length=150
        )
        self.add_item(self.dropdown_ph)
        
        self.menu_ph = discord.ui.TextInput(
            label="Menu placeholder | عبارة القائمة",
            default=config["tickets"].get("menu_placeholder", "تحديل التكيت"),
            style=discord.TextStyle.short,
            max_length=150
        )
        self.add_item(self.menu_ph)
        
        self.modal_title = discord.ui.TextInput(
            label="Modal title | عنوان النافذة",
            default=config["tickets"]["messages"].get("modal_title", "MODAL TITLE"),
            style=discord.TextStyle.short,
            max_length=100
        )
        self.add_item(self.modal_title)
        
        self.ticket_desc = discord.ui.TextInput(
            label="Ticket desc | وصف التكيت",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class EditSuccessMessageModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="✅ Success | رسالة النجاح")
        
        self.success_msg = discord.ui.TextInput(
            label="Created msg (you) | رسالة النجاح",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class MessagesSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📝 Messages | الرسائل (1/2)")
        
        self.dropdown_ph = discord.ui.TextInput(
            label="Dropdown placeholder | عبارة القائمة",
            default=config["tickets"].get("dropdown_placeholder", ""),
            required=False
        )
        self.add_item(self.dropdown_ph)
        
        self.menu_ph = discord.ui.TextInput(
            label="Menu placeholder | عبارة القائمة",
            default=config["tickets"].get("menu_placeholder", ""),
            required=False
        )
        self.add_item(self.menu_ph)
        
        self.modal_title = discord.ui.TextInput(
            label="Modal title | عنوان النافذة",
            default=config["tickets"]["messages"].get("modal_title", ""),
            required=False
        )
        self.add_item(self.modal_title)
        
        self.ticket_desc = discord.ui.TextInput(
            label="Ticket desc | وصف التذكرة",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class MessagesSettingsModal2(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📝 Messages | الرسائل (2/3)")
        
        self.reason_field = discord.ui.TextInput(
            label="Reason name | اسم السبب",
            default=config["tickets"]["messages"].get("reason_field_name", "REASON:"),
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.reason_field)
        
        self.claim_msg = discord.ui.TextInput(
            label="Claim msg (@USER) | رسالة الاستلام",
            placeholder="@USER claimed | @USER استلم",
            default=config["tickets"]["messages"].get("claim_message", ""),
            style=discord.TextStyle.short,
            required=False,
            max_length=200
        )
        self.add_item(self.claim_msg)
        
        self.claim_emoji = discord.ui.TextInput(
            label="Claim emoji | ايموجي",
            default=config["tickets"]["messages"].get("claim_emoji", "👥"),
            style=discord.TextStyle.short,
            max_length=4000,
            required=False
        )
        self.add_item(self.claim_emoji)
        
        self.by_label = discord.ui.TextInput(
            label="By label | بواسطة",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class MessagesSettingsModal3(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="📝 Buttons | الأزرار (3/3)")
        
        self.ticket_num_text = discord.ui.TextInput(
            label="Ticket num | رقم التذكرة",
            default=config["tickets"]["messages"].get("ticket_number_text", "تم فتح التكيت"),
            style=discord.TextStyle.short,
            required=False,
            max_length=100
        )
        self.add_item(self.ticket_num_text)
        
        self.close_btn = discord.ui.TextInput(
            label="Close text | نص الإغلاق",
            default=config["tickets"]["buttons"].get("close", "CLOSE"),
            style=discord.TextStyle.short,
            required=False,
            max_length=80
        )
        self.add_item(self.close_btn)
        
        self.close_emoji = discord.ui.TextInput(
            label="Close emoji | ايموجي",
            default=config["tickets"]["buttons"].get("close_emoji", "🔒"),
            style=discord.TextStyle.short,
            max_length=4000,
            required=False
        )
        self.add_item(self.close_emoji)
        
        self.claim_btn = discord.ui.TextInput(
            label="Claim text | نص الاستلام",
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
            await interaction.response.send_message(
                "✅ Updated | تم تحديث كل الإعدادات. Use /ticket_log_channel | استخدم /ticket_log_channel لتحديد قناة السجل.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class MenuOptionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.button(label="Rename | تغيير", emoji="✏️", style=discord.ButtonStyle.primary, row=0)
    async def rename_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("rename")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Add User | إضافة", emoji="👤", style=discord.ButtonStyle.primary, row=0)
    async def add_user_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("add_user")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remove User | إزالة", emoji="🚫", style=discord.ButtonStyle.primary, row=0)
    async def remove_user_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("remove_user")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Reset | إعادة", emoji="🔄", style=discord.ButtonStyle.primary, row=1)
    async def reset_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EditMenuOptionModal("reset")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Back | رجوع", emoji="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SettingsCategoryView()
        embed = discord.Embed(
            title="🎫 Ticket Settings Panel | لوحة إعدادات التكيت",
            description="**Choose a category to edit: | اختر فئة للتعديل:**\n\n"
                       "🎨 **Panel | اللوحة** - Title/desc/images/colors | العنوان/الوصف/الصور/الألوان\n"
                       "📋 **Options | الخيارات** - Add/edit/remove options | إضافة/تعديل/حذف\n"
                       "👥 **Roles | الأدوار** - Support & ping roles | أدوار الدعم والمنشن\n"
                       "📝 **Messages | الرسائل** - All text & placeholders | جميع النصوص\n"
                       "🎛️ **Menu | القائمة** - Dropdown menu options | خيارات القائمة\n"
                       "⚙️ **View | عرض** - See current settings | عرض الإعدادات",
            color=parse_color(config["tickets"]["embed_color"])
        )
        await interaction.response.edit_message(embed=embed, view=view)

class EditMenuOptionModal(discord.ui.Modal):
    def __init__(self, option_key):
        self.option_key = option_key
        option_name = option_key.replace("_", " ").title()
        super().__init__(title=f"Edit | تعديل: {option_name}")
        
        menu_cfg = config["tickets"].get("menu_options", {}).get(option_key, {})
        
        self.label = discord.ui.TextInput(
            label="Label | الاسم",
            default=menu_cfg.get("label", ""),
            required=False
        )
        self.add_item(self.label)
        
        self.emoji = discord.ui.TextInput(
            label="Emoji | ايموجي",
            default=menu_cfg.get("emoji", ""),
            required=False,
            max_length=4000
        )
        self.add_item(self.emoji)
        
        self.description = discord.ui.TextInput(
            label="Description | الوصف",
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
            await interaction.response.send_message(
                f"✅ Updated | تم تحديث: {self.option_key.replace('_', ' ')}",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

# ============================================================
# MODERATION SYSTEM
# ============================================================

def get_mod_config(guild_id):
    """Get moderation config for guild"""
    guild_cfg = get_guild_config(guild_id)

    changed = False
    if "moderation" not in guild_cfg:
        guild_cfg["moderation"] = {}
        changed = True

    mod_cfg = guild_cfg["moderation"]

    if "enabled" not in mod_cfg:
        mod_cfg["enabled"] = True
        changed = True
    if "mod_log_channel" not in mod_cfg:
        mod_cfg["mod_log_channel"] = None
        changed = True
    if "dm_on_action" not in mod_cfg:
        mod_cfg["dm_on_action"] = True
        changed = True
    if "shortcuts" not in mod_cfg:
        mod_cfg["shortcuts"] = {}
        changed = True
    if "messages" not in mod_cfg:
        mod_cfg["messages"] = {}
        changed = True

    # Access role gate: support both old single role and new multi-role list
    if "allowed_role_ids" not in mod_cfg or not isinstance(mod_cfg.get("allowed_role_ids"), list):
        mod_cfg["allowed_role_ids"] = []
        changed = True
    if "allowed_role_id" not in mod_cfg:
        mod_cfg["allowed_role_id"] = None
        changed = True

    # Migrate old single role -> list
    if mod_cfg.get("allowed_role_id") and not mod_cfg.get("allowed_role_ids"):
        try:
            mod_cfg["allowed_role_ids"] = [int(mod_cfg.get("allowed_role_id"))]
            changed = True
        except Exception:
            pass

    # Default templates (used as embed description; placeholders: {server} {reason} {duration} {moderator})
    default_messages = {
        "ban_dm": "تم حظرك من **{server}**.\nالسبب: {reason}\n\nYou have been banned from **{server}**.\nReason: {reason}",
        "kick_dm": "تم طردك من **{server}**.\nالسبب: {reason}\n\nYou have been kicked from **{server}**.\nReason: {reason}",
        "warn_dm": "تم تحذيرك في **{server}**.\nالسبب: {reason}\n\nYou have been warned in **{server}**.\nReason: {reason}",
        "timeout_dm": "تم إعطاؤك مهلة (Timeout) في **{server}**.\nالمدة: {duration}\nالسبب: {reason}\n\nYou have been timed out in **{server}**.\nDuration: {duration}\nReason: {reason}",
        "ban_log": "🔨 **User Banned | تم الحظر**",
        "kick_log": "👢 **User Kicked | تم الطرد**",
        "warn_log": "⚠️ **User Warned | تم التحذير**",
        "timeout_log": "⏱️ **User Timed Out | تم الإعطاء مهلة**",
        "channel_locked": "🔒 **Channel Locked | تم قفل القناة**",
        "channel_unlocked": "🔓 **Channel Unlocked | تم فتح القناة**",
    }
    for key, value in default_messages.items():
        if key not in mod_cfg["messages"]:
            mod_cfg["messages"][key] = value
            changed = True

    # Per-command DM embed colors
    if "embed_colors" not in mod_cfg:
        mod_cfg["embed_colors"] = {}
        changed = True
    default_colors = {
        "ban": "#ED4245",
        "kick": "#FEE75C",
        "warn": "#F1C40F",
        "timeout": "#5865F2",
        # messaging commands
        "dm": "#57F287",
        "say": "#57F287",
    }
    for key, value in default_colors.items():
        if key not in mod_cfg["embed_colors"]:
            mod_cfg["embed_colors"][key] = value
            changed = True

    if changed and guild_id is not None:
        update_guild_config(guild_id, guild_cfg)

    return mod_cfg


def build_mod_dm_embed(action, guild, moderator, reason, duration=None):
    mod_cfg = get_mod_config(guild.id)
    color_value = mod_cfg.get("embed_colors", {}).get(action, "#5865F2")

    titles = {
        "ban": "🔨 Banned | تم الحظر",
        "kick": "👢 Kicked | تم الطرد",
        "warn": "⚠️ Warning | تحذير",
        "timeout": "⏱️ Timeout | مهلة",
        "dm": "✉️ Message | رسالة",
        "say": "📣 Announcement | إعلان",
    }

    template = mod_cfg.get("messages", {}).get(f"{action}_dm", "{reason}")
    description = template.format(
        server=guild.name,
        reason=reason or "No reason | بدون سبب",
        duration=duration or "N/A | غير محدد",
        moderator=str(moderator),
    )

    embed = discord.Embed(
        title=titles.get(action, action),
        description=description,
        color=parse_color(str(color_value)),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_footer(text=guild.name)
    return embed


def _get_allowed_role_ids(mod_cfg) -> set[int]:
    role_ids: set[int] = set()

    # New list
    raw_list = mod_cfg.get("allowed_role_ids")
    if isinstance(raw_list, list):
        for rid in raw_list:
            try:
                if rid not in (None, "", 0, "0"):
                    role_ids.add(int(rid))
            except Exception:
                continue

    # Backward-compat single role
    raw_single = mod_cfg.get("allowed_role_id")
    try:
        if raw_single not in (None, "", 0, "0"):
            role_ids.add(int(raw_single))
    except Exception:
        pass

    return role_ids


def is_mod_authorized(member: discord.Member, mod_cfg, *, action: str | None = None) -> bool:
    """Additional moderation gate.

    If an allowed role is configured, the member must have it (admins bypass).
    This does not replace Discord permissions; it adds an extra server-configurable check.
    """
    try:
        if member.guild_permissions.administrator:
            return True

        allowed_role_ids = _get_allowed_role_ids(mod_cfg)
        if not allowed_role_ids:
            return True

        return any(r.id in allowed_role_ids for r in getattr(member, "roles", []))
    except Exception:
        return False

async def send_mod_log(guild, action, moderator, target, reason, duration=None):
    """Send moderation action to log channel"""
    try:
        mod_cfg = get_mod_config(guild.id)
        if not mod_cfg.get("mod_log_channel"):
            return
        
        channel = guild.get_channel(int(mod_cfg["mod_log_channel"]))
        if not channel:
            return
        
        title = (
            mod_cfg.get("messages", {}).get(f"{action}_log")
            or mod_cfg.get("messages", {}).get(action)
            or f"**{action.upper()}**"
        )

        embed = discord.Embed(
            title=title,
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )

        if isinstance(target, discord.abc.GuildChannel):
            embed.add_field(name="Channel | القناة", value=f"{target.mention} ({target.id})", inline=True)
        else:
            embed.add_field(name="User | العضو", value=f"{target.mention} ({target.id})", inline=True)

        embed.add_field(name="Moderator | المشرف", value=f"{moderator.mention}", inline=True)
        if duration:
            embed.add_field(name="Duration | المدة", value=duration, inline=True)
        embed.add_field(name="Reason | السبب", value=reason or "No reason | بدون سبب", inline=False)
        embed.set_footer(text=guild.name)
        
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
                title="Command: ban | أمر: حظر",
                description="**حظر المحتجر**\n**الأختصارات**\n`#حظر -حظر- طرد- حظرتلقائي- طرد- بفك`\n**الاستخدام**\n`/ban [user] (time m/h/d/mo/y) (reason)`\n\n**أمثلة للأمر:**\n`/ban @user`\n`/ban @user spamming`\n`/ban @user 1h spamming`\n`/ban @user 1d breaking rules`\n`/ban @user 1w advertising`",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحظر الأعضاء | You don't have permission to ban members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="ban"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )
        
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
                dm_embed = build_mod_dm_embed("ban", interaction.guild, interaction.user, reason)
                await user.send(embed=dm_embed)
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
                title="Command: kick | أمر: طرد",
                description="**طرد العضو**\n**الأختصارات**\n`#طرد -طرد- كيك- طرد- إطرد`\n**الاستخدام**\n`/kick [user] (reason)`\n\n**أمثلة للأمر:**\n`/kick @user`\n`/kick @user spamming`\n`/kick @user inappropriate behavior`\n`/kick @user breaking rules`",
                color=discord.Color.orange()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لطرد الأعضاء | You don't have permission to kick members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="kick"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )
        
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
                dm_embed = build_mod_dm_embed("kick", interaction.guild, interaction.user, reason)
                await user.send(embed=dm_embed)
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
                title="Command: timeout | أمر: مهلة",
                description="**مهلة العضو**\n**الأختصارات**\n`#مهلة -مهلة- ميوت- كتم- صامت`\n**الاستخدام**\n`/timeout [user] [duration] (reason)`\n\n**أمثلة للأمر:**\n`/timeout @user 10` (10 minutes)\n`/timeout @user 10 spamming`\n`/timeout @user 60 trolling`\n`/timeout @user 1440 breaking rules` (1 day)\n\n**Duration in minutes**",
                color=discord.Color.yellow()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                "❌ No permission | ليس لديك صلاحية لإعطاء مهلة",
                ephemeral=True,
            )
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="timeout"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )

        # Discord timeout max is 28 days (40320 minutes)
        if duration < 1 or duration > 40320:
            return await interaction.response.send_message(
                "❌ Duration 1-40320 min | المدة بين 1 و 40320 دقيقة (28 يوم)",
                ephemeral=True,
            )

        # Timeout user first
        await user.timeout(discord.utils.utcnow() + timedelta(minutes=duration), reason=reason)
        
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
                duration_str = f"{duration} دقيقة | {duration} minutes"
                dm_embed = build_mod_dm_embed("timeout", interaction.guild, interaction.user, reason, duration=duration_str)
                await user.send(embed=dm_embed)
            except Exception as e:
                logger.error(f"Failed to send DM to {user}: {e}")
        
        await send_mod_log(interaction.guild, "timeout", interaction.user, user, reason, f"{duration} minutes")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a user | تحذير عضو")
@app_commands.describe(user="The user to warn", reason="Reason for warning")
async def warn_user(interaction: discord.Interaction, user: discord.Member = None, reason: str = "No reason provided"):
    """Warn a user"""
    try:
        if not user:
            help_embed = discord.Embed(
                title="Command: warn | أمر: تحذير",
                description="**تحذير العضو**\n**الأختصارات**\n`#تحذير -تحذير- وارن- انذار- إنذار`\n**الاستخدام**\n`/warn [user] (reason)`\n\n**أمثلة للأمر:**\n`/warn @user`\n`/warn @user be respectful`\n`/warn @user stop spamming`\n`/warn @user read the rules`",
                color=discord.Color.gold()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لتحذير الأعضاء | You don't have permission to warn members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="warn"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )
        
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
                dm_embed = build_mod_dm_embed("warn", interaction.guild, interaction.user, reason)
                await user.send(embed=dm_embed)
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

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="lock"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )
        
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False, reason=reason)

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

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="unlock"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )
        
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
@app_commands.describe(amount="Number of messages to delete (blank = clear channel) | عدد الرسائل (اتركه فارغًا لمسح القناة)")
async def clear_messages(interaction: discord.Interaction, amount: int | None = None):
    """Delete messages"""
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لإدارة الرسائل | You don't have permission to manage messages", ephemeral=True)

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )
        
        await interaction.response.defer(ephemeral=True)

        if amount is None:
            total = await _purge_channel_all(interaction.channel, reason=f"Clear all by {interaction.user}")
            await interaction.followup.send(
                f"✅ تم حذف {total} رسالة (قد تبقى رسائل أقدم من 14 يوم) | Deleted {total} messages (messages older than 14 days may remain)",
                ephemeral=True,
            )
            return

        if amount <= 0:
            return await interaction.followup.send("❌ Invalid amount | رقم غير صحيح", ephemeral=True)

        deleted = await interaction.channel.purge(limit=int(amount))
        await interaction.followup.send(
            f"✅ تم حذف {len(deleted)} رسالة | Deleted {len(deleted)} messages",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


async def _purge_channel_all(channel: discord.TextChannel, *, reason: str | None = None) -> int:
    """Best-effort clear: deletes as many messages as possible (Discord won't bulk-delete >14 days)."""
    total_deleted = 0
    # Safety cap to avoid endless loops in weird edge cases
    for _ in range(200):
        batch = await channel.purge(limit=100, reason=reason)
        if not batch:
            break
        total_deleted += len(batch)
        # small delay to be kind to rate limits
        await asyncio.sleep(1)
    return total_deleted


# ============================================================
# AUTO CLEAR (delete channel + send message)
# ============================================================

def get_autoclear_config(guild_id: int) -> dict:
    """Get auto-clear config for a guild and ensure defaults exist."""
    guild_cfg = get_guild_config(guild_id)
    changed = False

    if "auto_clear" not in guild_cfg or not isinstance(guild_cfg.get("auto_clear"), dict):
        guild_cfg["auto_clear"] = {}
        changed = True

    acfg = guild_cfg["auto_clear"]

    def _set_default(key: str, value):
        nonlocal changed
        if key not in acfg:
            acfg[key] = value
            changed = True

    _set_default("enabled", False)
    _set_default("channel_id", None)
    _set_default("message", "✅ Cleared | ✅ تم الحذف")
    _set_default("interval_seconds", 60)
    # If there are old 14d+ messages, deletion can take time.
    # When send_early=True we send the message right after bulk-deleting newer messages,
    # then continue deleting older messages using history(before=sent_message) so it won't be deleted.
    _set_default("send_early", True)

    if changed:
        update_guild_config(guild_id, guild_cfg)

    return acfg


_autoclear_tasks: dict[int, asyncio.Task] = {}
_autoclear_locks: dict[int, asyncio.Lock] = {}


def _autoclear_lock(guild_id: int) -> asyncio.Lock:
    lock = _autoclear_locks.get(int(guild_id))
    if lock is None:
        lock = asyncio.Lock()
        _autoclear_locks[int(guild_id)] = lock
    return lock


async def _autoclear_delete_all_then_send(
    channel: discord.TextChannel,
    message_to_send: str,
    *,
    send_early: bool,
) -> tuple[int, bool]:
    deleted_total = 0
    sent_message: discord.Message | None = None
    before_cursor: discord.Message | None = None

    while True:
        history_kwargs = {"limit": 100}
        if before_cursor is not None:
            history_kwargs["before"] = before_cursor

        messages = [m async for m in channel.history(**history_kwargs)]
        if not messages:
            break

        now = discord.utils.utcnow()
        can_delete: list[discord.Message] = []
        too_old: list[discord.Message] = []
        for m in messages:
            if sent_message is not None and m.id == sent_message.id:
                continue

            age_seconds = (now - m.created_at).total_seconds()
            if age_seconds >= 14 * 24 * 3600:
                too_old.append(m)
            else:
                can_delete.append(m)

        # Fast path: bulk delete for messages <14 days
        if can_delete:
            try:
                await channel.delete_messages(can_delete)
                deleted_total += len(can_delete)
            except discord.HTTPException:
                for m in can_delete:
                    try:
                        await m.delete()
                        deleted_total += 1
                        await asyncio.sleep(0.15)
                    except Exception:
                        pass

        # If we reached the "old messages" zone, send immediately (so it feels instant)
        # Do this as soon as we detect old messages (even if we also deleted newer messages in this batch).
        if send_early and sent_message is None and message_to_send and too_old:
            try:
                sent_message = await channel.send(str(message_to_send))
                before_cursor = sent_message
            except Exception:
                sent_message = None

        # Old 14d+ messages must be deleted one-by-one (Discord limitation)
        for m in too_old:
            try:
                await m.delete()
                deleted_total += 1
                await asyncio.sleep(0.15)
            except Exception:
                pass

        await asyncio.sleep(0.25)

    if message_to_send and sent_message is None:
        try:
            sent_message = await channel.send(str(message_to_send))
        except Exception:
            sent_message = None

    return deleted_total, bool(sent_message)


async def _autoclear_run_once(guild_id: int) -> str:
    acfg = get_autoclear_config(guild_id)

    channel_id = acfg.get("channel_id")
    if not channel_id:
        return "❌ Set channel first | لازم تحدد الروم أولاً: /autoclear_setchannel"

    channel = bot.get_channel(int(channel_id))
    if not isinstance(channel, discord.TextChannel):
        return "❌ Channel not found | الروم غير موجودة أو البوت ما عنده صلاحية"

    message_to_send = str(acfg.get("message") or "").strip()
    interval = int(acfg.get("interval_seconds") or 60)
    send_early = bool(acfg.get("send_early", True))

    lock = _autoclear_lock(guild_id)
    if lock.locked():
        return "⏳ Already running | العملية شغالة حالياً"

    async with lock:
        deleted_count, sent = await _autoclear_delete_all_then_send(
            channel,
            message_to_send,
            send_early=send_early,
        )

    sent_txt = "✅ Sent | ✅ تم الإرسال" if sent else "⚠️ Not sent | لم يتم الإرسال"
    return f"✅ Cleared {deleted_count} | تم حذف {deleted_count} رسالة • {sent_txt} • every {interval}s | كل {interval} ثانية"


async def _autoclear_worker(guild_id: int):
    await bot.wait_until_ready()
    while not bot.is_closed():
        acfg = get_autoclear_config(guild_id)
        if not acfg.get("enabled"):
            break

        interval = int(acfg.get("interval_seconds") or 60)
        interval = max(20, min(interval, 24 * 3600))

        start_time = asyncio.get_event_loop().time()
        try:
            result = await _autoclear_run_once(guild_id)
            logger.info(f"[AutoClear:{guild_id}] {result}")
        except Exception as e:
            logger.error(f"[AutoClear:{guild_id}] error: {e}")

        elapsed = asyncio.get_event_loop().time() - start_time
        await asyncio.sleep(max(0, interval - elapsed))


def _autoclear_start_task(guild_id: int):
    existing = _autoclear_tasks.get(int(guild_id))
    if existing and not existing.done():
        return
    _autoclear_tasks[int(guild_id)] = asyncio.create_task(_autoclear_worker(int(guild_id)))


def _autoclear_stop_task(guild_id: int):
    task = _autoclear_tasks.pop(int(guild_id), None)
    if task and not task.done():
        task.cancel()


@bot.tree.command(name="autoclear_setchannel", description="AutoClear: set channel | تحديد روم الحذف")
@app_commands.describe(channel="Channel to clear | الروم")
async def autoclear_setchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        acfg = get_autoclear_config(interaction.guild_id)
        acfg["channel_id"] = channel.id
        update_guild_config(interaction.guild_id, {"auto_clear": acfg})
        await interaction.response.send_message(
            f"✅ Channel set | تم تحديد الروم: {channel.mention}",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_setmsg", description="AutoClear: set message | تغيير رسالة الإرسال")
@app_commands.describe(message="Message after clear | الرسالة بعد الحذف")
async def autoclear_setmsg(interaction: discord.Interaction, message: str):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        acfg = get_autoclear_config(interaction.guild_id)
        acfg["message"] = str(message)
        update_guild_config(interaction.guild_id, {"auto_clear": acfg})
        await interaction.response.send_message(
            "✅ Message updated | تم تحديث الرسالة",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_setinterval", description="AutoClear: set interval | تغيير مدة التكرار")
@app_commands.describe(seconds="Repeat every N seconds (min 20) | كل كم ثانية")
async def autoclear_setinterval(interaction: discord.Interaction, seconds: int):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        seconds = int(seconds)
        if seconds < 20 or seconds > 24 * 3600:
            return await interaction.response.send_message(
                "❌ Interval 20-86400 | المدة بين 20 و 86400 ثانية",
                ephemeral=True,
            )

        acfg = get_autoclear_config(interaction.guild_id)
        acfg["interval_seconds"] = seconds
        update_guild_config(interaction.guild_id, {"auto_clear": acfg})
        await interaction.response.send_message(
            f"✅ Interval set | تم تحديد المدة: {seconds}s",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_fast", description="AutoClear: fast send | إرسال الرسالة بسرعة")
@app_commands.describe(enabled="Send message early (recommended) | إرسال سريع")
async def autoclear_fast(interaction: discord.Interaction, enabled: bool):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        acfg = get_autoclear_config(interaction.guild_id)
        acfg["send_early"] = bool(enabled)
        update_guild_config(interaction.guild_id, {"auto_clear": acfg})
        await interaction.response.send_message(
            ("⚡ Fast mode enabled | تم تفعيل الإرسال السريع" if enabled else "🐢 Fast mode disabled | تم إيقاف الإرسال السريع"),
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_start", description="AutoClear: start | تشغيل الحذف التلقائي")
async def autoclear_start(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        acfg = get_autoclear_config(interaction.guild_id)
        if not acfg.get("channel_id"):
            return await interaction.response.send_message(
                "❌ Set channel first | لازم تحدد الروم أولاً: /autoclear_setchannel",
                ephemeral=True,
            )

        acfg["enabled"] = True
        update_guild_config(interaction.guild_id, {"auto_clear": acfg})

        await interaction.response.defer(ephemeral=True)
        # Run once immediately, then loop
        result = await _autoclear_run_once(interaction.guild_id)
        _autoclear_start_task(interaction.guild_id)

        await interaction.followup.send(
            "🚀 Started | تم التشغيل\n" + result,
            ephemeral=True,
        )
    except Exception as e:
        try:
            await interaction.followup.send(f"❌ Error | خطأ: {str(e)}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_stop", description="AutoClear: stop | إيقاف الحذف التلقائي")
async def autoclear_stop(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        acfg = get_autoclear_config(interaction.guild_id)
        acfg["enabled"] = False
        update_guild_config(interaction.guild_id, {"auto_clear": acfg})
        _autoclear_stop_task(interaction.guild_id)
        await interaction.response.send_message("⛔ Stopped | تم الإيقاف", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_status", description="AutoClear: status | حالة الحذف التلقائي")
async def autoclear_status(interaction: discord.Interaction):
    try:
        acfg = get_autoclear_config(interaction.guild_id)
        ch = f"<#{acfg.get('channel_id')}>" if acfg.get("channel_id") else "❌ Not set | غير محددة"
        enabled = "✅ ON | شغال" if acfg.get("enabled") else "⛔ OFF | متوقف"
        interval = int(acfg.get("interval_seconds") or 60)
        send_early = "✅" if acfg.get("send_early", True) else "❌"
        msg = str(acfg.get("message") or "").strip() or "(empty)"

        await interaction.response.send_message(
            f"📌 Status | الحالة: {enabled}\n"
            f"📍 Channel | الروم: {ch}\n"
            f"⏱️ Interval | المدة: {interval}s\n"
            f"⚡ Send early | إرسال سريع: {send_early}\n"
            f"📝 Message | الرسالة: {msg}",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoclear_now", description="AutoClear: run once | حذف الآن مرة واحدة")
async def autoclear_now(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ Manage Messages required | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="clear"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        result = await _autoclear_run_once(interaction.guild_id)
        await interaction.followup.send(result, ephemeral=True)
    except Exception as e:
        try:
            await interaction.followup.send(f"❌ Error | خطأ: {str(e)}", ephemeral=True)
        except Exception:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

# Shortcut command handler
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.guild:
        return await bot.process_commands(message)

    guild_cfg = get_guild_config(message.guild.id)

    # ----- Poem channel processing (per server) -----
    try:
        poem_channel_id = guild_cfg.get("poem_channel")
        if poem_channel_id and int(poem_channel_id) == message.channel.id:
            embed = discord.Embed(
                title="𝐓𝐑 • 𝐏𝐨𝐞𝐦𝐬",
                description=f"\n\n**{message.content}**\n\n",
                color=parse_color(guild_cfg.get("embed_color", "#9B59B6")),
            )

            if message.author.avatar:
                embed.set_thumbnail(url=message.author.avatar.url)

            embed.set_footer(
                text=f"{message.author.display_name}",
                icon_url=bot.user.avatar.url if bot.user and bot.user.avatar else None,
            )

            embed_message = await message.channel.send(embed=embed)

            if guild_cfg.get("auto_react") and guild_cfg.get("react_emojis"):
                for emoji in guild_cfg.get("react_emojis", []):
                    try:
                        await embed_message.add_reaction(str(emoji).strip())
                    except Exception:
                        pass

            if guild_cfg.get("show_image") and guild_cfg.get("image_url"):
                try:
                    await message.channel.send(str(guild_cfg.get("image_url")).strip())
                except Exception:
                    pass

            try:
                await message.delete()
            except Exception:
                pass

            return
    except Exception as e:
        logger.error(f"Poem processing error: {e}")

    # ----- Auto replies -----
    try:
        for rule in (guild_cfg.get("auto_replies") or []):
            if not rule or not rule.get("enabled", True):
                continue

            allowed_roles = rule.get("allowed_role_ids")
            if isinstance(allowed_roles, list) and allowed_roles:
                if isinstance(message.author, discord.Member) and not _member_has_any_role(message.author, allowed_roles):
                    continue

            trigger = str(rule.get("trigger", "")).strip()
            reply = str(rule.get("reply", "")).strip()
            if not trigger or not reply:
                continue

            if _matches_trigger(
                message.content.strip(),
                trigger,
                match_type=_normalize_match_type(rule.get("match")),
                case_sensitive=bool(rule.get("case_sensitive", False)),
            ):
                mention = bool(rule.get("mention", False))
                mode = _normalize_reply_mode(rule.get("mode"))
                content = f"{message.author.mention} {reply}" if mention else reply
                allowed = discord.AllowedMentions(users=mention, roles=False, everyone=False, replied_user=False)

                if mode == "reply":
                    await message.reply(content, mention_author=False, allowed_mentions=allowed)
                else:
                    await message.channel.send(content, allowed_mentions=allowed)
                break
    except Exception as e:
        logger.error(f"Auto reply error: {e}")

    # ----- Channel auto reply/react rules -----
    try:
        for rule in (guild_cfg.get("channel_auto") or []):
            if not rule or not rule.get("enabled", True):
                continue
            if int(rule.get("channel_id", 0) or 0) != message.channel.id:
                continue

            reply = str(rule.get("reply", "")).strip()
            if reply:
                content = f"{message.author.mention} {reply}" if rule.get("mention", False) else reply
                await message.channel.send(content, allowed_mentions=discord.AllowedMentions(users=bool(rule.get("mention", False))))

            for emoji in (rule.get("reactions") or []):
                try:
                    await message.add_reaction(str(emoji).strip())
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Channel auto error: {e}")

    # ----- Giveaway custom shortcut word -----
    try:
        gw = get_giveaway_config(message.guild.id)
        word = str(gw.get("shortcut_word") or "").strip()
        if word:
            content = str(message.content or "").strip()
            if content.lower() == word.lower():
                # Post an interaction button (modals require interactions)
                await message.channel.send(
                    "🎁 Click to open the giveaway form | اضغط لفتح نموذج السحب",
                    view=GiveawayOpenFormView(),
                    delete_after=60,
                )
    except Exception:
        pass
    
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

                    # Role gate (admins bypass). Applies to all shortcut actions.
                    if not is_mod_authorized(message.author, mod_cfg, action=action):
                        continue
                    
                    # Handle delete messages shortcut
                    if action == "delete":
                        if not message.author.guild_permissions.manage_messages:
                            continue

                        # Extract number from message (e.g., "m10" -> 10)
                        parts = message.content[len(shortcut):].strip()

                        # If no number provided => clear whole channel
                        if not parts:
                            try:
                                await message.delete()
                            except Exception:
                                pass
                            deleted_count = await _purge_channel_all(message.channel, reason=f"Clear all by {message.author}")
                            notify = await message.channel.send(
                                f"✅ تم مسح القناة ({deleted_count} رسالة) | Channel cleared ({deleted_count} messages)\n"
                                f"⚠️ قد تبقى رسائل أقدم من 14 يوم | Messages older than 14 days may remain"
                            )
                            await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=4))
                            await notify.delete()
                            continue

                        # Support both "m10" and "m 10"
                        amount = int(parts) if parts.isdigit() else int(action_data.get("default_amount", 5))

                        try:
                            await message.delete()
                        except Exception:
                            pass
                        deleted = await message.channel.purge(limit=amount)
                        
                        notify = await message.channel.send(f"✅ Deleted {len(deleted)} messages")
                        await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=3))
                        await notify.delete()

                    # Handle lock/unlock channel shortcuts
                    elif action in ["lock", "unlock"]:
                        if not message.author.guild_permissions.manage_channels:
                            continue

                        channel = message.channel
                        reason = message.content[len(shortcut):].strip() or "No reason provided"

                        if action == "lock":
                            await channel.set_permissions(message.guild.default_role, send_messages=False, reason=reason)
                            embed = discord.Embed(
                                title="🔒 تم قفل القناة | Channel Locked",
                                description=f"{channel.mention} **تم قفلها**\n**السبب:** {reason}\n\n{channel.mention} **has been locked**\n**Reason:** {reason}",
                                color=discord.Color.red(),
                            )
                            await message.channel.send(embed=embed, delete_after=10)
                            await send_mod_log(message.guild, "channel_locked", message.author, channel, reason)
                        else:
                            await channel.set_permissions(message.guild.default_role, send_messages=True, reason=reason)
                            embed = discord.Embed(
                                title="🔓 تم فتح القناة | Channel Unlocked",
                                description=f"{channel.mention} **تم فتحها**\n**السبب:** {reason}\n\n{channel.mention} **has been unlocked**\n**Reason:** {reason}",
                                color=discord.Color.green(),
                            )
                            await message.channel.send(embed=embed, delete_after=10)
                            await send_mod_log(message.guild, "channel_unlocked", message.author, channel, reason)

                        try:
                            await message.delete()
                        except Exception:
                            pass
                    
                    # Handle moderation shortcuts (ban, kick, warn, timeout)
                    elif action in ["ban", "kick", "warn", "timeout"]:
                        required_perm = {
                            "ban": "ban_members",
                            "kick": "kick_members",
                            "warn": "moderate_members",
                            "timeout": "moderate_members",
                        }.get(action)
                        if required_perm and not getattr(message.author.guild_permissions, required_perm, False):
                            continue

                        # Parse: shortcut @user reason or shortcut @user duration reason
                        content = message.content[len(shortcut):].strip()
                        
                        if not message.mentions:
                            # Show help message
                            if action == "ban":
                                help_embed = discord.Embed(
                                    title="Command: ban | أمر: حظر",
                                    description="**حظر المحتجر**\n**الأختصارات**\n`#حظر -حظر- طرد- حظرتلقائي- طرد- بفك`\n**الاستخدام**\n`/ban [user] (time m/h/d/mo/y) (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user`\n`" + shortcut + " @user spamming`\n`" + shortcut + " @user 1h spamming`\n`" + shortcut + " @user 1d breaking rules`\n`" + shortcut + " @user 1w advertising`",
                                    color=discord.Color.red()
                                )
                            elif action == "kick":
                                help_embed = discord.Embed(
                                    title="Command: kick | أمر: طرد",
                                    description="**طرد العضو**\n**الأختصارات**\n`#طرد -طرد- كيك- طرد- إطرد`\n**الاستخدام**\n`/kick [user] (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user`\n`" + shortcut + " @user spamming`\n`" + shortcut + " @user inappropriate behavior`\n`" + shortcut + " @user breaking rules`",
                                    color=discord.Color.orange()
                                )
                            elif action == "warn":
                                help_embed = discord.Embed(
                                    title="Command: warn | أمر: تحذير",
                                    description="**تحذير العضو**\n**الأختصارات**\n`#تحذير -تحذير- وارن- انذار- إنذار`\n**الاستخدام**\n`/warn [user] (reason)`\n\n**أمثلة للأمر:**\n`" + shortcut + " @user`\n`" + shortcut + " @user be respectful`\n`" + shortcut + " @user stop spamming`\n`" + shortcut + " @user read the rules`",
                                    color=discord.Color.gold()
                                )
                            elif action == "timeout":
                                help_embed = discord.Embed(
                                    title="Command: timeout | أمر: مهلة",
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
                                    dm_embed = build_mod_dm_embed("ban", message.guild, message.author, reason)
                                    await target.send(embed=dm_embed)
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
                                    dm_embed = build_mod_dm_embed("kick", message.guild, message.author, reason)
                                    await target.send(embed=dm_embed)
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
                                    dm_embed = build_mod_dm_embed("warn", message.guild, message.author, reason)
                                    await target.send(embed=dm_embed)
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
                                    duration = timedelta(seconds=value)
                                    duration_minutes = value / 60
                                elif unit == 'm':
                                    duration = timedelta(minutes=value)
                                    duration_minutes = value
                                elif unit == 'h':
                                    duration = timedelta(hours=value)
                                    duration_minutes = value * 60
                                elif unit == 'd':
                                    duration = timedelta(days=value)
                                    duration_minutes = value * 1440
                            else:
                                duration = timedelta(minutes=10)
                                duration_minutes = 10
                            
                            # Timeout user
                            await target.timeout(discord.utils.utcnow() + duration, reason=reason)
                            
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
                                    dm_embed = build_mod_dm_embed("timeout", message.guild, message.author, reason, duration=duration_str)
                                    await target.send(embed=dm_embed)
                                except Exception as e:
                                    logger.error(f"Failed to send DM: {e}")
                            
                            await send_mod_log(message.guild, "timeout", message.author, target, reason, duration_str)
                        
                        await message.delete()
                    
                except Exception as e:
                    logger.error(f"Shortcut error: {e}")
                    await message.channel.send(f"❌ Error | خطأ: {str(e)}", delete_after=5)
    
    await bot.process_commands(message)

class ModSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Ban", emoji="🔨", style=discord.ButtonStyle.danger, row=0, custom_id="modsetup:ban")
    async def ban_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BanSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Kick", emoji="👢", style=discord.ButtonStyle.danger, row=0, custom_id="modsetup:kick")
    async def kick_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = KickSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Warn", emoji="⚠️", style=discord.ButtonStyle.primary, row=0, custom_id="modsetup:warn")
    async def warn_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = WarnSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Timeout", emoji="⏱️", style=discord.ButtonStyle.primary, row=0, custom_id="modsetup:timeout")
    async def timeout_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TimeoutSettingsModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Log Channel", emoji="📝", style=discord.ButtonStyle.secondary, row=1, custom_id="modsetup:log")
    async def log_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModLogModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Clear", emoji="🧹", style=discord.ButtonStyle.secondary, row=1, custom_id="modsetup:clear")
    async def clear_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ClearSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Lock/Unlock", emoji="🔒", style=discord.ButtonStyle.secondary, row=1, custom_id="modsetup:lock_unlock")
    async def lock_unlock_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ChannelLockUnlockSettingsModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Access Role", emoji="🛡️", style=discord.ButtonStyle.secondary, row=1, custom_id="modsetup:access_role")
    async def access_role_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModAccessRoleModal()
        await interaction.response.send_modal(modal)

class BanSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔨 Ban | حظر")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Msg | رسالة",
            placeholder="You have been banned from {server}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut | اختصار",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class KickSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="👢 Kick | طرد")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Msg | رسالة",
            placeholder="You have been kicked from {server}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut | اختصار",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class WarnSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="⚠️ Warn | تحذير")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Msg | رسالة",
            placeholder="You have been warned in {server}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut | اختصار",
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
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class TimeoutSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="⏱️ Timeout | تايم اوت")
        
        self.dm_msg = discord.ui.TextInput(
            label="DM Msg | رسالة",
            placeholder="You have been timed out. Duration: {duration}. Reason: {reason}",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.add_item(self.dm_msg)
        
        self.shortcut = discord.ui.TextInput(
            label="Shortcut | اختصار",
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
            msg = "✅ Timeout settings updated | تم تحديث إعدادات المهلة"
            if self.shortcut.value:
                msg += (
                    f"\n**Shortcut | اختصار:** `{self.shortcut.value}` + @user + duration | المدة"
                    f"\nExample | مثال: `{self.shortcut.value} @user 10m reason`"
                )
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


class ChannelLockUnlockSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔒 Lock/Unlock | قفل/فتح")

        self.lock_shortcut = discord.ui.TextInput(
            label="Lock shortcut | اختصار القفل",
            placeholder="c",
            style=discord.TextStyle.short,
            required=False,
            max_length=20,
        )
        self.add_item(self.lock_shortcut)

        self.unlock_shortcut = discord.ui.TextInput(
            label="Unlock shortcut | اختصار الفتح",
            placeholder="uc",
            style=discord.TextStyle.short,
            required=False,
            max_length=20,
        )
        self.add_item(self.unlock_shortcut)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "shortcuts" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["shortcuts"] = {}

            updated = []
            if self.lock_shortcut.value:
                guild_cfg["moderation"]["shortcuts"][self.lock_shortcut.value] = {
                    "action": "lock",
                    "command": "lock",
                }
                updated.append(f"🔒 lock: `{self.lock_shortcut.value}`")

            if self.unlock_shortcut.value:
                guild_cfg["moderation"]["shortcuts"][self.unlock_shortcut.value] = {
                    "action": "unlock",
                    "command": "unlock",
                }
                updated.append(f"🔓 unlock: `{self.unlock_shortcut.value}`")

            update_guild_config(interaction.guild_id, guild_cfg)

            if not updated:
                return await interaction.response.send_message(
                    "✅ No changes | لا يوجد تغيير (اتركه فارغًا للحفاظ على الحالي)",
                    ephemeral=True,
                )
            await interaction.response.send_message(
                "✅ Updated shortcuts | تم تحديث الاختصارات:\n" + "\n".join(updated),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


class ModAccessRoleModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🛡️ Access Role | دور الصلاحية")

        self.role = discord.ui.TextInput(
            label="Roles (mentions/IDs) | الأدوار",
            placeholder="@Mods @Staff أو 1234567890 987654321",
            style=discord.TextStyle.short,
            required=False,
            max_length=80,
        )
        self.add_item(self.role)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}

            raw = (self.role.value or "").strip()
            if not raw:
                guild_cfg["moderation"]["allowed_role_id"] = None
                guild_cfg["moderation"]["allowed_role_ids"] = []
                update_guild_config(interaction.guild_id, guild_cfg)
                return await interaction.response.send_message(
                    "✅ Role gate disabled | تم تعطيل قفل الأدوار (من لديه صلاحيات ديسكورد يمكنه استخدام الأوامر).",
                    ephemeral=True,
                )

            # Accept multiple <@&id> mentions or plain numeric IDs
            ids = [int(x) for x in re.findall(r"(\d{5,})", raw)]
            if not ids:
                return await interaction.response.send_message(
                    "❌ Invalid roles | أدوار غير صحيحة (استخدم منشن/ID)",
                    ephemeral=True,
                )

            # Validate roles exist
            valid_ids = []
            valid_mentions = []
            for rid in ids:
                role_obj = interaction.guild.get_role(rid) if interaction.guild else None
                if role_obj:
                    valid_ids.append(rid)
                    valid_mentions.append(role_obj.mention)

            if not valid_ids:
                return await interaction.response.send_message(
                    "❌ Roles not found | الأدوار غير موجودة في هذا السيرفر",
                    ephemeral=True,
                )

            guild_cfg["moderation"]["allowed_role_id"] = None
            guild_cfg["moderation"]["allowed_role_ids"] = list(dict.fromkeys(valid_ids))
            update_guild_config(interaction.guild_id, guild_cfg)

            await interaction.response.send_message(
                "✅ Allowed roles updated | تم تحديث الأدوار المسموحة (الأدمن يتجاوز): " + " ".join(valid_mentions),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class ModMessagesModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Moderation Msg | رسائل الإدارة")
        guild_cfg = get_guild_config(None)
        mod_cfg = guild_cfg.get("moderation", {})
        msgs = mod_cfg.get("messages", {})
        
        self.ban_dm = discord.ui.TextInput(label="Ban DM | رسالة الحظر", default=msgs.get("ban_dm", ""), style=discord.TextStyle.paragraph, required=False)
        self.add_item(self.ban_dm)
        
        self.kick_dm = discord.ui.TextInput(label="Kick DM | رسالة الطرد", default=msgs.get("kick_dm", ""), style=discord.TextStyle.paragraph, required=False)
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
            await interaction.response.send_message("✅ Updated | تم تحديث رسائل الإدارة", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

class ModLogModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Log Channel | قناة السجل")
        
        self.channel = discord.ui.TextInput(label="Log channel ID | معرف", placeholder="1234567890", required=False)
        self.add_item(self.channel)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            
            guild_cfg["moderation"]["mod_log_channel"] = self.channel.value
            update_guild_config(interaction.guild_id, guild_cfg)
            await interaction.response.send_message(
                f"✅ Log channel set | تم تعيين قناة السجل: <#{self.channel.value}>",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


class ClearSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🧹 Clear Settings | إعدادات المسح")

        self.shortcut = discord.ui.TextInput(
            label="Shortcut | اختصار (اختياري)",
            placeholder="m",
            style=discord.TextStyle.short,
            required=False,
            max_length=20,
        )
        self.add_item(self.shortcut)

        self.default_amount = discord.ui.TextInput(
            label="Default number | رقم افتراضي",
            placeholder="5",
            style=discord.TextStyle.short,
            required=False,
            max_length=5,
        )
        self.add_item(self.default_amount)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            guild_cfg = get_guild_config(interaction.guild_id)
            if "moderation" not in guild_cfg:
                guild_cfg["moderation"] = {}
            if "shortcuts" not in guild_cfg["moderation"]:
                guild_cfg["moderation"]["shortcuts"] = {}

            updated = []
            if self.shortcut.value:
                default_amount = 5
                if self.default_amount.value and self.default_amount.value.strip().isdigit():
                    default_amount = int(self.default_amount.value.strip())

                guild_cfg["moderation"]["shortcuts"][self.shortcut.value.strip()] = {
                    "action": "delete",
                    "command": "clear",
                    "default_amount": default_amount,
                }
                updated.append(
                    f"🧹 clear: `{self.shortcut.value.strip()}` (default={default_amount})"
                )

            update_guild_config(interaction.guild_id, guild_cfg)
            if not updated:
                return await interaction.response.send_message(
                    "✅ No shortcut set (leave blank to keep current).\n✅ لم يتم تغيير شيء.",
                    ephemeral=True,
                )
            await interaction.response.send_message(
                "✅ Updated clear shortcut | تم تحديث اختصار المسح:\n" + "\n".join(updated) +
                "\n\nUsage | الاستخدام:\n"
                "- `shortcut` = clear whole channel | مسح القناة\n"
                "- `shortcut 10` = delete 10 messages | حذف 10 رسائل",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

@bot.tree.command(name="mod_setup", description="Open moderation settings panel | فتح لوحة إعدادات الإشراف")
async def mod_setup(interaction: discord.Interaction):
    """Open moderation settings panel"""
    try:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Administrator required | تحتاج صلاحية المدير",
                ephemeral=True,
            )
        
        view = ModSettingsView()
        embed = discord.Embed(
            title="⚙️ Moderation Settings | إعدادات الإشراف",
            description=(
                "**Configure actions + shortcuts (English/Arabic):**\n"
                "**إعداد الأوامر + الاختصارات (عربي/إنجليزي):**\n\n"
                "🔨 **Ban | حظر** - Message & shortcut | رسالة + اختصار\n"
                "👢 **Kick | طرد** - Message & shortcut | رسالة + اختصار\n"
                "⚠️ **Warn | تحذير** - Message & shortcut | رسالة + اختصار\n"
                "⏱️ **Timeout | مهلة** - Message & shortcut | رسالة + اختصار\n"
                "🧹 **Clear | مسح** - Shortcut + default amount | اختصار + رقم افتراضي\n"
                "🔒 **Lock/Unlock | قفل/فتح** - Shortcuts | اختصارات\n"
                "🛡️ **Access Role | صلاحية** - Who can use mod system | من يستطيع استخدام الإشراف\n"
                "📝 **Log Channel | سجل** - Set mod log channel | تحديد قناة السجل\n\n"
                "**Clear shortcut usage | استخدام اختصار المسح:**\n"
                "- `m` = clear channel | مسح القناة\n"
                "- `m 20` = delete 20 messages | حذف 20 رسالة\n\n"
                "**Slash Commands | أوامر:**\n"
                "`/ban` `/kick` `/timeout` `/warn` `/lock` `/unlock` `/clear`\n"
                "`/dm` `/say` `/set_mod_color`"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text=interaction.guild.name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="set_mod_color", description="Set embed color for moderation DMs/messages | تعيين لون الإيمبد")
@app_commands.describe(
    action="Action | العملية",
    color="Color | اللون: #FF0000 / 0xFF0000 / FF0000",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="ban", value="ban"),
        app_commands.Choice(name="kick", value="kick"),
        app_commands.Choice(name="warn", value="warn"),
        app_commands.Choice(name="timeout", value="timeout"),
    ]
)
async def set_mod_color(interaction: discord.Interaction, action: app_commands.Choice[str], color: str):
    try:
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Admin only | للأدمن فقط", ephemeral=True)

        try:
            parsed_color = parse_color(color)
        except Exception:
            return await interaction.response.send_message(
                "❌ Invalid color | لون غير صحيح. Use name (red/blue) أو hex مثل #FF0000",
                ephemeral=True,
            )

        guild_cfg = get_guild_config(interaction.guild_id)
        if "moderation" not in guild_cfg:
            guild_cfg["moderation"] = {}
        if "embed_colors" not in guild_cfg["moderation"]:
            guild_cfg["moderation"]["embed_colors"] = {}

        guild_cfg["moderation"]["embed_colors"][action.value] = color
        update_guild_config(interaction.guild_id, guild_cfg)

        preview = discord.Embed(
            title=f"✅ Updated color | تم تحديث اللون: {action.value}",
            description=f"Saved | تم الحفظ: `{color}`",
            color=parsed_color,
        )
        await interaction.response.send_message(embed=preview, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="dm", description="Send a DM to a user | إرسال رسالة خاصة")
@app_commands.describe(user="User to DM", message="Message to send")
async def dm_command(interaction: discord.Interaction, user: discord.User, message: str):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ You need Manage Messages | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="dm"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )

        await user.send(message, allowed_mentions=discord.AllowedMentions.none())
        await interaction.response.send_message("✅ DM sent", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Couldn't DM user: {str(e)}", ephemeral=True)


@bot.tree.command(name="say", description="Bot sends a message in a channel | إرسال رسالة في السيرفر")
@app_commands.describe(
    message="Message content",
    channel="Channel to send in (optional)",
    mention="Optional mention",
    user="User to mention (only if mention=user)",
)
@app_commands.choices(
    mention=[
        app_commands.Choice(name="none", value="none"),
        app_commands.Choice(name="user", value="user"),
        app_commands.Choice(name="everyone", value="everyone"),
        app_commands.Choice(name="here", value="here"),
    ]
)
async def say_command(
    interaction: discord.Interaction,
    message: str,
    channel: discord.TextChannel = None,
    mention: app_commands.Choice[str] = None,
    user: discord.User = None,
):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ You need Manage Messages | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="say"):
            return await interaction.response.send_message(
                "❌ Not allowed | غير مسموح لك باستخدام أوامر الإشراف هنا.",
                ephemeral=True,
            )

        target_channel = channel or interaction.channel

        mention_value = mention.value if mention else "none"
        content = None
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)

        if mention_value == "user":
            if not user:
                return await interaction.response.send_message("❌ Provide a user | يرجى تحديد عضو", ephemeral=True)
            content = user.mention
            allowed_mentions = discord.AllowedMentions(users=True, everyone=False, roles=False)
        elif mention_value in ("everyone", "here"):
            if not interaction.user.guild_permissions.mention_everyone and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message(
                    "❌ Mention Everyone required | تحتاج صلاحية المنشن للجميع",
                    ephemeral=True,
                )
            content = "@everyone" if mention_value == "everyone" else "@here"
            allowed_mentions = discord.AllowedMentions(everyone=True, users=False, roles=False)

        final_message = f"{content}\n{message}" if content else message
        await target_channel.send(final_message, allowed_mentions=allowed_mentions)
        await interaction.response.send_message("✅ Sent | تم الإرسال", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="embed", description="Create and send an embed | إنشاء وإرسال إيمبد")
@app_commands.describe(
    channel="Channel (optional) | القناة (اختياري)",
    title="Title (optional) | العنوان (اختياري)",
    description="Text (optional) | الوصف (اختياري)",
    color="Color (optional) | اللون (اختياري)",
    image="Upload image (optional) | ارفع صورة",
    thumbnail="Upload thumbnail (optional) | ارفع صورة صغيرة",
    image_url="Image URL (optional) | رابط الصورة",
    thumbnail_url="Thumbnail URL (optional) | رابط المصغرة",
    footer="Footer (optional) | الفوتر",
)
async def embed_command(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    title: str = None,
    description: str = None,
    color: str = None,
    image: discord.Attachment = None,
    thumbnail: discord.Attachment = None,
    image_url: str = None,
    thumbnail_url: str = None,
    footer: str = None,
):
    try:
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                "❌ You need Manage Messages | تحتاج صلاحية إدارة الرسائل",
                ephemeral=True,
            )

        target_channel = channel or interaction.channel

        if not (title or description or image_url or thumbnail_url or image or thumbnail):
            return await interaction.response.send_message(
                "❌ Fill at least one field | املأ حقلًا واحدًا على الأقل (title/description/image/thumbnail).",
                ephemeral=True,
            )

        embed = discord.Embed(
            title=title or None,
            description=description or None,
            color=parse_color(color or "#5865F2"),
            timestamp=discord.utils.utcnow(),
        )

        final_image_url = None
        if image:
            final_image_url = getattr(image, "url", None)
        elif image_url:
            final_image_url = image_url.strip()

        final_thumbnail_url = None
        if thumbnail:
            final_thumbnail_url = getattr(thumbnail, "url", None)
        elif thumbnail_url:
            final_thumbnail_url = thumbnail_url.strip()

        if final_image_url:
            embed.set_image(url=final_image_url)
        if final_thumbnail_url:
            embed.set_thumbnail(url=final_thumbnail_url)
        if footer:
            embed.set_footer(text=footer.strip())

        await target_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        await interaction.response.send_message("✅ Embed sent | تم إرسال الإمبد", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoreply_panel", description="Auto replies panel | لوحة الردود التلقائية")
async def autoreply_panel(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج صلاحية إدارة السيرفر", ephemeral=True)

        items = get_auto_replies_config(interaction.guild_id)
        embed = _build_autoreply_panel_embed(interaction.guild, items)
        view = AutoReplyPanelView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)


@bot.tree.command(name="channel_auto_panel", description="Channel auto reply/react panel | لوحة الردود في القنوات")
async def channel_auto_panel(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required | تحتاج صلاحية إدارة السيرفر", ephemeral=True)

        items = get_channel_auto_config(interaction.guild_id)
        embed = _build_channel_auto_panel_embed(interaction.guild, items)
        view = ChannelAutoPanelView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error | خطأ: {str(e)}", ephemeral=True)

# Run the bot
try:
    # Use environment variable for token
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    bot.run(token)
except Exception as e:
    logger.error(f"Bot error: {e}", exc_info=True)
