# assignbus.py

import asyncio
import re

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_GUILD_ID
from database.sheets import get_worksheet
from utils.bloxlink import get_roblox_id


LOG_CHANNEL_NAME = "assignment-logs"

ALLOWED_ROLES = (
    "Transportation Supervisor",
    "Transportation Director",
)


def get_driver_name(nickname: str) -> str:
    """Remove the trailing route section from a nickname."""
    return re.sub(r"\s*⌞[^⌝]*⌝\s*$", "", nickname).strip()


def get_updated_nickname(nickname: str, route: str) -> str:
    """Add a route while preserving existing route assignments."""

    base_name = get_driver_name(nickname)

    match = re.search(r"⌞(.*?)⌝\s*$", nickname)

    routes = []

    if match:
        routes = [
            item.strip()
            for item in match.group(1).split("|")
            if item.strip()
        ]

    if route not in routes:
        routes.append(route)

    return f"{base_name} ⌞{' | '.join(routes)}⌝"


def update_spreadsheet(bus_number, roblox_id, driver_name):
    """Find the bus in column C and update columns J and K."""

    worksheet = get_worksheet()

    bus_numbers = worksheet.col_values(3)

    matching_rows = [
        row_number
        for row_number, value in enumerate(bus_numbers, start=1)
        if value.strip().casefold() == bus_number.strip().casefold()
    ]

    if not matching_rows:
        raise ValueError(
            f"Bus {bus_number} was not found in spreadsheet column C."
        )

    if len(matching_rows) > 1:
        raise ValueError(
            f"Bus {bus_number} appears more than once in column C."
        )

    row = matching_rows[0]

    route = worksheet.cell(row, 9).value

    if not route or not route.strip():
        raise ValueError(
            f"Bus {bus_number} does not have a route in column I."
        )

    existing_roblox_id = worksheet.cell(row, 10).value

    # Update J and K together.
    worksheet.batch_update([
        {
            "range": f"J{row}:K{row}",
            "values": [[
                roblox_id if roblox_id is not None else (
                    existing_roblox_id or ""
                ),
                driver_name,
            ]],
        }
    ])

    return route.strip()


class AssignmentCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="assignbus",
        description="Assign a driver to a bus."
    )
    @app_commands.describe(
        user="The Discord member receiving the assignment.",
        bus_number="The bus number being assigned."
    )
    @app_commands.guild_only()
    @app_commands.checks.has_any_role(*ALLOWED_ROLES)
    async def assignbus(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        bus_number: str,
    ):

        await interaction.response.defer(ephemeral=True)

        # Find the bus and its route.
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

            if not route or not route.strip():
                await interaction.followup.send(
                    f"Bus `{bus_number}` has no route assigned "
                    "in column I.",
                    ephemeral=True
                )
                return

            route = route.strip()

        except Exception as error:
            print(f"Spreadsheet lookup error: {error}")

            await interaction.followup.send(
                "I couldn't look up that bus in Google Sheets.",
                ephemeral=True
            )
            return

        # Get the driver's Roblox ID through Bloxlink.
        roblox_id, bloxlink_status = await asyncio.to_thread(
            get_roblox_id, user.id
        )

        # Prepare the new nickname.
        old_nickname = user.nick
        current_nickname = user.display_name

        driver_name = get_driver_name(current_nickname)

        new_nickname = get_updated_nickname(
            current_nickname,
            route
        )

        if len(new_nickname) > 32:
            await interaction.followup.send(
                "The updated nickname would exceed Discord's "
                "32-character nickname limit. Shorten the "
                "driver's current nickname first.",
                ephemeral=True
            )
            return

        # Change the Discord nickname.
        try:
            await user.edit(
                nick=new_nickname,
                reason=(
                    f"Bus {bus_number} / Route {route} "
                    f"assigned by {interaction.user}"
                )
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "I couldn't change that member's nickname. "
                "Check my Manage Nicknames permission and role "
                "hierarchy.",
                ephemeral=True
            )
            return

        except discord.HTTPException as error:
            await interaction.followup.send(
                f"Discord rejected the nickname change: {error}",
                ephemeral=True
            )
            return

        # Update the spreadsheet.
        try:
            worksheet = await asyncio.to_thread(get_worksheet)

            existing_roblox_id = await asyncio.to_thread(
                lambda: worksheet.cell(row, 10).value
            )

            # If Bloxlink returns an error, preserve the existing ID.
            spreadsheet_roblox_id = (
                roblox_id
                if bloxlink_status == "found"
                else (
                    ""
                    if bloxlink_status == "not_linked"
                    else existing_roblox_id or ""
                )
            )

            await asyncio.to_thread(
                worksheet.batch_update,
                [
                    {
                        "range": f"J{row}:K{row}",
                        "values": [[
                            spreadsheet_roblox_id,
                            driver_name,
                        ]],
                    }
                ]
            )

        except Exception as error:
            print(f"Spreadsheet update error: {error}")

            # Attempt to restore the original nickname.
            try:
                await user.edit(
                    nick=old_nickname,
                    reason="Rolling back failed bus assignment"
                )
            except discord.HTTPException:
                pass

            await interaction.followup.send(
                "The spreadsheet update failed. I attempted to "
                "restore the member's previous nickname. "
                "Please check the spreadsheet before retrying.",
                ephemeral=True
            )
            return

        # Find the assignment log channel.
        log_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=LOG_CHANNEL_NAME
        )

        # Format the assignment log.
        admin_name = interaction.user.display_name.upper()
        driver_name_upper = driver_name.upper()

        driver_id_text = (
            roblox_id if bloxlink_status == "found"
            else (
                "NOT LINKED"
                if bloxlink_status == "not_linked"
                else "LOOKUP ERROR"
            )
        )

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
            f"\x1b[32m {driver_name_upper}\n"
            f"\x1b[0m\x1b[1mDRIVER ID:  \x1b[0m"
            f"\x1b[35m {driver_id_text}\n"
            "```"
        )

        log_success = False

        if log_channel:
            try:
                await log_channel.send(log_message)
                log_success = True
            except discord.HTTPException as error:
                print(f"Assignment log error: {error}")

        # Build the administrator's confirmation.
        result = (
            f"Successfully assigned **{user.mention}** "
            f"to bus **{bus_number}**, route **{route}**.\n"
            f"New nickname: **{new_nickname}**"
        )

        if bloxlink_status == "not_linked":
            result += (
                "\n\n⚠️ **Warning:** This member has no linked "
                "Roblox account. The assignment was completed, "
                "but column J was left blank."
            )

        elif bloxlink_status == "error":
            result += (
                "\n\n⚠️ **Warning:** Bloxlink lookup failed. "
                "The assignment was completed, but the existing "
                "Roblox ID in column J was preserved."
            )

        if not log_success:
            result += (
                "\n\n⚠️ The assignment log could not be sent. "
                "Check that `#assignment-logs` exists and that "
                "I have permission to send messages there."
            )

        await interaction.followup.send(
            result,
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AssignmentCommands(bot))
