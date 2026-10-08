import discord
from discord.ext import tasks
from discord import app_commands
import json
from datetime import datetime
import pytz
import os

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Load JSON
def load_store_data():
    with open("stores.json", "r") as f:
        return json.load(f)

# Sort entries by time
def sort_by_time(entries):
    return sorted(entries, key=lambda e: datetime.strptime(e["time"], "%I:%M %p"))

# Build embed
def build_embed(entries, day):
    embed = discord.Embed(
        title=f"📦 Restock Locations for {day}",
        description="Daily reminder to check possible restocks.",
        color=0x00BFFF
    )

    for e in entries:
        embed.add_field(
            name=f"{e['store']} — {e['time']}",
            value=f"📍 **Location:** {e['location']}\n🔗 [Google Maps]({e['map']})",
            inline=False
        )

    embed.set_footer(text="Restock Reminder Bot • 7AM CST")
    return embed

# Daily reminder
@tasks.loop(minutes=1)
async def daily_reminder():
    cst = pytz.timezone("America/Chicago")
    now = datetime.now(cst)

    if now.hour == 7 and now.minute == 0:
        day = now.strftime("%A")
        data = load_store_data()

        if day in data and len(data[day]) > 0:
            channel = bot.get_channel(CHANNEL_ID)
            entries = sort_by_time(data[day])
            embed = build_embed(entries, day)
            await channel.send(embed=embed)

# /show command
@tree.command(name="show", description="Show today’s restock locations.")
async def show_command(interaction: discord.Interaction):
    cst = pytz.timezone("America/Chicago")
    day = datetime.now(cst).strftime("%A")
    data = load_store_data()

    if day in data and len(data[day]) > 0:
        entries = sort_by_time(data[day])
        embed = build_embed(entries, day)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(
            f"No entries found for **{day}** in stores.json.",
            ephemeral=True
        )

# Modal for /route
class RouteModal(discord.ui.Modal, title="Enter Your Location"):
    location = discord.ui.TextInput(label="Your starting address", placeholder="123 Main St, Kenosha WI")

    async def on_submit(self, interaction: discord.Interaction):
        user_location = str(self.location)

        cst = pytz.timezone("America/Chicago")
        day = datetime.now(cst).strftime("%A")
        data = load_store_data()

        if day not in data or len(data[day]) == 0:
            await interaction.response.send_message(
                f"No entries found for **{day}** in stores.json.",
                ephemeral=True
            )
            return

        entries = sort_by_time(data[day])

        # Build Google Maps multi-stop route
        stops = [user_location.replace(" ", "+")]
        for e in entries:
            stops.append(e["location"].replace(" ", "+"))

        maps_url = "https://www.google.com/maps/dir/" + "/".join(stops)

        # Build embed listing stops
        embed = discord.Embed(
            title=f"🗺️ Route for {day}",
            description=f"Starting from: **{user_location}**\n\n[Open Route in Google Maps]({maps_url})",
            color=0x00BFFF
        )

        for i, e in enumerate(entries, start=1):
            embed.add_field(
                name=f"Stop {i}: {e['store']} — {e['time']}",
                value=f"📍 {e['location']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

# /route command
@tree.command(name="route", description="Generate a multi-stop route for today’s restocks.")
async def route_command(interaction: discord.Interaction):
    await interaction.response.send_modal(RouteModal())

# Ready event
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await tree.sync()  # Register slash commands globally
    daily_reminder.start()

bot.run(TOKEN)
