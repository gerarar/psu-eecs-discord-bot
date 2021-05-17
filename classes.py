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


class Classes(commands.Cog):
	"""
		This cog is for commands dealing with classes
	"""

	@commands.command(aliases=["hi"]) 
	async def hello(self, ctx):
		await ctx.send(f'Hello {ctx.author.name}.')


def setup(bot):
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
		An extension must have a global function, setup 
			defined as the entry point on what to do when 
			the extension is loaded. 
		This entry point must have a single argument, the bot.
	"""
	bot.add_cog(Classes(bot)) # add cog/Class by passing in instance