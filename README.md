<div align="center">

# 📊 ServerStats

**Real-Time Server Analytics & Activity Insights for Discord**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-v2.0+-5865F2.svg)](https://github.com/Rapptz/discord.py)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Track member engagement, voice activity, and moderation team performance effortlessly.

[Features](#-features) • [Commands](#-commands) • [Installation](#-installation) • [Author](#-author)

</div>


## ✨ Features

- 📈 **Live Analytics:** Track community growth, active members, and engagement trends in real time.
- 🎙️ **Voice & Text Metrics:** Measure time spent in voice channels and message activity across text channels.
- 🛡️ **Staff Performance:** Gain insight into moderator activity, response frequency, and staff stats.
- 📑 **Automated Reports:** Run `/report` to generate instant, easy-to-read weekly activity summaries.


## 🛠️ Commands

| Command | Description |
| :--- | :--- |
| `/report` | Generates a comprehensive weekly server engagement report. |
| `/stats` | Shows live metrics for chat activity, voice channels, and member growth. |
| `/staff_stats` | Displays performance & moderation statistics for staff members. |


## ⚙️ Setup & Installation

### 1️⃣ Clone the Repository
```bash
git clone [https://github.com/bikiogirl/ServerStats.git](https://github.com/bikiogirl/ServerStats.git)
cd ServerStats

2️⃣ Install Dependencies
Bash
pip install -r requirements.txt

3️⃣ Configure Environment Variables
Create a .env file based on .env.example:
Code snippet
DISCORD_TOKEN=your_discord_bot_token_here

4️⃣ Start the Bot
Bash
python bot.py
