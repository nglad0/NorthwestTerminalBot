# setstatus.py

import discord
from discord import app_commands
from discord.ext import commands


ALLOWED_ROLES = {
    "Transportation Supervisor",
    "Transportation Director",
}


@app_commands.command(
    name="setstatus",
    description="Change the bot's Discord status and activity."
)
@app_commands.describe(
    status="The bot's online status.",
    activity_type="What the bot should display as doing.",
    activity_text="The text displayed alongside the activity."
)
@app_commands.choices(
    status=[
        app_commands.Choice(name="Online", value="online"),
        app_commands.Choice(name="Idle", value="idle"),
        app_commands.Choice(name="Do Not Disturb", value="dnd"),
        app_commands.Choice(name="Invisible", value="invisible"),
    ],
    activity_type=[
        app_commands.Choice(name="Playing", value="playing"),
        app_commands.Choice(name="Watching", value="watching"),
        app_commands.Choice(name="Listening to", value="listening"),
        app_commands.Choice(name="Competing in", value="competing"),
        app_commands.Choice(name="Clear activity", value="none"),
    ],
)
async def setstatus(
    interaction: discord.Interaction,
    status: app_commands.Choice[str],
    activity_type: app_commands.Choice[str],
    activity_text: str = None,
):
    # Check staff permissions
    if not isinstance(interaction.user, discord.Member) or not any(
        role.name in ALLOWED_ROLES
        for role in interaction.user.roles
    ):
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True
        )
        return

    # Prepare online status
    status_options = {
        "online": discord.Status.online,
        "idle": discord.Status.idle,
        "dnd": discord.Status.dnd,
        "invisible": discord.Status.invisible,
    }

    # Prepare activity
    activity_options = {
        "playing": discord.ActivityType.playing,
        "watching": discord.ActivityType.watching,
        "listening": discord.ActivityType.listening,
        "competing": discord.ActivityType.competing,
    }

    if activity_type.value == "none":
        activity = None

    else:
        if not activity_text or not activity_text.strip():
            await interaction.response.send_message(
                "Please provide text for the bot's activity.",
                ephemeral=True
            )
            return

        activity = discord.Activity(
            type=activity_options[activity_type.value],
            name=activity_text.strip()
        )

    try:
        await interaction.client.change_presence(
            status=status_options[status.value],
            activity=activity
        )

        activity_description = (
            "No activity"
            if activity is None
            else f"{activity_type.name} {activity_text.strip()}"
        )

        await interaction.response.send_message(
            f"Successfully updated the bot's presence!\n"
            f"**Status:** {status.name}\n"
            f"**Activity:** {activity_description}",
            ephemeral=True
        )

    except discord.HTTPException:
        await interaction.response.send_message(
            "Discord could not update the bot's presence. Please try again.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    bot.tree.add_command(setstatus)
