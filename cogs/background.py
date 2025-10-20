import discord
from discord.ext import commands
import time
import os
import sys
import datetime
import asyncio
import mysqlConnection_local as sql # mysql file
import traceback
import pytz
import threading
import string
from dotenv import load_dotenv

load_dotenv() # adds environment variables to current environment

"""
	This cog is for commands dealing with background tasks/processes
"""
class Background(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.on_ready_status = True

		self.log_channel_id = int(os.getenv("LOG_CHANNEL"))
		self.reminders_dict = {
			"Reminders_10Minutes":
				{
					"Warning_Msg": string.Template("***FINAL*** **$class_name HOMEWORK REMINDER:** `$class_obj` is due in less then **10 minutes**!! $class_role_mention")
				},
			"Reminders_3Hours":
				{
					"Warning_Msg": string.Template("**$class_name HOMEWORK REMINDER:** `$class_obj` is due in less then **3 hours**!! $class_role_mention")
				},
			"Reminders_24Hours":
				{
					"Warning_Msg": string.Template("**$class_name HOMEWORK REMINDER:** `$class_obj` is due in less then **3 hours**!! $class_role_mention")
				}
		}
		self.class_sub_channel_id = int(os.getenv("CLASS_SUB_CHANNEL"))
		self.sem = threading.Semaphore(1) # used to prevent background task from restarting before previous one finishes


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
		Background task that runs every 60 seconds
		Checks 3 tables from the database -- Reminders_10Minutes, Reminders_3Hours, Reminders_24Hours
		If any table has info, would output the corresponding message in #class-announcements channel
	"""
	async def reminder_process(self):
		mydb, my_cursor = sql.connect()

		for table, value in self.reminders_dict.items():
			print(f"table: {table}")
			query = f"SELECT * FROM {table} WHERE Datetimestamp < '%s'"
			query = query % datetime.datetime.now()
			my_cursor.execute(query)

			# my_cursor.execute(query, (datetime.datetime.now(),))   # this doesnt work for some reason
			d = my_cursor.fetchall()
			print(f'{table}: {d}')
			
			if len(d) > 0:
				for a in d:
					my_cursor.execute("SELECT Class_role_id FROM Classes WHERE Class_name = %s", (a[1],))
					obj = my_cursor.fetchall()

					data = {
						"class_name": a[1],
						"class_obj": a[3],
						"class_role_mention": {discord.utils.get(self.bot.get_guild(int(os.getenv("GUILD_ID"))).roles, id=int(a[0])).mention}
					}

					# this will sub in data values into the $-placeholders by matching dictionary keys to placeholder names
					m = await self.bot.get_channel(int(os.getenv("CLASS_ANNOUNCEMENTS"))).send(value["Warning_Msg"].substitute(data))

					await m.add_reaction(emoji="🖕")
					my_cursor.execute("DELETE FROM %s WHERE ID = %s", (table, a[0],)) #delete from table
					mydb.commit()

		sql.close(mydb, my_cursor)
		await asyncio.sleep(60)
		self.sem.release()


	"""
		Main function for the background task that runs every 60 seconds
	"""
	async def my_background_task(self):
		await self.bot.wait_until_ready()
		while not self.bot.is_closed():
			self.sem.acquire() 
			try:
				await self.reminder_process()
			except Exception:
				pass


	"""
		Listener event for on_ready
		>>	called when the bot successfully connects to Discord API
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_ready
	"""
	@commands.Cog.listener()
	async def on_ready(self):

		if self.on_ready_status: # this should only run once, especially when the API disconnects and reconnects
			self.on_ready_status = False

			mydb, my_cursor = sql.connect()

			my_cursor.execute("SELECT Class_name FROM Classes ORDER BY Class_name")
			d = my_cursor.fetchall()
			
			arr = []
			for i in d:
				if i[0].split(" ")[0] not in [a[0] for a in arr]: # check if department is accounted for yet
					arr.append([i[0].split(" ")[0], [i[0]]]) # append [dept alias, [class]]
				else:
					for inner in arr:
						if i[0].split(" ")[0] == inner[0]:
							inner_arr = inner[1]
							inner_arr.append(i[0])
							break

			f = lambda x: len(x[1]) # returns length of nested list
			arr.sort(key=f, reverse=True) # sort array by number of classes in each department/field from greatest to smallest

			# await self.bot.get_channel(self.class_sub_channel_id).purge(limit=10)
			
			est = pytz.timezone('US/Eastern')
			em = discord.Embed(description = "**Join a class group chat and receive notifications by invoking one of the following command(s) below**:\n\n",
								color=0x10D600, timestamp=datetime.datetime.now())

			my_cursor.execute("SELECT Department_name, Department_alias FROM Departments")
			d = my_cursor.fetchall()
			# all_dept_names = [b[0] for b in d]

			for field in arr:
				text = ""
				for classs in field[1]:
					text += "{} - `!join {}`\n".format(classs, classs.split(" ")[1]) # join nested array together to string

				for dept in d:
					if field[0] == dept[1]:	
						em.add_field(name="{} | {}".format(dept[0], dept[1]), 
							value=text, inline=True)
						break

			await self.bot.get_channel(self.class_sub_channel_id).send(embed=em)

			await self.update_guild_member_count()
			await self.reorder_channels()

			sql.close(mydb, my_cursor)

			# bot.loop.create_task(await my_background_task())
			# await asyncio.gather(self.my_background_task()) # disabled as of 12.19.2024


async def setup(bot):
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
		An extension must have a global function, setup 
			defined as the entry point on what to do when 
			the extension is loaded. 
		This entry point must have a single argument, the bot.
	"""
	await bot.add_cog(Background(bot)) # add cog/Class by passing in instance