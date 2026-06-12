"""
oak_discord.py
OAK — Morgan Heights Studio Discord Bot
Run with: python3 oak_discord.py
Requires: pip install discord.py anthropic requests
"""

import discord
import anthropic
import requests
import json
import os
from datetime import datetime, timezone

# ── Config — set these as environment variables in Railway ────
DISCORD_TOKEN    = os.getenv('DISCORD_TOKEN')
ANTHROPIC_KEY    = os.getenv('ANTHROPIC_KEY')
GCAL_KEY         = os.getenv('GCAL_KEY', '')
GCAL_ID          = os.getenv('GCAL_ID', '13869b11c3943cceb3751f411b4907b14c9e02b3df051317896133346f9b5e3d@group.calendar.google.com')
GENERAL_CHANNEL  = int(os.getenv('GENERAL_CHANNEL', '1515091256378921163'))
BOT_NAME         = 'OAK'

# ── Anthropic client ──────────────────────────────────────────
ai = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ── OAK system prompt ─────────────────────────────────────────
OAK_SYSTEM = """You are OAK, the Morgan Heights Studio Discord bot.

Think Randy from Tracker — deadpan, competent, slightly nerdy, dry humor, loyal to the studio, not trying to be cool. That's the energy.

STUDIO CONTEXT:
Morgan Heights Studio is a solo indie operation in San Antonio, TX. One developer — Lone Star Tsalagi (Sèitheach Wilson). Army vet (10th Mountain, SPARTANS, OEF), white-hat hacker background, Cherokee/Patawomeck heritage, runs a six-country nonprofit. Started gaming on Atari, all-time favorite games are Xenosaga 1-3. Programs because he loves it.

Current game: The Shattered Coast: Oakhaven — AI dungeon master RPG, currently in ALPHA. Not finished. Active development.

YOUR DISCORD PERSONALITY:
- Match the user's register. Casual gets casual. Technical gets technical. Pissed gets calm and useful.
- Zero filler. 'Great question!', 'I'd be happy to help!' — banned.
- Dry wit when it fits. Not your default.
- You can have opinions. Generic neutrality is not the vibe.
- Keep Discord responses concise — this isn't a blog post.
- Never claim to be the developer. You're OAK.
- If you don't know something, say so directly.
- You are not trying to be cool. That's exactly what makes you work."""

# ── Get calendar events ───────────────────────────────────────
def get_calendar_events():
    if 'YOUR' in GCAL_KEY:
        return []
    try:
        now = datetime.now(timezone.utc).isoformat()
        url = (f'https://www.googleapis.com/calendar/v3/calendars/'
               f'{requests.utils.quote(GCAL_ID)}/events'
               f'?key={GCAL_KEY}'
               f'&timeMin={requests.utils.quote(now)}'
               f'&timeMax={requests.utils.quote(now[:10])}T23:59:59Z'
               f'&orderBy=startTime&singleEvents=true&maxResults=5')
        r = requests.get(url, timeout=8)
        data = r.json()
        return data.get('items', [])
    except Exception:
        return []

# ── Generate OAK response ─────────────────────────────────────
def oak_reply(message_content: str, author_name: str, is_dev: bool = False) -> str:
    dev_note = ' This is the studio dev — talk to them as a peer, drop the support register.' if is_dev else ''
    try:
        resp = ai.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=300,
            system=OAK_SYSTEM + dev_note,
            messages=[{'role': 'user', 'content': f'{author_name}: {message_content}'}]
        )
        return resp.content[0].text
    except Exception as e:
        return f"Something broke on my end. ({e})"

# ── Generate calendar event post ──────────────────────────────
def oak_event_post(title: str, date_str: str, description: str = '') -> str:
    desc_line = f'Event details: {description}' if description else ''
    prompt = f"""You are OAK posting a studio event update to the Morgan Heights Studio Discord server.

Event: {title}
Date/Time: {date_str}
{desc_line}

CRITICAL: Use the exact time and details from the event. Do not invent anything.
- Short and punchy — Discord, not Facebook
- OAK energy — dry, real, gamer-professional
- Under 100 words
- Sign off as — OAK 🎮

Raw text only."""
    try:
        resp = ai.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return resp.content[0].text
    except Exception:
        return ''

# ── Discord client ────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'OAK online as {client.user}')
    channel = client.get_channel(GENERAL_CHANNEL)
    if channel:
        # Check for today's events on startup
        events = get_calendar_events()
        for event in events:
            title    = event.get('summary', 'Studio Event')
            desc     = event.get('description', '')
            start    = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date', '')
            date_str = datetime.fromisoformat(start.replace('Z', '+00:00')).strftime('%b %-d at %-I:%M%p') if start else 'TBD'
            post     = oak_event_post(title, date_str, desc)
            if post:
                await channel.send(post)

@client.event
async def on_message(message):
    # Ignore own messages
    if message.author == client.user:
        return

    # Only respond in general channel
    if message.channel.id != GENERAL_CHANNEL:
        return

    # Respond if OAK is mentioned or message starts with !oak
    content = message.content.strip()
    mentioned = client.user in message.mentions
    commanded = content.lower().startswith('!oak')

    if not mentioned and not commanded:
        return

    # Clean the message
    clean = content.replace(f'<@{client.user.id}>', '').replace('!oak', '').strip()
    if not clean:
        clean = 'hey'

    # Check if dev (you can add your Discord user ID here)
    is_dev = str(message.author.id) in ['YOUR_DISCORD_USER_ID']

    async with message.channel.typing():
        reply = oak_reply(clean, message.author.display_name, is_dev)
        await message.reply(reply)

# ── Run ───────────────────────────────────────────────────────
client.run(DISCORD_TOKEN)
