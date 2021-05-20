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
import mysqlConnection_local as sql # mysql file
import traceback
import pytz
import threading

def is_in_channel(counting_chnl):
	async def predicate(ctx):
		print("ctx.channel.id", ctx.channel.id)
		print("counting_chnl", counting_chnl)
		return ctx.channel and ctx.channel.id == counting_chnl
	return commands.check(predicate)

class Classes(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	def to_upper(argument):
		return argument.upper()
	"""
		This cog is for commands dealing with classes
	"""

	@commands.command(aliases=["hi"]) 
	async def hello(self, ctx, *args):
		# print(type(content))
		await ctx.send(f'Hello {ctx.author.name}. {args}')


	"""
		Listener event for on_message
		>>	called when a message is created and sent
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message
	"""
	# @commands.Cog.listener()
	# # @is_in_channel(1234)
	# async def on_message(self, message: discord.Message):
	# 	# print(message.content)
	# 	print("msg is in channel!")

	"""
		!add command
		>>	used to add reminders for a certain class like homework, exams, etc.
	"""
	@commands.command()
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
				my_cursor.execute("SELECT * FROM Classes WHERE Class_name = '%s'" % (reply.content.upper()))
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
					await reply_msg.reply("Error! Can't seem to find the class **{}**.\nPlease double check that you have entered it correctly and re-enter it!".format(reply.content.upper()))
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



def setup(bot):
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
		An extension must have a global function, setup 
			defined as the entry point on what to do when 
			the extension is loaded. 
		This entry point must have a single argument, the bot.
	"""
	bot.add_cog(Classes(bot)) # add cog/Class by passing in instance