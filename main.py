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
DEPLOY_MARKER = "2026-02-04T00:00Z"

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
    _set_default("panel_title", "🎫 Tickets | التكيت")
    _set_default("panel_description", "اختر نوع التكيت من القائمة أدناه | Choose a ticket type below")
    _set_default("dropdown_placeholder", "إضغط لفتح التكيت")
    _set_default("menu_placeholder", "تعديل التكيت")
    _set_default("panel_image", "")
    _set_default("panel_author_icon", "")
    _set_default("panel_author_name", "Ticket System")
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
        embed.add_field(name="No auto replies | لا يوجد", value="Use **Add** to create one.", inline=False)
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
        name=f"Rules ({start+1}-{end} / {total})",
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
            label="Trigger (word/sentence)",
            placeholder="hi",
            required=True,
            max_length=200,
        )
        self.add_item(self.trigger)

        self.reply = discord.ui.TextInput(
            label="Reply text",
            placeholder="welcome!",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
        )
        self.add_item(self.reply)

        self.match = discord.ui.TextInput(
            label="Match: contains/exact/startswith/endswith",
            placeholder="contains",
            required=False,
            max_length=20,
        )
        self.add_item(self.match)

        self.mode = discord.ui.TextInput(
            label="Mode: send/reply",
            placeholder="send",
            required=False,
            max_length=10,
        )
        self.add_item(self.mode)

        # NOTE: Discord modals allow max 5 inputs.
        # Put mention + case_sensitive + roles in one field.
        self.options = discord.ui.TextInput(
            label="Options (mention/case/roles)",
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
        await interaction.response.send_message("✅ Auto reply added.", ephemeral=True)


class AutoReplyEditModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Edit Auto Reply | تعديل رد")
        self.guild_id = int(guild_id)

        self.index = discord.ui.TextInput(
            label="Rule number",
            placeholder="1",
            required=True,
            max_length=5,
        )
        self.add_item(self.index)

        self.trigger = discord.ui.TextInput(
            label="Trigger (leave blank = keep)",
            placeholder="hello",
            required=False,
            max_length=200,
        )
        self.add_item(self.trigger)

        self.reply = discord.ui.TextInput(
            label="Reply text (leave blank = keep)",
            placeholder="welcome!",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1500,
        )
        self.add_item(self.reply)

        self.options = discord.ui.TextInput(
            label="Options (match/mode/mention/case/roles)",
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
            await interaction.response.send_message(f"✅ Updated rule {idx}.", ephemeral=True)
        except Exception as e:
            logger.error(f"AutoReplyEditModal error: {e}")
            try:
                await interaction.response.send_message("❌ Error while editing rule.", ephemeral=True)
            except Exception:
                pass


class AutoReplyTestModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Test Auto Reply | اختبار")
        self.guild_id = int(guild_id)
        self.text = discord.ui.TextInput(
            label="Message text to test",
            placeholder="type something...",
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
                        title="✅ Match Found",
                        description=f"Rule: `{idx}`\nOptions: `{rule.get('match','contains')}` / `{mode}` / mention={mention}",
                        color=discord.Color.green(),
                    )
                    embed.add_field(name="Trigger", value=trigger[:1024], inline=False)
                    embed.add_field(name="Bot would send", value=preview[:1024], inline=False)
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

            await interaction.response.send_message("❌ No rule matched that text.", ephemeral=True)
        except Exception as e:
            logger.error(f"AutoReplyTestModal error: {e}")
            try:
                await interaction.response.send_message("❌ Error while testing rules.", ephemeral=True)
            except Exception:
                pass


class AutoReplyIndexModal(discord.ui.Modal):
    def __init__(self, guild_id: int, mode: str):
        super().__init__(title=f"Auto Reply: {mode.title()}")
        self.guild_id = int(guild_id)
        self.mode = mode

        self.index = discord.ui.TextInput(
            label="Rule number (from panel)",
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
            return await interaction.response.send_message("❌ Invalid number.", ephemeral=True)

        if idx < 1 or idx > len(items):
            return await interaction.response.send_message("❌ Out of range.", ephemeral=True)

        i = idx - 1
        if self.mode == "remove":
            removed = items.pop(i)
            update_guild_config(interaction.guild_id, {"auto_replies": items})
            return await interaction.response.send_message(f"✅ Removed: {removed.get('trigger')}", ephemeral=True)

        if self.mode == "toggle":
            items[i]["enabled"] = not items[i].get("enabled", True)
            update_guild_config(interaction.guild_id, {"auto_replies": items})
            state = "enabled" if items[i]["enabled"] else "disabled"
            return await interaction.response.send_message(f"✅ Toggled rule {idx} ({state}).", ephemeral=True)

        await interaction.response.send_message("❌ Unknown action.", ephemeral=True)


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

    @discord.ui.button(label="Add", style=discord.ButtonStyle.success, row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(AutoReplyAddModal(self.guild_id))

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.primary, row=0)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(AutoReplyEditModal(self.guild_id))

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(AutoReplyIndexModal(self.guild_id, "remove"))

    @discord.ui.button(label="Toggle", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(AutoReplyIndexModal(self.guild_id, "toggle"))

    @discord.ui.button(label="Test", style=discord.ButtonStyle.secondary, row=1)
    async def test_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(AutoReplyTestModal(self.guild_id))

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, row=1)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await self._refresh(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, row=1)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        items = get_auto_replies_config(interaction.guild_id)
        total_pages = max(1, (len(items) + 8 - 1) // 8)
        self.page = min(total_pages - 1, self.page + 1)
        await self._refresh(interaction)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)


def _build_channel_auto_panel_embed(guild: discord.Guild, items: list[dict]) -> discord.Embed:
    embed = discord.Embed(
        title="📌 Channel Auto Panel | لوحة الردود في القنوات",
        description="When someone sends a message in a configured channel, the bot replies and can react.",
        color=discord.Color.green(),
    )
    if not items:
        embed.add_field(name="No channel rules", value="Use **Add** to create one.", inline=False)
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
        ch_text = f"<#{channel_id}>" if channel_id else "(no channel)"
        lines.append(f"`{i}` {enabled} [{mention}] {ch_text} → {rep} | {reactions}")
    embed.add_field(name="Rules", value="\n".join(lines), inline=False)
    embed.set_footer(text=f"Server: {guild.name}")
    return embed


class ChannelAutoAddModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        super().__init__(title="Add Channel Auto Rule")
        self.guild_id = int(guild_id)

        self.channel = discord.ui.TextInput(
            label="Channel mention or ID",
            placeholder="#general or 1234567890",
            required=True,
            max_length=60,
        )
        self.add_item(self.channel)

        self.reply = discord.ui.TextInput(
            label="Reply text",
            placeholder="Thanks for your message!",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
        )
        self.add_item(self.reply)

        self.reactions = discord.ui.TextInput(
            label="Reactions (space-separated, optional)",
            placeholder="✅ 🔥",
            required=False,
            max_length=200,
        )
        self.add_item(self.reactions)

        self.mention = discord.ui.TextInput(
            label="Mention user in reply? yes/no",
            placeholder="no",
            required=False,
            max_length=10,
        )
        self.add_item(self.mention)

        self.enabled = discord.ui.TextInput(
            label="Enabled? yes/no",
            placeholder="yes",
            required=False,
            max_length=10,
        )
        self.add_item(self.enabled)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Server only", ephemeral=True)

        raw = self.channel.value.strip()
        m = re.search(r"(\d{5,})", raw)
        if not m:
            return await interaction.response.send_message("❌ Invalid channel.", ephemeral=True)
        channel_id = int(m.group(1))
        channel_obj = interaction.guild.get_channel(channel_id)
        if not channel_obj:
            return await interaction.response.send_message("❌ Channel not found in this server.", ephemeral=True)

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
        await interaction.response.send_message("✅ Channel auto rule added.", ephemeral=True)


class ChannelAutoIndexModal(discord.ui.Modal):
    def __init__(self, guild_id: int, mode: str):
        super().__init__(title=f"Channel Auto: {mode.title()}")
        self.guild_id = int(guild_id)
        self.mode = mode

        self.index = discord.ui.TextInput(
            label="Rule number (from panel)",
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
            return await interaction.response.send_message("❌ Invalid number.", ephemeral=True)

        if idx < 1 or idx > len(items):
            return await interaction.response.send_message("❌ Out of range.", ephemeral=True)

        i = idx - 1
        if self.mode == "remove":
            removed = items.pop(i)
            update_guild_config(interaction.guild_id, {"channel_auto": items})
            return await interaction.response.send_message(f"✅ Removed rule for <#{removed.get('channel_id')}>.", ephemeral=True)

        if self.mode == "toggle":
            items[i]["enabled"] = not items[i].get("enabled", True)
            update_guild_config(interaction.guild_id, {"channel_auto": items})
            state = "enabled" if items[i]["enabled"] else "disabled"
            return await interaction.response.send_message(f"✅ Toggled rule {idx} ({state}).", ephemeral=True)

        await interaction.response.send_message("❌ Unknown action.", ephemeral=True)


class ChannelAutoPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = int(guild_id)

    async def _refresh(self, interaction: discord.Interaction):
        items = get_channel_auto_config(interaction.guild_id)
        embed = _build_channel_auto_panel_embed(interaction.guild, items)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Add", style=discord.ButtonStyle.success, row=0)
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(ChannelAutoAddModal(self.guild_id))

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, row=0)
    async def remove_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(ChannelAutoIndexModal(self.guild_id, "remove"))

    @discord.ui.button(label="Toggle", style=discord.ButtonStyle.primary, row=0)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)
        await interaction.response.send_modal(ChannelAutoIndexModal(self.guild_id, "toggle"))

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, row=0)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._refresh(interaction)

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
    embed.set_footer(text=interaction.guild.name)
    await interaction.response.send_message(embed=embed, view=GiveawayPanelView(), ephemeral=True)

@bot.event
async def on_ready():
    """Bot is ready"""
    try:
        # Register persistent views once so old panels keep working after restarts.
        if not getattr(bot, "_persistent_views_added", False):
            bot.add_view(ModSettingsView())
            bot._persistent_views_added = True

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
        embed.set_footer(text=interaction.guild.name)
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
            options.append(
                discord.SelectOption(
                    label=option["label"],
                    emoji=option.get("emoji", "🎫"),
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
                title=self.ticket_type,
                description=tcfg.get("messages", {}).get("ticket_created_desc", "✅ تم فتح التكيت بنجاح"),
                color=parse_color(tcfg.get("embed_color", "#9B59B6"))
            )
            
            # Add ticket image
            if tcfg.get("panel_image") and str(tcfg.get("panel_image")).strip():
                embed.set_image(url=str(tcfg.get("panel_image")).strip())
            
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
                color=parse_color(tcfg.get("embed_color", "#9B59B6"))
            )
            
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
                title=messages.get("log_ticket_opened", "📬 Ticket Opened"),
                color=parse_color(tcfg.get("embed_color", "#9B59B6")),
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
            label=tcfg.get("buttons", {}).get("close", "CLOSE"),
            emoji=tcfg.get("buttons", {}).get("close_emoji", "🔒"),
            style=close_style,
            custom_id=f"ticket_close_{channel_id}"
        )
        close_btn.callback = self.close_ticket
        self.add_item(close_btn)
        
        # Claim button (ADMIN ONLY)
        claim_style = style_map.get(tcfg.get("buttons", {}).get("claim_style", "primary").lower(), discord.ButtonStyle.primary)
        claim_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("claim", "CLAIM"),
            emoji=tcfg.get("buttons", {}).get("claim_emoji", "👥"),
            style=claim_style,
            custom_id=f"ticket_claim_{channel_id}"
        )
        claim_btn.callback = self.claim_ticket
        self.add_item(claim_btn)
        
        # Ping Admin button (MEMBER CAN USE)
        ping_admin_style = style_map.get(tcfg.get("buttons", {}).get("ping_admin_style", "secondary").lower(), discord.ButtonStyle.secondary)
        ping_admin_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("ping_admin", "استدعاء الإدارة"),
            emoji=tcfg.get("buttons", {}).get("ping_admin_emoji", "📢"),
            style=ping_admin_style,
            custom_id=f"ticket_ping_admin_{channel_id}"
        )
        ping_admin_btn.callback = self.ping_admin
        self.add_item(ping_admin_btn)
        
        # Mention Member button (ADMIN ONLY)
        mention_member_style = style_map.get(tcfg.get("buttons", {}).get("mention_member_style", "secondary").lower(), discord.ButtonStyle.secondary)
        mention_member_btn = discord.ui.Button(
            label=tcfg.get("buttons", {}).get("mention_member", "منشن العضو"),
            emoji=tcfg.get("buttons", {}).get("mention_member_emoji", "👤"),
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
                title = messages.get("log_ticket_closed", "🔒 Ticket Closed")
                by_label = messages.get("log_closed_by", "Closed By")
            elif action == "claimed":
                title = messages.get("log_ticket_claimed", "👥 Ticket Claimed")
                by_label = messages.get("log_claimed_by", "Claimed By")
            else:
                return
            
            embed = discord.Embed(
                title=title,
                color=parse_color(tcfg.get("embed_color", "#9B59B6")),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name=by_label, value=interaction.user.mention, inline=True)
            embed.add_field(name=messages.get("log_channel", "Channel"), value=interaction.channel.mention, inline=True)
            
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
            placeholder=tcfg.get("menu_placeholder", "تعديل التكيت"),
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

        tcfg = get_ticket_config(interaction.guild_id)
        
        # Create embed
        embed = discord.Embed(
            title=tcfg.get("panel_title", "🎫 Tickets | التكيت"),
            description=tcfg.get("panel_description", "اختر نوع التكيت من القائمة أدناه | Choose a ticket type below"),
            color=parse_color(tcfg.get("embed_color", "#9B59B6"))
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
        tcfg = get_ticket_config(interaction.guild_id)
        tcfg["category_id"] = category.id
        update_guild_config(interaction.guild_id, {"tickets": tcfg})
        
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
        tcfg = get_ticket_config(interaction.guild_id)
        tcfg["log_channel_id"] = channel.id
        update_guild_config(interaction.guild_id, {"tickets": tcfg})
        
        await interaction.response.send_message(f"✅ Ticket log channel set to: {channel.mention}", ephemeral=True)
        logger.info(f"Ticket log channel set to {channel.id}")
        
    except Exception as e:
        logger.error(f"Error setting log channel: {e}")
        await interaction.response.send_message("❌ Error", ephemeral=True)

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

    embed.set_footer(text=f"Guild: {guild.name}")
    return embed


class TicketSetupPanelView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=180)
        self.guild_id = int(guild_id)

    @discord.ui.button(label="Panel | اللوحة", emoji="🎨", style=discord.ButtonStyle.primary, row=0)
    async def panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupPanelModal(self.guild_id))

    @discord.ui.button(label="Channels | القنوات", emoji="📁", style=discord.ButtonStyle.primary, row=0)
    async def channels(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupChannelsModal(self.guild_id))

    @discord.ui.button(label="Roles | الأدوار", emoji="👥", style=discord.ButtonStyle.primary, row=0)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupRolesModal(self.guild_id))

    @discord.ui.button(label="Add Option | إضافة خيار", emoji="➕", style=discord.ButtonStyle.success, row=1)
    async def add_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupAddOptionModal(self.guild_id))

    @discord.ui.button(label="Remove Option | حذف خيار", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def remove_option(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketSetupRemoveOptionModal(self.guild_id))

    @discord.ui.button(label="Refresh | تحديث", emoji="🔄", style=discord.ButtonStyle.secondary, row=1)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        tcfg = get_ticket_config(self.guild_id)
        embed = _build_ticket_setup_embed(interaction.guild, tcfg)
        await interaction.response.edit_message(embed=embed, view=self)


class TicketSetupPanelModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="🎨 Ticket Panel Settings")

        self.title_input = discord.ui.TextInput(
            label="Panel Title",
            default=str(tcfg.get("panel_title", ""))[:256],
            max_length=256,
            required=False,
        )
        self.desc_input = discord.ui.TextInput(
            label="Panel Description",
            default=str(tcfg.get("panel_description", ""))[:2000],
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=False,
        )
        self.color_input = discord.ui.TextInput(
            label="Embed Color (#RRGGBB or name)",
            default=str(tcfg.get("embed_color", "#9B59B6"))[:32],
            max_length=32,
            required=False,
        )
        self.dropdown_ph = discord.ui.TextInput(
            label="Dropdown Placeholder",
            default=str(tcfg.get("dropdown_placeholder", ""))[:100],
            max_length=100,
            required=False,
        )
        self.menu_ph = discord.ui.TextInput(
            label="Menu Placeholder",
            default=str(tcfg.get("menu_placeholder", ""))[:100],
            max_length=100,
            required=False,
        )

        self.add_item(self.title_input)
        self.add_item(self.desc_input)
        self.add_item(self.color_input)
        self.add_item(self.dropdown_ph)
        self.add_item(self.menu_ph)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        if self.title_input.value.strip():
            tcfg["panel_title"] = self.title_input.value.strip()
        if self.desc_input.value.strip():
            tcfg["panel_description"] = self.desc_input.value.strip()
        if self.color_input.value.strip():
            tcfg["embed_color"] = self.color_input.value.strip()
        if self.dropdown_ph.value.strip():
            tcfg["dropdown_placeholder"] = self.dropdown_ph.value.strip()
        if self.menu_ph.value.strip():
            tcfg["menu_placeholder"] = self.menu_ph.value.strip()

        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Updated ticket panel settings", ephemeral=True)


class TicketSetupChannelsModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="📁 Ticket Channels")

        self.category_id = discord.ui.TextInput(
            label="Category ID (optional)",
            default=str(tcfg.get("category_id") or ""),
            required=False,
            max_length=25,
        )
        self.log_channel_id = discord.ui.TextInput(
            label="Log Channel ID (optional)",
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
        await interaction.response.send_message("✅ Updated ticket channels", ephemeral=True)


class TicketSetupRolesModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        tcfg = get_ticket_config(self.guild_id)
        super().__init__(title="👥 Ticket Roles")

        self.support_roles = discord.ui.TextInput(
            label="Support Role IDs/mentions (space separated)",
            default=" ".join(str(rid) for rid in (tcfg.get("support_roles") or []))[:400],
            required=False,
            max_length=400,
        )
        self.ping_roles = discord.ui.TextInput(
            label="Ping Role IDs/mentions (space separated)",
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
        await interaction.response.send_message("✅ Updated ticket roles", ephemeral=True)


class TicketSetupAddOptionModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        super().__init__(title="➕ Add Ticket Option")

        self.label_input = discord.ui.TextInput(label="Label", placeholder="Support | دعم", max_length=100)
        self.emoji_input = discord.ui.TextInput(label="Emoji (optional)", required=False, max_length=20)
        self.desc_input = discord.ui.TextInput(
            label="Description (optional)",
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
        await interaction.response.send_message("✅ Added ticket option", ephemeral=True)


class TicketSetupRemoveOptionModal(discord.ui.Modal):
    def __init__(self, guild_id: int):
        self.guild_id = int(guild_id)
        super().__init__(title="🗑️ Remove Ticket Option")
        self.index_input = discord.ui.TextInput(label="Option number", placeholder="1", max_length=4)
        self.add_item(self.index_input)

    async def on_submit(self, interaction: discord.Interaction):
        tcfg = get_ticket_config(self.guild_id)
        options = tcfg.get("ticket_options", []) or []
        try:
            idx = int(self.index_input.value.strip()) - 1
        except Exception:
            return await interaction.response.send_message("❌ Invalid number", ephemeral=True)

        if idx < 0 or idx >= len(options):
            return await interaction.response.send_message("❌ Out of range", ephemeral=True)

        options.pop(idx)
        tcfg["ticket_options"] = options
        update_guild_config(self.guild_id, {"tickets": tcfg})
        await interaction.response.send_message("✅ Removed ticket option", ephemeral=True)

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
        "ban_log": "🔨 **User Banned**",
        "kick_log": "👢 **User Kicked**",
        "warn_log": "⚠️ **User Warned**",
        "timeout_log": "⏱️ **User Timed Out**",
        "channel_locked": "🔒 **Channel Locked**",
        "channel_unlocked": "🔓 **Channel Unlocked**",
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
        reason=reason or "No reason provided",
        duration=duration or "N/A",
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
            embed.add_field(name="Channel", value=f"{target.mention} ({target.id})", inline=True)
        else:
            embed.add_field(name="User", value=f"{target.mention} ({target.id})", inline=True)

        embed.add_field(name="Moderator", value=f"{moderator.mention}", inline=True)
        if duration:
            embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason or "No reason provided", inline=False)
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
                title="Command: ban",
                description="**حظر المحتجر**\n**الأختصارات**\n`#حظر -حظر- طرد- حظرتلقائي- طرد- بفك`\n**الاستخدام**\n`/ban [user] (time m/h/d/mo/y) (reason)`\n\n**أمثلة للأمر:**\n`/ban @user`\n`/ban @user spamming`\n`/ban @user 1h spamming`\n`/ban @user 1d breaking rules`\n`/ban @user 1w advertising`",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحظر الأعضاء | You don't have permission to ban members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="ban"):
            return await interaction.response.send_message(
                "❌ You are not allowed to use moderation commands in this server.",
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
                title="Command: kick",
                description="**طرد العضو**\n**الأختصارات**\n`#طرد -طرد- كيك- طرد- إطرد`\n**الاستخدام**\n`/kick [user] (reason)`\n\n**أمثلة للأمر:**\n`/kick @user`\n`/kick @user spamming`\n`/kick @user inappropriate behavior`\n`/kick @user breaking rules`",
                color=discord.Color.orange()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ ليس لديك صلاحية لطرد الأعضاء | You don't have permission to kick members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="kick"):
            return await interaction.response.send_message(
                "❌ You are not allowed to use moderation commands in this server.",
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
                title="Command: timeout",
                description="**مهلة العضو**\n**الأختصارات**\n`#مهلة -مهلة- ميوت- كتم- صامت`\n**الاستخدام**\n`/timeout [user] [duration] (reason)`\n\n**أمثلة للأمر:**\n`/timeout @user 10` (10 minutes)\n`/timeout @user 10 spamming`\n`/timeout @user 60 trolling`\n`/timeout @user 1440 breaking rules` (1 day)\n\n**Duration in minutes**",
                color=discord.Color.yellow()
            )
            return await interaction.response.send_message(embed=help_embed, ephemeral=True)
        
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ You don't have permission to timeout members", ephemeral=True)
        
        mod_cfg = get_mod_config(interaction.guild_id)
        if not is_mod_authorized(interaction.user, mod_cfg, action="timeout"):
            return await interaction.response.send_message(
                "❌ You are not allowed to use moderation commands in this server.",
                ephemeral=True,
            )

        # Discord timeout max is 28 days (40320 minutes)
        if duration < 1 or duration > 40320:
            return await interaction.response.send_message("❌ Duration must be between 1 and 40320 minutes (28 days)", ephemeral=True)

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
        if not is_mod_authorized(interaction.user, mod_cfg, action="warn"):
            return await interaction.response.send_message(
                "❌ You are not allowed to use moderation commands in this server.",
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
                "❌ You are not allowed to use moderation commands in this server.",
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
                "❌ You are not allowed to use moderation commands in this server.",
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
                "❌ You are not allowed to use moderation commands in this server.",
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
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


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
                    await message.channel.send(f"❌ Error: {str(e)}", delete_after=5)
    
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
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

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
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

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
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

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
            msg = f"✅ Timeout settings updated!"
            if self.shortcut.value:
                msg += f"\n**Shortcut:** Type `{self.shortcut.value}` + mention user + duration (e.g., `{self.shortcut.value} @user 10m reason`)"
            await interaction.response.send_message(msg, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ChannelLockUnlockSettingsModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔒 Lock/Unlock Shortcuts")

        self.lock_shortcut = discord.ui.TextInput(
            label="Lock shortcut (e.g., c, lock)",
            placeholder="c",
            style=discord.TextStyle.short,
            required=False,
            max_length=20,
        )
        self.add_item(self.lock_shortcut)

        self.unlock_shortcut = discord.ui.TextInput(
            label="Unlock shortcut (e.g., uc, unlock)",
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
                    "✅ No shortcuts set (leave blank to keep current).",
                    ephemeral=True,
                )
            await interaction.response.send_message(
                "✅ Updated shortcuts:\n" + "\n".join(updated),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ModAccessRoleModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🛡️ Moderation Access Role")

        self.role = discord.ui.TextInput(
            label="Role mentions or IDs (blank = disable)",
            placeholder="@Mods @Staff or 1234567890 987654321",
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
                    "✅ Role gate disabled (anyone with Discord permissions can use mod commands).",
                    ephemeral=True,
                )

            # Accept multiple <@&id> mentions or plain numeric IDs
            ids = [int(x) for x in re.findall(r"(\d{5,})", raw)]
            if not ids:
                return await interaction.response.send_message("❌ Invalid roles. Use role mentions or IDs.", ephemeral=True)

            # Validate roles exist
            valid_ids = []
            valid_mentions = []
            for rid in ids:
                role_obj = interaction.guild.get_role(rid) if interaction.guild else None
                if role_obj:
                    valid_ids.append(rid)
                    valid_mentions.append(role_obj.mention)

            if not valid_ids:
                return await interaction.response.send_message("❌ Roles not found in this server.", ephemeral=True)

            guild_cfg["moderation"]["allowed_role_id"] = None
            guild_cfg["moderation"]["allowed_role_ids"] = list(dict.fromkeys(valid_ids))
            update_guild_config(interaction.guild_id, guild_cfg)

            await interaction.response.send_message(
                "✅ Allowed roles updated (admins bypass): " + " ".join(valid_mentions),
                ephemeral=True,
            )
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
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="set_mod_color", description="Set embed color for moderation DMs/messages | تعيين لون الإيمبد")
@app_commands.describe(action="Which action", color="Color name or hex: #FF0000 / 0xFF0000 / FF0000")
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
                "❌ Invalid color. Use a name (red/blue/...) or hex like #FF0000",
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
            title=f"✅ Updated color: {action.value}",
            description=f"Saved: `{color}`",
            color=parsed_color,
        )
        await interaction.response.send_message(embed=preview, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


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
                "❌ You are not allowed to use moderation commands in this server.",
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
                "❌ You are not allowed to use moderation commands in this server.",
                ephemeral=True,
            )

        target_channel = channel or interaction.channel

        mention_value = mention.value if mention else "none"
        content = None
        allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)

        if mention_value == "user":
            if not user:
                return await interaction.response.send_message("❌ Please provide a user to mention", ephemeral=True)
            content = user.mention
            allowed_mentions = discord.AllowedMentions(users=True, everyone=False, roles=False)
        elif mention_value in ("everyone", "here"):
            if not interaction.user.guild_permissions.mention_everyone and not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("❌ You need Mention Everyone permission", ephemeral=True)
            content = "@everyone" if mention_value == "everyone" else "@here"
            allowed_mentions = discord.AllowedMentions(everyone=True, users=False, roles=False)

        final_message = f"{content}\n{message}" if content else message
        await target_channel.send(final_message, allowed_mentions=allowed_mentions)
        await interaction.response.send_message("✅ Sent", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="embed", description="Create and send an embed | إنشاء وإرسال إيمبد")
@app_commands.describe(
    channel="Channel to send in (optional)",
    title="Embed title (optional)",
    description="Embed description/text (optional)",
    color="Color name or hex (optional)",
    image="Upload image (optional)",
    thumbnail="Upload thumbnail (optional)",
    image_url="Image URL (optional)",
    thumbnail_url="Thumbnail URL (optional)",
    footer="Footer text (optional)",
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
                "❌ Please fill at least one field (title/description/image/thumbnail).",
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
        await interaction.response.send_message("✅ Embed sent", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="autoreply_panel", description="Auto replies panel | لوحة الردود التلقائية")
async def autoreply_panel(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)

        items = get_auto_replies_config(interaction.guild_id)
        embed = _build_autoreply_panel_embed(interaction.guild, items)
        view = AutoReplyPanelView(interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


@bot.tree.command(name="channel_auto_panel", description="Channel auto reply/react panel | لوحة الردود في القنوات")
async def channel_auto_panel(interaction: discord.Interaction):
    try:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Manage Server required", ephemeral=True)

        items = get_channel_auto_config(interaction.guild_id)
        embed = _build_channel_auto_panel_embed(interaction.guild, items)
        view = ChannelAutoPanelView(interaction.guild_id)
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
