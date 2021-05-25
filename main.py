import discord
from discord.ext import commands
import time
import os
import sys
import datetime
import asyncio
import random
import mysql.connector
import datetime
import inspect
# import mysqlConnection_local as sql # mysql file
import traceback
import pytz
import threading
from dotenv import load_dotenv

load_dotenv() # adds environment variables to current environment (like bot key)
bot = commands.Bot(command_prefix="!")

class PSU_Bot(commands.Bot): # inherits discord.commands class
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/api.html#discord.ext.commands.Bot
		self is commands.Bot type 
	"""
	def __init__(self):  
		super().__init__(command_prefix="!", intents=discord.Intents.all())
		self.token = os.getenv("BOT_KEY")
		# self.load_extension("cogs.classes")	# loads Classes extension containing classes-related commands
		self.load_extension("cogs.counting")	# loads Classes extension containing classes-related commands
		# print(vars(self))
		

	"""
		Function runs once bot is connected to discord API
	"""
	async def on_ready(self):
		print("PSU Bot V2 Connected!")
		print(f"Logged in as {self.user.name}:{self.user.id}")
		# print(vars(self))
		try:
			await self.get_channel(795781887603114034).send("PSU EECS bot online!")
		except AttributeError:
			pass
		self.print_commands()

	"""
		Helper function to print all commands currently available 
	"""
	def print_commands(self):
		cog = self.get_cog('Classes')
		comms = cog.get_commands()
		print(f"Classes commands: {[c.name for c in comms]}")

	"""
		Runs bot and connects to discord API
	"""
	def run(self):	# runs bot given token, must be last func in class
		super().run(self.token, reconnect=True)


if __name__ == "__main__":
	psu_bot = PSU_Bot()
	psu_bot.run()	# run bot

