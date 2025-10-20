import discord
from discord.ext import commands
import time
import os
import sys
import datetime
import asyncio
import random
import mysql.connector
import inspect
import traceback
import pytz
import threading
from dotenv import load_dotenv

load_dotenv() # adds environment variables to current environment (like bot key)
# bot = commands.Bot(command_prefix="!")


class PSU_Bot(commands.Bot): # inherits discord.commands class
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#discord.ext.commands.Bot
		self is commands.Bot type 
	"""
	def __init__(self):  
		super().__init__(command_prefix="!", intents=discord.Intents.all())
		self.token = os.getenv("BOT_KEY")

	async def setup_hook(self):
		# load cogs
		print("Loading extensions...")
		await self.load_extension("cogs.classes")		# loads Classes extension containing classes-related commands
		await self.load_extension("cogs.counting")		# loads Classes extension containing counting-related commands
		await self.load_extension("cogs.logging")		# loads Classes extension containing logging-related functions
		await self.load_extension("cogs.background")	# loads Classes extension containing background related tasks
		print("DONE LOADING EXTENSIONS")

	"""
		Function runs once bot is connected to discord API
	"""
	async def on_ready(self):
		print("PSU Bot V2 Connected!")
		print(f"Logged in as {self.user.name}:{self.user.id}")
		# print(vars(self))
		try:
			await self.get_channel(int(os.getenv("STARTUP_CHANNEL"))).send("PSU EECS bot online!")
		except AttributeError:
			pass
		self.print_commands()

	"""
		Helper function to print all commands currently available 
	"""
	def print_commands(self):
		for cog_name in self.cogs:
			cog = self.get_cog(cog_name)
			comms = cog.get_commands()
			print(f"{cog_name} commands: {[c.name for c in comms]}")

	"""
		Runs bot and connects to discord API
	"""
	def run(self):	# runs bot given token, must be last func in class
		super().run(self.token, reconnect=True)


if __name__ == "__main__":
	psu_bot = PSU_Bot()
	psu_bot.run()	# run bot

