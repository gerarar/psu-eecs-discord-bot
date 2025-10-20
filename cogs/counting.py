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
from dotenv import load_dotenv

load_dotenv() # adds environment variables to current environment

"""
	This cog is for commands dealing with counting
"""
class Counting(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.on_ready_status = True

		self.counting_LOCK = threading.Condition(lock=threading.Lock()) # condition lock
		self.counting_sem = threading.Semaphore(1)
		self.counting_number = False
		self.counting_number_userId = False
		self.MIN_CNTR = 0
		self.c_status = False

		# (1-n)% = 99% chance for bot to auto-reply with a counting number after successful user input
		self._BOT_REPLY_PROBABILITY = 0.01


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
		Check for commands, returns True if message not from bot
		>>	https://discordpy.readthedocs.io/en/stable/ext/commands/commands.html#checks
	"""
	def is_not_bot():
		async def predicate(ctx):
			print(ctx.author.id)
			print(self.bot.id)
			return ctx.author and ctx.author.id != self.bot.id
		return commands.check(predicate)

	"""
		Bot sends a new counting number to #counting 
	"""
	async def bot_counting_number(self):
		# global counting_number
		# global counting_number_userId
		
		self.counting_number = self.counting_number + 1
		self.counting_number_userId = 1234
		await self.bot.get_channel(int(os.getenv("COUNTING_CHANNEL"))).send("{0:b}".format(self.counting_number)) # bot sends counting number in binary

	"""
		1 minute loop for counting
		>>	if interrupted by condition lock, MIN_CNTR resets back to 0
		>>	otherwise condition lock timeouts and MIN_CNTR increments
	"""
	def counting_1minute_loop(self):

		self.counting_LOCK.acquire()
		print("about to wait")
		timeout = 60	# 1 minute
		ret_lock = self.counting_LOCK.wait(timeout) # False if timeout, True if notified -- reaquires lock regardless
		
		print(f"ret_lock: {ret_lock}")
		if ret_lock:
			print("########### Notified before timeout!")
			self.MIN_CNTR = 0
			print(f"MIN_CNTR RESET TO {self.MIN_CNTR}")

			self.timeout_minutes = random.randint(1,10)
			print(f"timeout_minutes: {self.timeout_minutes}")
			
		elif not ret_lock:
			print("Timeout!")
			inner_time = time.time()
			self.MIN_CNTR += 1

		self.counting_LOCK.release()
		return

	"""
		background loop for counting
		>>	if 'timeout_minutes' minutes has passed, bot will send a counting number to #counting channel
		>>		once bot has already done so, bot will just sleep until a user sends a number which restarts 30 minute timer
	"""
	async def background_loop_counting(self):

		self.MIN_CNTR = 0 	# counter to count how many minutes
		start = time.time()
		self.c_status = False 	# used to determine if bot can send a number

		await self.bot.wait_until_ready()

		self.timeout_minutes = random.randint(1,10)
		print("timeout_minutes:", self.timeout_minutes)
		# counting_LOCK.acquire()
		# counting_LOCK.wait() # wait until successful number sent by user, will notify and continue on.
		while not self.bot.is_closed():
			# await asyncio.gather(thread_func())
			if self.MIN_CNTR < self.timeout_minutes and self.c_status:
				print("prob", prob := random.random())
				if self.MIN_CNTR == 0 and prob > self._BOT_REPLY_PROBABILITY:	# (1-n)% chance for bot to immediately send a counting number after user input
					await self.bot_counting_number()
					print("AUTO1: counting number has been set to", self.counting_number)
					self.c_status = False	# set status to false so this clause cant run again til successful user number
					self.timeout_minutes = random.randint(1,10)	# get a new timeout to wait
					print(f"timeout_minutes: {self.timeout_minutes}")
					continue

				print("BEFORE ASYNCIO to_thread CALL")
				await asyncio.to_thread(self.counting_1minute_loop)
				print("AFTER ASYNCIO to_thread CALL")
			
			elif not self.c_status: 
				await asyncio.sleep(1)
				continue
			
			else:	# if timoput_minutes minutes has passed, have bot send a number if didnt send one since last user number
				await self.bot_counting_number()
				print("AUTO2: counting number has been set to", self.counting_number)
				self.MIN_CNTR = 0	# reset MIN_CNTR back to zero
				self.c_status = False	# set status to false so this clause cant run again til successful user number
				self.timeout_minutes = random.randint(1,10)	# get a new timeout to wait
				print(f"timeout_minutes: {self.timeout_minutes}")

			print(f"MIN_CNTR: {self.MIN_CNTR} -- {time.time()-start}")


	@commands.Cog.listener()
	async def on_ready(self):
		
		if self.on_ready_status: # this should only run once, especially when the API disconnects and reconnects
			self.on_ready_status = False

			mydb, my_cursor = sql.connect()

			# global counting_number
			if not self.counting_number:
				# mydb, my_cursor = sql.connect()
				my_cursor.execute("SELECT * FROM Counting_Channel")
				data = my_cursor.fetchall()

				# global counting_number_userId
				self.counting_number = int(data[0][1]) # set global variables
				self.counting_number_userId = str(data[0][0]) 

				counting_msgs = [message async for message in self.bot.get_channel(int(os.getenv("COUNTING_CHANNEL"))).history(limit=30)]
				for c_m in counting_msgs:
					try:
						number_msg = int(c_m.content, 2) # checks if msg is a valid binary number
						if number_msg > self.counting_number:
							# mydb, my_cursor = sql.connect()
							
							my_cursor.execute("TRUNCATE Counting_Channel")
							mydb.commit() #commit sql query

							# my_cursor.execute("INSERT INTO Counting_Channel(userId, numb) VALUES (%s, %s)",
							# 	( str(c_m.author.id), number_msg ))
							my_cursor.execute("INSERT INTO Counting_Channel(userId, numb) VALUES (%s, %s)",
								( str(1234), number_msg ))
							mydb.commit() #commit sql query

							# sql.close(mydb, my_cursor) #close connection to db

							self.counting_number = number_msg # save to global var
							self.counting_number_userId = str(c_m.author.id)
							print("overwrote counting number set in db")
						break
					except ValueError: # message sent is not of integer type
						await self.delete_message(c_m.channel, c_m, 0)

				sql.close(mydb, my_cursor)
				await self.bot_counting_number()

				print("Counting number has been set to", self.counting_number)

			# start loop for counting loop
			await asyncio.gather(self.background_loop_counting())

	"""
		Listener event for on_message
		>>	called when a message is created and sent
		>>	https://discordpy.readthedocs.io/en/stable/api.html#discord.on_message
	"""
	@commands.Cog.listener()
	async def on_message(self, message: discord.Message):
		author, channel = message.author, message.channel

		if channel.id == int(os.getenv("COUNTING_CHANNEL")) and author.id != int(os.getenv("BOT_ID")): # if message is in #counting channel and not from bot
			try:
				number_sent = int(message.content, 2) # checks if msg is a valid binary number
				
				print(f"entered number {number_sent} userId {author.id} counting_number {self.counting_number} counting_number_userId {self.counting_number_userId}")
				if self.counting_sem.acquire(blocking=False): #can grab semaphore lock

					#can correctly incremented global counting_number var and not same user as previous iteration
					if number_sent == (self.counting_number + 1) and self.counting_number_userId != str(message.author.id):
						mydb, my_cursor = sql.connect()
						
						my_cursor.execute("TRUNCATE Counting_Channel")
						mydb.commit() #commit sql query

						my_cursor.execute("INSERT INTO Counting_Channel(userId, numb) VALUES (%s, %s)",
							( str(message.author.id), number_sent ))
						mydb.commit() #commit sql query

						sql.close(mydb, my_cursor) #close connection to db

						self.counting_number = number_sent # save to global var
						self.counting_number_userId = str(message.author.id)
						# counting_number_userId = str(1234)   # for debug purposes 

						if number_sent == 69696:
							await message.reply("CONGRATULATIONS! YOU HAVE WON THE COUNTING GAME!! 🥳🎉🥳🎉 {}".format(message.author.mention))
						elif number_sent == 69649:
							await message.reply("CONGRATULATIONS! YOU GOT THE LAST PALIDROME BEFORE THE WINNING NUMBER!! 🥳🎉🥳🎉 {}".format(message.author.mention))
							await message.add_reaction(emoji="🇳")
							await message.add_reaction(emoji="🇮") 
							await message.add_reaction(emoji="🇨") 
							await message.add_reaction(emoji="🇪") 

						elif str(message.content) == str(message.content)[::-1]:
							await message.reply("Congrats, you got a Palindrome! {}".format(message.author.mention))
							await message.add_reaction(emoji="🇳")
							await message.add_reaction(emoji="🇮") 
							await message.add_reaction(emoji="🇨") 
							await message.add_reaction(emoji="🇪") 

						elif number_sent % 1000 == 0:
							await channel.send("{}!!! 🥳🎉\n{}% of goal achieved!".format(number_sent, round(number_sent/69696*100, 3)))

						elif number_sent % 100 == 0:
							await channel.send("{}! 🎉\n{}% of goal achieved!".format(number_sent, round(number_sent/69696*100, 3)))
						
						self.counting_sem.release() #release sem lock

						self.counting_LOCK.acquire()
						start = time.time() # reset time global var

						print("Notifying counting_1minute_loop()")
						self.counting_LOCK.notify()
						self.counting_LOCK.release()
						self.c_status = True

					else:
						self.counting_sem.release() #release sem lock
						await self.delete_message(channel, message, 0)

				else: #cannot grab semaphore lock
					await self.delete_message(channel, message, 0)

			except ValueError: # message sent is not of integer type
				await self.delete_message(channel, message, 0)


async def setup(bot):
	"""
		>> https://discordpy.readthedocs.io/en/latest/ext/commands/cogs.html
		An extension must have a global function, setup 
			defined as the entry point on what to do when 
			the extension is loaded. 
		This entry point must have a single argument, the bot.
	"""
	await bot.add_cog(Counting(bot)) # add cog/Class by passing in instance
