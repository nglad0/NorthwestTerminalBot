# Northwest Terminal

**Northwest Terminal Transportation — Discord Support Bot**

Northwest Terminal is a Discord bot developed for the Northwest Terminal Transportation community, a Roblox school transportation simulation group.

The bot provides administrative tools for managing vehicle assignments, driver information, and transportation operations.

## Features

### Vehicle Management
- **`/assignbus`** — Assigns a bus to a Discord member.
- **`/revokebus`** — Revokes an existing bus assignment.
- Automatically updates driver nicknames with assigned route numbers.
- Maintains driver assignment information in Google Sheets.

### Roblox Integration
- Uses Bloxlink to retrieve Roblox account information associated with Discord members.
- Supports Roblox ID lookups for driver records.

### Administrative Logging
- Records vehicle assignment changes.
- Sends assignment logs to the designated assignment-logs channel.
- Restricts vehicle management commands to authorized transportation staff.

## Technology

- Python
- discord.py
- Google Sheets API
- Bloxlink API
- Flask

## Project Structure

NorthwestTerminalBot/
├── commands/
│   ├── assignbus.py
│   └── revokebus.py
├── database/
│   └── sheets.py
├── utils/
│   └── bloxlink.py
├── docs/
│   └── Website files
├── bot.py
├── config.py
├── webserver.py
├── requirements.txt
└── README.md

## Configuration

The bot uses environment variables and a Google service account to connect to external services.

Required configuration includes:
- Discord bot token
- Google Sheets credentials and spreadsheet configuration
- Bloxlink API key
- Discord server ID

**Important:** Private credentials and configuration files must never be committed to the public repository.

## Hosting

- **Discord Bot:** Bot-Hosting.net
- **Website:** GitHub Pages

## Project Information

Developed for the Northwest Terminal Transportation community.

*Northwest Terminal — Transportation Operations & Support.*
-nglad_08 11/05/2026 5:25 PM