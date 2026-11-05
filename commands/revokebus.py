# revokebus.py

import asyncio
import re

import discord
from discord import app_commands
from discord.ext import commands

from database.sheets import get_worksheet
from utils.bloxlink import get_discord_ids


LOG_CHANNEL_NAME = "assignment-logs"

ALLOWED_ROLES = (
    "Transportation Supervisor",
    "Transportation Director",
)


def remove_route_from_nickname(nickname: str, route: str):
    """
    Remove one route from the nickname while preserving
    any other assigned routes.

    Returns (new_nickname, route_was_found).
    """

    match = re.search(r"⌞(.*?)⌝\s*$", nickname)

    if not match:
        return nickname, False

    base_name = nickname[:match.start()].strip()

    routes = [
        item.strip()
        for item in match.group(1).split("|")
        if item.strip()
    ]

    updated_routes = [
        item for item in routes
        if item.casefold() != route.casefold()
    ]

    if len(updated_routes) == len(routes):
        return nickname, False

    if updated_routes:
        new_nickname = (
            f"{base_name} ⌞{' | '.join(updated_routes)}⌝"
        )
    else:
        new_nickname = base_name

    return new_nickname, True


class RevocationCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="revokebus",
        description="Revoke a driver's bus assignment."
    )
    @app_commands.describe(
        bus_number="The bus number being revoked."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_any_role(*ALLOWED_ROLES)
    async def revokebus(
        self,
        interaction: discord.Interaction,
        bus_number: str,
    ):

        await interaction.response.defer(ephemeral=True)

        # Find the bus in Google Sheets.
        try:
            worksheet = await asyncio.to_thread(get_worksheet)

            bus_numbers = await asyncio.to_thread(
                worksheet.col_values, 3
            )

            matching_rows = [
                row_number
                for row_number, value in enumerate(
                    bus_numbers, start=1
                )
                if value.strip().casefold()
                == bus_number.strip().casefold()
            ]

            if not matching_rows:
                await interaction.followup.send(
                    f"Bus `{bus_number}` was not found.",
                    ephemeral=True
                )
                return

            if len(matching_rows) > 1:
                await interaction.followup.send(
                    f"Bus `{bus_number}` appears more than once "
                    "in column C. Please fix the spreadsheet.",
                    ephemeral=True
                )
                return

            row = matching_rows[0]

            route = await asyncio.to_thread(
                lambda: worksheet.cell(row, 9).value
            )

            roblox_id = await asyncio.to_thread(
                lambda: worksheet.cell(row, 10).value
            )

            if not route or not route.strip():
                await interaction.followup.send(
                    f"Bus `{bus_number}` has no route in column I.",
                    ephemeral=True
                )
                return

            route = route.strip()

            if not roblox_id or not roblox_id.strip():
                await interaction.followup.send(
                    f"Bus `{bus_number}` has no Roblox ID in "
                    "column J. Nothing was changed.",
                    ephemeral=True
                )
                return

            roblox_id = roblox_id.strip()

        except Exception as error:
            print(f"Spreadsheet lookup error: {error}")

            await interaction.followup.send(
                "I couldn't look up that bus in Google Sheets.",
                ephemeral=True
            )
            return

        # Find the Discord account linked to the Roblox ID.
        discord_ids, lookup_status = await asyncio.to_thread(
            get_discord_ids, roblox_id
        )

        if lookup_status == "not_found" or not discord_ids:
            await interaction.followup.send(
                "Bloxlink couldn't find a Discord account linked "
                "to this Roblox ID. Nothing was changed.",
                ephemeral=True
            )
            return

        if lookup_status != "found":
            await interaction.followup.send(
                "The Bloxlink lookup failed. Nothing was changed.",
                ephemeral=True
            )
            return

        if len(discord_ids) != 1:
            await interaction.followup.send(
                "Bloxlink returned multiple Discord accounts "
                "for this Roblox ID. I stopped to avoid changing "
                "the wrong member.",
                ephemeral=True
            )
            return

        # Fetch the driver from this Discord server.
        try:
            driver = await interaction.guild.fetch_member(
                int(discord_ids[0])
            )

        except discord.NotFound:
            await interaction.followup.send(
                "The linked Discord member could not be found "
                "in this server. Nothing was changed.",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:
            print(f"Discord member lookup error: {error}")

            await interaction.followup.send(
                "I couldn't retrieve the driver from Discord. "
                "Nothing was changed.",
                ephemeral=True
            )
            return

        # Prepare the nickname without the revoked route.
        old_nickname = driver.nick
        current_nickname = driver.display_name

        new_nickname, route_was_found = (
            remove_route_from_nickname(
                current_nickname,
                route
            )
        )

        # Change the nickname if necessary.
        if new_nickname != current_nickname:
            try:
                await driver.edit(
                    nick=new_nickname,
                    reason=(
                        f"Bus {bus_number} / Route {route} "
                        f"revoked by {interaction.user}"
                    )
                )

            except discord.Forbidden:
                await interaction.followup.send(
                    "I couldn't change the driver's nickname. "
                    "Check my Manage Nicknames permission and "
                    "role hierarchy. Nothing was cleared.",
                    ephemeral=True
                )
                return

            except discord.HTTPException as error:
                await interaction.followup.send(
                    f"Discord rejected the nickname change: {error}",
                    ephemeral=True
                )
                return

        # Clear columns J and K.
        try:
            await asyncio.to_thread(
                worksheet.batch_update,
                [
                    {
                        "range": f"J{row}:K{row}",
                        "values": [["", ""]],
                    }
                ]
            )

        except Exception as error:
            print(f"Spreadsheet update error: {error}")

            # Attempt to restore the original nickname.
            if new_nickname != current_nickname:
                try:
                    await driver.edit(
                        nick=old_nickname,
                        reason="Rolling back failed bus revocation"
                    )
                except discord.HTTPException:
                    pass

            await interaction.followup.send(
                "The spreadsheet update failed. I attempted "
                "to restore the driver's previous nickname. "
                "Please check the spreadsheet before retrying.",
                ephemeral=True
            )
            return

        # Find the assignment log channel.
        log_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=LOG_CHANNEL_NAME
        )

        # Format the revocation log.
        admin_name = interaction.user.display_name.upper()

        log_message = (
            "## VEHICLE ASSIGNMENT CHANGE LOG\n"
            "```ansi\n"
            f"\x1b[0m\x1b[1mADMIN:      \x1b[0m"
            f"\x1b[31m {admin_name}\n"
            f"\x1b[0m\x1b[1mVEHICLE:    \x1b[0m"
            f"\x1b[33m {bus_number.upper()}\n"
            f"\x1b[0m\x1b[1mROUTE:      \x1b[0m"
            f"\x1b[34m {route.upper()}\n"
            f"\x1b[0m\x1b[1mDRIVER:     \x1b[0m"
            f"\x1b[32m N/A\n"
            f"\x1b[0m\x1b[1mDRIVER ID:  \x1b[0m"
            f"\x1b[35m N/A\n"
            "```"
        )

        log_success = False

        if log_channel:
            try:
                await log_channel.send(log_message)
                log_success = True

            except discord.HTTPException as error:
                print(f"Revocation log error: {error}")

        # Confirmation for the administrator.
        result = (
            f"Successfully revoked bus **{bus_number}**, "
            f"route **{route}**, from **{driver.mention}**.\n"
            f"Spreadsheet columns J and K have been cleared."
        )

        if route_was_found:
            result += (
                f"\nUpdated nickname: **{new_nickname}**"
            )
        else:
            result += (
                "\n⚠️ The route wasn't found in the driver's "
                "nickname, so the nickname was left unchanged."
            )

        if not log_success:
            result += (
                "\n\n⚠️ The assignment log could not be sent. "
                "Check the `#assignment-logs` channel permissions."
            )

        await interaction.followup.send(
            result,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(RevocationCommands(bot))
