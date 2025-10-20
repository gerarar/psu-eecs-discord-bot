import discord
from discord.ext import commands
import datetime
import asyncio
import random
import datetime
import inspect
import mysqlConnection_local as sql # mysql file
import traceback
import pytz
import os
from dotenv import load_dotenv

load_dotenv() # loads environment variables from .env file

"""
	This cog is for commands dealing with classes
"""
class Classes(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(aliases=["hi"]) 
	async def hello(self, ctx, *args):
		# print(type(content))
		await ctx.send(f'Hello {ctx.author.name}. {args}')

	"""
		Check for commands, given a channel and optional error message
	>>	https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html#checks
	"""
	def is_in_channel(chnl: int, error_msg=None):
		async def predicate(ctx):
			if error_msg != None and not (ctx.channel and ctx.channel.id == chnl):
				await ctx.reply(f"{error_msg} {ctx.author.mention}")
			return ctx.channel and ctx.channel.id == chnl
		return commands.check(predicate)

	"""
		Helper fuction to update the member count for a certain class
	"""
	async def update_class_member_count(self, role: discord.Role, chat_id: int):
		psu_discord = self.bot.get_guild(int(os.getenv("GUILD_ID")))

		cat = self.bot.get_channel(chat_id).category
		members = psu_discord.members

		f = lambda m : role in [r.id for r in m.roles] # checks if class specific role is in member roles
		# print(members)
		
		result = list(filter(f, members))
		num_members = len( result )

		for ch in cat.voice_channels:
			if "registered members" in ch.name.lower():
				await ch.delete()
				break

		overwrite = discord.PermissionOverwrite()
		overwrite.connect = False
		overwrite.view_channel = False

		voice_ch = await psu_discord.create_voice_channel("Registered Members: {}".format(num_members), category=cat)
		await voice_ch.set_permissions(psu_discord.default_role, overwrite=overwrite)
		print("Set {} registered members to {}".format(self.bot.get_channel(chat_id).name, num_members))

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
		!add command
		>>	used to add reminders for a certain class like homework, exams, etc.
	"""
	# @commands.command() # disabled as of 12.19.2024
	async def add(self, ctx, *args):
		# !add hw8
		# cmpsc 465
		# 10/17/19 10pm
		# confirm

		if len(args) > 0:
			assignment_name = " ".join(args)
			overall_status = True
			channel, author = ctx.channel, ctx.author

			def mcheck(msg):
				return msg.author == author and msg.channel == channel
			
			await ctx.reply(f"What class is this for? {author.mention}\nEnter the class name using the following format for example:\n`CMPSC 473` or `CMPEN 331` OR `EE 350` OR `STAT 319`")
			while True:

				reply_msg = await self.bot.wait_for('message', check=mcheck)

				mydb, my_cursor = sql.connect()
				my_cursor.execute("SELECT * FROM Classes WHERE Class_name = '%s'" % (reply_msg.content.upper()))
				d = my_cursor.fetchall()
				sql.close(mydb, my_cursor)
				# d = [("0", "1", "CMPSC 473", "3", "1234", "5", "4321")] # data for debuging locally

				if len(d) > 0:
					class_name = d[0][2]
					class_channel_id = int(d[0][4])
					class_role_id = int(d[0][6])
				elif reply_msg.content.upper() == "CANCEL":
					await reply_msg.reply("Class Reminder session cancelled.")
					break
				else:
					await reply_msg.reply("Error! Can't seem to find the class **{}**.\nPlease double check that you have entered it correctly and re-enter it!".format(reply_msg.content.upper()))
					continue
			
				await reply_msg.reply(f"When is this particular thing due? {author.mention}\nState the date and time like `9/17/2019 10:00pm`")
				while True:

					reply_msg = await self.bot.wait_for('message', check=mcheck)

					addToHour = 0
					content = reply_msg.content.upper()

					if "AM" in content.upper():
						pass
					elif "PM" in content.upper():
						pass
					else:
						await reply_msg.reply("You did not specify `am` or `pm` in your provided time, please try again! %s\nState the date and time like `9/17/2019 10:00pm`" % author.mention)
						continue # go back to start of loop
					
					if True:

						if "PM" in content and "12" not in content.split(" ")[1].split(":")[0]:
							addToHour += 12
							content = content.replace("PM", "")
						content = content.replace("AM", "")
						content = content.replace("PM", "")

						try:
							time_lst = content.split(" ")
							timesplit = time_lst[1].split(":")
							
							hour = int(timesplit[0]) + addToHour
							if hour > 23:
								hour -= 24 #so hour is 23 or less
							try:
								minute = timesplit[1]
							except IndexError:
								minute = 0
							# time = estTime.replace(hour=int(hour),minute=int(minute),second=0,microsecond=0)
						except ValueError:
							await reply_msg.reply("You've entered a time that doesn't exist, please try again! 1%s\nState the date and time like `9/17/2019 10:00pm`" % author.mention)
							continue
						except IndexError:
							minute = 0
							if checkFloat(hour) and checkFloat(minute):
								await reply_msg.reply("This is not a valid date and time, please try again!2 %s\nState the date and time like `9/17/2019 10:00pm`" % author.mention)
								continue
								# return str(int(hour)), minute
							else:
								await reply_msg.reply("This is not a valid date and time, please try again!3 %s\nState the date and time like `9/17/2019 10:00pm`" % author.mention)
								continue

						print(hour, minute, addToHour)

					try:
						date = content.split(" ")[0]
						month = date.split("/")[0]
						day = date.split("/")[1]
						try:
							year = int(date.split("/")[2])
							if year < 2000:
								year += 2000
						except IndexError:
							year = datetime.datetime.today().year

					except Exception:
						await reply_msg.reply("This is not a valid date and time, please try again!4 %s\nState the date and time like `9/17/2019 10:00pm`" % author.mention)
						continue


					try:
						est = pytz.timezone('US/Eastern')
						estTime = datetime.datetime.now().astimezone(est) # set base time as etc time object
						expire = estTime.replace(month=int(month),day=int(day),year=int(year),hour=int(hour),minute=int(minute))
						# expire = expire + datetime.timedelta(hours=4) #eastern to utc is 4hr difference 
						print("prev expire:", expire)
						tz = pytz.timezone('UTC')
						expire = expire.astimezone(tz) # convert expire time to UTC to store into db
						print("new expire:", expire)
						
					except Exception:
						await reply_msg.reply("Something went wrong!\n\n%s\n\nExiting." % traceback.format_exc())
						break

					await reply_msg.reply(f"Send `confirm` to add `{assignment_name}` for `{class_name}`, due on `{month}/{day}/{year}` at `{hour}:{minute}`. {author.mention}\n`cancel` to cancel this session.")

					reply_msg = await self.bot.wait_for('message', check=mcheck)
					if reply_msg.content.upper() == "CONFIRM":

						if (divmod((expire-datetime.datetime.now(datetime.timezone.utc)).total_seconds(), 3600)[0] >= 24):
							expire_24 = expire - datetime.timedelta(hours=24)
							print("created a 24 timestamp")
							
							mydb, my_cursor = sql.connect()
							my_cursor.execute("INSERT INTO Reminders_24Hours(Class_name, Class_channel_id, Description, Datetimestamp) VALUES (%s, %s, %s, %s)",
								(class_name, class_channel_id, assignment_name, expire_24))
							mydb.commit()
							sql.close(mydb, my_cursor)

						if (divmod((expire-datetime.datetime.now(datetime.timezone.utc)).total_seconds(), 3600)[0] >= 3):
							expire_3 = expire - datetime.timedelta(hours=3)
							print("created a 3 timestamp")

							
							mydb, my_cursor = sql.connect()
							my_cursor.execute("INSERT INTO Reminders_3Hours(Class_name, Class_channel_id, Description, Datetimestamp) VALUES (%s, %s, %s, %s)",
								(class_name, class_channel_id, assignment_name, expire_3))
							mydb.commit()
							sql.close(mydb, my_cursor)

						if (divmod((expire-datetime.datetime.now(datetime.timezone.utc)).total_seconds(), 60)[0] >= 10):
							expire_10 = expire - datetime.timedelta(minutes=10)
							print("created a 10min timestamp")


							mydb, my_cursor = sql.connect()
							my_cursor.execute("INSERT INTO Reminders_10Minutes(Class_name, Class_channel_id, Description, Datetimestamp) VALUES (%s, %s, %s, %s)",
								(class_name, class_channel_id, assignment_name, expire_10))
							mydb.commit()
							sql.close(mydb, my_cursor)

						sql.close(mydb, my_cursor)
						await reply_msg.reply("Successfully added class reminder.")
						await self.bot.get_channel(class_channel_id).send(f"Added **{assignment_name}** to **{class_name}** class reminders.\nDue on `{month}/{day}/{year}` at `{hour}:{minute}`.")
						break
					else:
						sql.close(mydb, my_cursor)
						await reply_msg.reply("Cancelled session.")
						break
				break
		else:
			await ctx.reply("To add a class reminder, the syntax of the command is `!add <assignment_name>`\nJust replace `<assignment_name>` with the name of the reminder you want to set!")

	"""
		!create command
		>>	used to create classes, which then sub-creates a group chat channel, resources channel, voice channel, and class role
	"""
	@commands.command()
	async def create(self, ctx, *args):
		channel, author = ctx.channel, ctx.author

		def mcheck(msg):
			return msg.author == author and msg.channel == channel

		def cancel(m):
			if m.upper() == "CANCEL":
				return True
			else: False

		while True:
			create_class_embed = (discord.Embed(title = "Please enter the alias of the class you want to create, for example: `CMPSC 465`", color=random.randint(111111, 999999), timestamp=datetime.datetime.now())
				.set_footer(text = "Enter cancel to stop this session")
				.set_author(name = author.name, icon_url = author.avatar.url))

			await ctx.reply(embed=create_class_embed)
			cond = True
			while cond:
				reply_msg = await self.bot.wait_for('message', check=mcheck)
				if cancel(reply_msg.content):
					cond = False
					continue
				else:
					if len(reply_msg.content.split(" ")) > 1:
						break  # this break won't trigger the else in while-else construct
					else:
						await reply_msg.reply("Make sure to format the class alias like `CMPSC 465`, with a space in between!")
			else:  # this executes when cond is set to false
				await reply_msg.reply("Class creation session cancelled.")
				break
			class_alias = reply_msg.content.upper()

			mydb, my_cursor = sql.connect()
			my_cursor.execute("SELECT * FROM Classes WHERE Class_name = '%s'" % (class_alias))
			d = my_cursor.fetchall()
			sql.close(mydb, my_cursor)

			if len(d) > 0:
				await reply_msg.reply("**{}** has already been created! Are you sure you want to continue? (yes/no)".format(class_alias))
				reply_msg = await self.bot.wait_for('message', check=mcheck)
				if reply_msg.content.upper() == "NO":
					await reply_msg.reply("Class creation session cancelled.")
					break


			mydb, my_cursor = sql.connect()
			my_cursor.execute("SELECT Department_alias, Department_id FROM Departments")
			d = my_cursor.fetchall()
			sql.close(mydb, my_cursor)

			print(d)

			class_department = None
			Class_channel_id = None
			found_dep_status = True
			for dep in d:
				if dep[0] in class_alias:
					class_department, class_department_id = dep[0], dep[1]
					found_dep_status = False
					break

			if found_dep_status: #insert Department name into db since it doesnt exist
				await reply_msg.reply("This department doesn't seem to exist in the database! What does `{}` stand for and represent?\nFor example, `CMPSC` represents `Computer Science`.".format(class_alias.split(" ")[0]))
				cond = True
				while cond:
					reply = await self.bot.wait_for('message', check=mcheck)
					if cancel(reply_msg.content):
						cond = False
						continue
					else:
						to_input = reply_msg.content.title()
						break  # this break won't trigger the else in while-else construct
				else:  # this executes when cond is set to false
					await reply_msg.reply("Class creation session cancelled.")
					break


				mydb, my_cursor = sql.connect()
				my_cursor.execute("INSERT INTO Departments (Department_name, Department_alias) VALUES (%s, %s)",
				(to_input, class_alias.split(" ")[0]))
				mydb.commit()
				sql.close(mydb, my_cursor)

				mydb, my_cursor = sql.connect()
				my_cursor.execute("SELECT Department_alias, Department_id FROM Departments")
				d = my_cursor.fetchall()
				sql.close(mydb, my_cursor)

				print(d)

				class_department = None
				Class_channel_id = None
				for dep in d:
					if dep[0] in class_alias:
						class_department, class_department_id = dep[0], dep[1]
						break

			create_class_embed = (discord.Embed(title = "Please enter the full name of the class, for example: `Data Structures and Algorithms`", color=random.randint(111111, 999999), timestamp=datetime.datetime.now())
				.set_footer(text = "Enter cancel to stop this session")
				.set_author(name = author.name, icon_url = author.avatar.url))
			await reply_msg.reply(embed=create_class_embed)

			reply_msg = await self.bot.wait_for('message', check=mcheck)
			if cancel(reply_msg.content):
				await reply_msg.reply("Class creation session cancelled.")
				break
			class_name = reply_msg.content.title()

			create_class_embed = (discord.Embed(title = "Enter `confirm` to create the following class, or `cancel` to stop this session:\n **{}**: {}".format(class_alias, class_name), color=random.randint(111111, 999999), timestamp=datetime.datetime.now())
				.set_author(name = author.name, icon_url = author.avatar.url))
			await reply_msg.reply(embed=create_class_embed)
			reply_msg = await self.bot.wait_for('message', check=mcheck)
			if cancel(reply_msg.content):
				await reply_msg.reply("Class creation session cancelled.")
				break
			elif reply_msg.content.upper() == "CONFIRM":
				guild = ctx.guild
				e = discord.utils.get(ctx.guild.roles, name='@everyone')
				r = await guild.create_role(name=class_alias.title(), color=discord.Color.from_rgb(random.randint(0, 256), random.randint(0, 256), random.randint(0, 256)), hoist=True, mentionable=True)
				
				# overwrites = {
				# 	guild.e: discord.PermissionOverwrite(send_messages = True, read_messages = False),
				# 	guild.r: discord.PermissionOverwrite(read_messages = True)
				# }
				
				cat = await guild.create_category_channel(class_alias)
				await cat.edit(position=5)
				overwrite = discord.PermissionOverwrite()
				overwrite.send_messages = True
				overwrite.read_messages = False
				await cat.set_permissions(discord.utils.get(ctx.guild.roles, name='@everyone'), overwrite=overwrite)
				overwrite = discord.PermissionOverwrite()
				overwrite.read_messages = True
				await cat.set_permissions(r, overwrite=overwrite)

				await guild.create_text_channel("{}-resources".format(class_alias.split(" ")[1]), category=cat)
				ch = await guild.create_text_channel("{}-chat".format(class_alias.split(" ")[1]), category=cat)
				await guild.create_voice_channel("{} voice".format(class_alias.split(" ")[1]), category=cat)



				mydb, my_cursor = sql.connect()
				my_cursor.execute("INSERT INTO Classes (Class_department_id, Class_name, Class_full_name, Class_channel_id, Class_category_id, Class_role_id) VALUES (%s, %s, %s, %s, %s, %s)",
				(class_department_id, class_alias, class_name, str(ch.id), str(cat.id), str(r.id)))
				mydb.commit()
				# sql.close(mydb, my_cursor)
				await reply_msg.reply("{} has been successfully created! You can now join the class in <#{}> to view class channels and receive notifications.".format(class_alias, os.getenv("CLASS_SUB_CHANNEL")))


				my_cursor.execute("SELECT Class_name FROM Classes ORDER BY Class_name")
				d = my_cursor.fetchall()

				text = "**Join a class group chat and receive notifications by invoking one of the following command(s) below**:\n\n"
				
				arr = []
				for i in d:
					if i[0].split(" ")[0] not in [a[0] for a in arr]: #check if department is accounted for yet
						arr.append([i[0].split(" ")[0], [i[0]]]) # append [dept alias, [class]]
					else:
						for inner in arr:
							if i[0].split(" ")[0] == inner[0]:
								inner_arr = inner[1]
								inner_arr.append(i[0])
								break
					# text += "	◽{} - `!join {}`\n".format(i[0], i[0].split(" ")[1])
				await self.bot.get_channel(int(os.getenv("CLASS_SUB_CHANNEL"))).purge(limit=10)
				
				est = pytz.timezone('US/Eastern')
				em = discord.Embed(description = "**Join a class group chat and receive notifications by invoking one of the following command(s) below**:\n\n",
						color=0x10D600, timestamp=datetime.datetime.now())

				my_cursor.execute("SELECT Department_name, Department_alias FROM Departments")
				d = my_cursor.fetchall()
				# all_dept_names = [b[0] for b in d]

				for field in arr:
					text = ""
					for classs in field[1]:
						text += "{} - `!join {}`\n".format(classs, classs.split(" ")[1]) #join nested array together to string

					for dept in d:
						if field[0] == dept[1]:	
							em.add_field(name="{} | {}".format(dept[0], dept[1]), 
								value=text, inline=True)
							break

				await self.bot.get_channel(int(os.getenv("CLASS_SUB_CHANNEL"))).send(embed=em)

				sql.close(mydb, my_cursor)


				await self.bot.get_channel(int(os.getenv("CLASS_ANNOUNCEMENTS"))).send("A chat has been created for **{}**: {}! You can join it via <#{}>!".format(class_alias, class_name, os.getenv("CLASS_SUB_CHANNEL")))
			else:
				await reply_msg.reply("Class creation session cancelled.")
			break


	"""
		>> Helper function to delete a message after buf number of seconds
	"""
	async def delete_message(self, chnl, msg, buf: int = 3):
		try:
			await asyncio.sleep(buf)
			await msg.delete()
			return
		except discord.errors.NotFound:
			pass

	"""
		!join command
		>>	used to join classes and their respective class channels, as well get class role
	"""
	@commands.command(aliases=["sub"])
	@is_in_channel(int(os.getenv("CLASS_SUB_CHANNEL")),
					error_msg="You entered the command in the wrong channel! Head over to <#{}> and send it there.".format(os.getenv("CLASS_SUB_CHANNEL")))
	async def join(self, ctx, *args):
		channel, author = ctx.channel, ctx.author
		try:
			mydb, my_cursor = sql.connect()
			my_cursor.execute("SELECT Class_name, Class_channel_id, Class_role_id FROM Classes")
			d = my_cursor.fetchall()
			sql.close(mydb, my_cursor)

			status = True
			for c in d:
				if args[0].upper() == c[0].split(" ")[1].upper():
					await self.delete_message(channel, ctx.message, 0)
					r = discord.utils.get(ctx.guild.roles, id=int(c[2]))
					await author.add_roles(r) 
					m = await self.bot.get_channel(int(c[1])).send("You have successfully joined and will now receive all notifications/announcements pertaining to **{}**! {}".format(c[0], author.mention))

					status = False

					await self.update_class_member_count(int(c[2]), int(c[1]))

					est = pytz.timezone('US/Eastern')
					em = discord.Embed(color=0x10D600, timestamp=datetime.datetime.now())

					em.add_field(name="Member joined {} chat".format(c[0]), 
						value="► Name: `{}#{}` {} [{}]\n► Joined Server On: **{}**\n► Channel: {}\n► Added Role: {} [{}]"
									.format(author.name, author.discriminator, author.mention, author.id, author.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p'), self.bot.get_channel(int(c[1])).mention, r.mention, r.id), 
						inline=False)
					em.set_author(name = author.name, icon_url = author.avatar.url)
					staff_log_channel = self.bot.get_channel(int(os.getenv("STAFF_LOG_CHANNEL")))
					await staff_log_channel.send(embed=em)
					await self.reorder_channels()

			if status: await ctx.reply("`{}` doesn't seem to exist yet, try creating class chats and roles for it by doing `!create` in <#{}>! {}".format(cont[1], author.mention, os.getenv("CLASS_SUB_CHANNEL")))
		except Exception as e:
			await self.delete_message(channel, ctx.message, 0)
			m = await channel.send("Error! The command you entered is incorrect. For example, enter `!join 331` if you want to join the class CMPEN 331. {}".format(author.mention))
			print(e)
			await self.delete_message(channel, m, 10)

	"""
		!leave command
		>>	used to leave a certain class -- command only valid in class group chat channels
	"""
	@commands.command()
	async def leave(self, ctx, *args):
		channel, author = ctx.channel, ctx.author

		mydb, my_cursor = sql.connect()
		my_cursor.execute("SELECT Class_name, Class_channel_id, Class_role_id, Class_category_id FROM Classes")
		d = my_cursor.fetchall()
		sql.close(mydb, my_cursor)

		for c in d:
			if int(channel.id) == int(c[1]):
				await self.delete_message(channel, ctx.message, 0)
				r = discord.utils.get(ctx.guild.roles, id=int(c[2]))
				await author.remove_roles(r) 

				m = await self.bot.get_channel(int(os.getenv("CLASS_ANNOUNCEMENTS"))).send("You have successfully unsubscribed from **{}**!\n{}".format(c[0], author.mention))
				est = pytz.timezone('US/Eastern')
				em = discord.Embed(color=0xFA0000, timestamp=datetime.datetime.now())

				em.add_field(name="Member left {} chat".format(c[0]), 
					value="► Name: `{}#{}` {} [{}]\n► Joined Server On: **{}**\n► Channel: {}\n► Removed Role: {} [{}]".format(author.name, author.discriminator, author.mention, author.id, author.joined_at.astimezone(est).strftime('%a %b %d %Y %-I:%M%p'), self.bot.get_channel(int(c[1])).mention, r.mention, r.id), 
					inline=False)
				em.set_author(name = author.name, icon_url = author.avatar.url)
				staff_log_channel = self.bot.get_channel(int(os.getenv("STAFF_LOG_CHANNEL")))
				await staff_log_channel.send(embed=em)

				await self.update_class_member_count(int(c[2]), int(c[1]))
				await self.delete_message(self.bot.get_channel(int(os.getenv("CLASS_SUB_CHANNEL"))), m, 10)	
				await self.reorder_channels()
				return

		# Error Handling
		m = await ctx.reply("Wrong Channel! Please go to the class chat you want to leave and enter `!leave` there. {}".format(author.mention))
		await self.delete_message(channel, ctx.message, 10)
		await self.delete_message(channel, m, 0)

	"""
		Listener event for on_message
		>>	called when a message is created and sent
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message
	"""
	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		channel = message.channel
		
		# if message is in #class-subscriptions channel and not a !join command and message not from bot
		if channel.id == int(os.getenv("CLASS_SUB_CHANNEL")) and not message.content.upper().startswith("!JOIN") and message.author.id != int(os.getenv("BOT_ID")):
			await self.delete_message(channel, message, 1)

		try:
			#		(categories in order)	  server stats 		   information		general channels 	extracurricular		utility channels
			if channel.category_id not in os.getenv("CATEGORIES").split(","):
				if channel.category.position != 5:	# position 5 is the highest position after default categories listed above
					await channel.category.edit(position=5)
		except AttributeError:
			print("Tried to get category_id from DMChannel. Message: ", message.content, message.author.name, message.author.id)

	@join.error
	async def join_error(self, ctx, error):
		if isinstance(error, commands.CheckFailure):
			print("Join command entered in wrong channel.")
			pass

async def setup(bot):
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
		An extension must have a global function, setup 
			defined as the entry point on what to do when 
			the extension is loaded. 
		This entry point must have a single argument, the bot.
	"""
	await bot.add_cog(Classes(bot)) # add cog/Class by passing in instance
