# bloxlink.py

import requests

from config import BLOXLINK_API_KEY, DISCORD_GUILD_ID


def get_roblox_id(discord_user_id: int):
    """
    Returns (roblox_id, status).

    Status:
      found       - Linked Roblox account found.
      not_linked  - No linked account found.
      error       - API or configuration problem.
    """

    if not BLOXLINK_API_KEY or not DISCORD_GUILD_ID:
        return None, "error"

    url = (
        f"https://api.blox.link/v4/public/guilds/"
        f"{DISCORD_GUILD_ID}/discord-to-roblox/"
        f"{discord_user_id}"
    )

    headers = {
        "Authorization": BLOXLINK_API_KEY
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if response.status_code == 404:
            return None, "not_linked"

        response.raise_for_status()
        data = response.json()

        roblox_id = data.get("robloxID")

        if roblox_id is None:
            return None, "error"

        return str(roblox_id), "found"

    except requests.RequestException:
        return None, "error"

    except (ValueError, TypeError):
        return None, "error"


def get_discord_ids(roblox_id: str):
    """
    Returns (discord_ids, status).

    Status:
      found      - One or more linked Discord IDs found.
      not_found  - No linked Discord accounts found.
      error      - API or configuration problem.
    """

    if not BLOXLINK_API_KEY or not DISCORD_GUILD_ID:
        return [], "error"

    url = (
        f"https://api.blox.link/v4/public/guilds/"
        f"{DISCORD_GUILD_ID}/roblox-to-discord/"
        f"{roblox_id}"
    )

    headers = {
        "Authorization": BLOXLINK_API_KEY
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if response.status_code == 404:
            return [], "not_found"

        response.raise_for_status()
        data = response.json()

        discord_ids = data.get("discordIDs")

        if not isinstance(discord_ids, list):
            return [], "error"

        return [str(user_id) for user_id in discord_ids], "found"

    except requests.RequestException:
        return [], "error"

    except (ValueError, TypeError):
        return [], "error"