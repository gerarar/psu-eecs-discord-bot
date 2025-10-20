import discord
from discord.ext import commands
import time
import os
import datetime
import asyncio
import mysqlConnection_local as sql # mysql file
import traceback
import pytz
from dotenv import load_dotenv

load_dotenv() # adds environment variables to current environment

"""
	This cog is for commands dealing with logging
"""
class Logging(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.on_ready_status = True

		self.log_channel_id = int(os.getenv("LOG_CHANNEL"))
		self.auto_delete_commands = ["!LEAVE", "!JOIN", "!ADD"]


	"""
		Helper function to retrieve counting number from db
	"""
	async def get_counting_number(self):
		mydb, my_cursor = sql.connect()
		my_cursor.execute("SELECT * FROM Counting_Channel")
		data = my_cursor.fetchall()
		sql.close(mydb, my_cursor)
		return int(data[0][1]) # return counting number retrieved from db
	
	"""
		Helper function to converts integers to binary representation as str format
	"""
	def int_to_binary(self, number: int):
		return "{0:b}".format(number)

	"""
		>> Helper function to delete a message after buf number of seconds
	"""
	async def delete_message(self, chnl, msg, buf: int = 3):
		try:
			await asyncio.sleep(buf)
			await msg.delete()
		except discord.errors.NotFound:
			pass
		return


	"""
		Helper fuction to udpate the serer stats of number of members, excluding bots, in the server/guild
	"""
	async def update_guild_member_count(self):
		psu_discord = self.bot.get_guild(int(os.getenv("GUILD_ID")))

		f = lambda x : x.bot == False

		members = psu_discord.members
		num_members = list(filter(f, members)) # remove bots from member list/count

		for cat in psu_discord.categories:
			if "server stats" in cat.name.lower():
				await cat.channels[0].delete()

				overwrite = discord.PermissionOverwrite()
				overwrite.connect = False

				perms = {
					psu_discord.default_role: overwrite
				}

				VC = await cat.create_voice_channel(f"Total Members: {len(num_members)}", overwrites=perms)
				break
		print("Edited total member VC")


	"""
		Helper fuction to reorder the class channels by thier respective member counts
	"""
	async def reorder_channels(self):
		BLACKLIST = ["Admin","GiveawayBot","Bots","Mod","dabBot","Simple Poll","Groovy"]
		# @everyone is position 0

		psu_discord = self.bot.get_guild(int(os.getenv("GUILD_ID")))
		raw_roles = psu_discord.roles

		f = lambda r : r.name not in BLACKLIST + ['@everyone']

		roles = list(filter(f, raw_roles))
		roles.sort(key=lambda x: (len(x.members), x.name), reverse=True)

		for index, role in enumerate(roles):
			pos = len(raw_roles)-len(BLACKLIST)-index
			if pos <= 0: pos = 1
			if role.position == pos:
				print("{} already in position {}".format(role.name, pos))
				continue

			print("Set {} to position {}".format(role.name, pos))
			await role.edit(position=pos)
			await asyncio.sleep(1)


	"""
		Listener event for on_member_remove
		>>	called whenever a user leaves the guild/server whether be intentional or a ban
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_member_remove
	"""
	@commands.Cog.listener()
	async def on_member_remove(self, member):
		await self.update_guild_member_count()
		print("{} left the server".format(member.name))
		await self.reorder_channels()

		await self.bot.get_channel(int(os.getenv("LOG_CHANNEL"))).send("{} left the server 🙁.".format(member.name))
		est = pytz.timezone('US/Eastern')

		possessed_roles = ", ".join([r.name for r in member.roles])

		em = discord.Embed(color=0xA30000, timestamp=datetime.datetime.now())

		joined_date = member.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')
		em.add_field(name="Member left or was kicked from the server", 
			value=f"► Name: `{member.name}#{member.discriminator}` {member.mention} [{member.id}]\n► Joined Server On: **{joined_date}**\n► Roles: `{possessed_roles}`", 
			inline=False)
		em.set_author(name = member.name, icon_url = member.avatar.url)
		
		staff_log_channel = self.bot.get_channel(self.log_channel_id)
		await staff_log_channel.send(embed=em)


	"""
		Listener event for on_member_join
		>>	called whenever a user joins the guild/server
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_member_join
	"""
	@commands.Cog.listener()
	async def on_member_join(self, member):
		await self.update_guild_member_count()
		print("{} joined the server".format(member.name))

		try:
			await member.send("Welcome to the Penn State CS/CE/EE Server!\nHead on over to <#{}}> to join one of the classes listed there.\nIf a certain class isn't listed there, you can create a group chat for that certain class by doing `!create` in <#{}> to get started.".format(os.getenv("CLASS_SUB_CHANNEL"), os.getenv("BOT_CHANNEL")))
			print("DM'd {}".format(member.name))
		except Exception:
			print("Could not DM {}".format(member.name))

		est = pytz.timezone('US/Eastern')
		em = discord.Embed(color=0xA30000, timestamp=datetime.datetime.now())

		joined_date = member.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')
		create_date = member.created_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')

		em.add_field(name="Member joined the server", 
			value=f"► Name: `{member.name}#{member.discriminator}` {member.mention} [{member.id}]\n► Joined Server On: **{joined_date}**\n► Created Account On: **{create_date}**", 
			inline=False)
		em.set_author(name = member.name, icon_url = member.avatar.url)
		
		staff_log_channel = self.bot.get_channel(self.log_channel_id)
		await staff_log_channel.send(embed=em)


	"""
		Listener event for on_message_delete
		>>	called whenever a message is deleted
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message_delete
	"""
	@commands.Cog.listener()
	async def on_message_delete(self, msg):

		# Check if message is not from bot and not a command 
		if msg.author.id != self.bot.user.id and not any(msg.content.upper().startswith(s.upper()) for s in self.auto_delete_commands):
			est = pytz.timezone('US/Eastern')
			joined_date = msg.author.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')

			em = discord.Embed( 
				description=f"► Name: `{msg.author.name}#{msg.author.discriminator}` {msg.author.mention} [{msg.author.id}]\n► Joined Server On: **{joined_date}**\n► Message ID: {msg.id}", 
				color=0xFF8B00, timestamp=datetime.datetime.now())

			em.set_author(name = f"Message by {msg.author.name}#{msg.author.discriminator} deleted in #{msg.channel.name}", icon_url = msg.author.avatar.url)
			em.add_field(name="Message Content", value=msg.content, inline=False)
			
			staff_log_channel = self.bot.get_channel(self.log_channel_id)
			await staff_log_channel.send(embed=em)

			counting_number = await self.get_counting_number()
			# Counting channel check
			if msg.channel.id == int(os.getenv("COUNTING_CHANNEL")):
				counting_number = await self.get_counting_number()
				print(msg.content, self.int_to_binary(counting_number))

				if self.int_to_binary(counting_number) in msg.content:
					if self.int_to_binary(counting_number) not in after.content.split(" "):
						await msg.channel.send("Current number was deleted.\n")
						await msg.channel.send(self.int_to_binary(counting_number))


	"""
		Listener event for on_raw_message_delete
		>>	called whenever an uncached message is deleted
		>>	a message is uncached is when a message is older than the bot's uptime
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_raw_message_delete
	"""
	@commands.Cog.listener()
	async def on_raw_message_delete(self, payload):

		# Check if message is uncached
		if payload.cached_message == "" or payload.cached_message == None:
			est = pytz.timezone('US/Eastern')
			em = discord.Embed( 
				description=f"► Message ID: {payload.message_id}", 
				color=0xFF8B00, timestamp=datetime.datetime.now())

			try:
				em.set_author(name = f"Uncached Message deleted in #{self.bot.get_channel(payload.channel_id).name}")
			except TypeError:
				return
			
			staff_log_channel = self.bot.get_channel(self.log_channel_id)
			await staff_log_channel.send(embed=em)	


	"""
		Listener event for on_message_edit
		>>	called whenever a message is edited
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message_edit
	"""
	@commands.Cog.listener()
	async def on_message_edit(self, before, after):
		if before.author.id != self.bot.user.id:
			est = pytz.timezone('US/Eastern')
			joined_date = before.author.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')

			em = discord.Embed( 
				description=f"► Name: `{before.author.name}#{before.author.discriminator}` {before.author.mention} [{before.author.id}]\n► Joined Server On: **{joined_date}**\n► Message ID: {before.id}", 
				color=0x0076FA, timestamp=datetime.datetime.now())

			em.set_author(name = f"Message in #{before.channel.name} edited by {before.author.name}#{before.author.discriminator}", icon_url = before.author.avatar.url)
			em.add_field(name="Original Content", value=before.content, inline=True)
			em.add_field(name="New Content", value=after.content, inline=True)

			staff_log_channel = self.bot.get_channel(self.log_channel_id)
			await staff_log_channel.send(embed=em)

		# Counting channel check
		if before.channel.id == int(os.getenv("COUNTING_CHANNEL")):
			l_msg = [message async for message in await before.channel.history(limit=1)]
			print(before.id, l_msg[0].id)
			if before.id == l_msg[0].id:
				counting_number = await self.get_counting_number()
				if self.int_to_binary(counting_number) not in after.content.split(" "):
					await before.channel.send("Current number was edited.\n")
					await before.channel.send(self.int_to_binary(counting_number))


	"""
		Listener event for on_member_update
		>>	called whenever a member updates their profile
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_member_update
	"""
	@commands.Cog.listener()
	async def on_member_update(self, before: discord.Member, after: discord.Member):
		if before.nick != after.nick:
			est = pytz.timezone('US/Eastern')
			joined_date = before.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')

			em = discord.Embed( 
				description=f"► Name: `{before.name}#{before.discriminator}` {before.mention} [{before.id}]\n► Joined Server On: **{joined_date}**", 
				color=0xFFF25A, timestamp=datetime.datetime.now())

			em.set_author(name = f"{before.name}#{before.discriminator}'s nickname was changed", icon_url = before.avatar.url)
			em.add_field(name="Original Nickname", value=before.nick, inline=True)
			em.add_field(name="New Nickname", value=after.nick, inline=True)

			staff_log_channel = self.bot.get_channel(self.log_channel_id)
			await staff_log_channel.send(embed=em)

	@commands.Cog.listener()
	async def on_presence_update(self, before: discord.Member, after: discord.Member):
		if before.status != after.status:
			est = pytz.timezone('US/Eastern')
			joined_date = before.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p')

			em = discord.Embed( 
				description=f"► Name: `{before.name}#{before.discriminator}` {before.mention} [{before.id}]\n► Joined Server On: **{joined_date}**", 
				color=0xFFF25A, timestamp=datetime.datetime.now())

			em.set_author(name = f"{before.name}#{before.discriminator}'s status was changed", icon_url = before.avatar.url)
			em.add_field(name="Original Status", value=str(before.status), inline=True)
			em.add_field(name="New Status", value=str(after.status), inline=True)

			staff_log_channel = self.bot.get_channel(self.log_channel_id)
			await staff_log_channel.send(embed=em)


async def setup(bot):
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
		An extension must have a global function, setup 
			defined as the entry point on what to do when 
			the extension is loaded. 
		This entry point must have a single argument, the bot.
	"""
	await bot.add_cog(Logging(bot)) # add cog/Class by passing in instance