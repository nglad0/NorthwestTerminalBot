# bot.py

import discord
from discord import app_commands
from discord.ext import commands

from config import DISCORD_TOKEN


# Discord bot permissions and intents
intents = discord.Intents.default()
intents.members = True


# Create the bot
class NWTRosterBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await self.load_extension("commands.assignbus")
        await self.load_extension("commands.revokebus")
        await self.load_extension("commands.setstatus")
        
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")


bot = NWTRosterBot()


@bot.event
async def on_ready():
    print("--------------------------------")
    print(f"Bot online: {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    print("Northwest Terminal Support Bot is ready!")
    print("--------------------------------")


@bot.tree.command(
    name="ping",
    description="Check whether the bot is responding."
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Pong! Northwest Terminal Support Bot is online.",
        ephemeral=True
    )


# Start the bot
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is missing from your .env file!")

bot.run(DISCORD_TOKEN)
