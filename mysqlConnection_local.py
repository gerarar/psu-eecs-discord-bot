import mysql.connector
import inspect


mydb, my_cursor = None, None

def connect():
	mydb = mysql.connector.connect(
			host = "host address",
			user = "username",
			password = "password",
			database = "name of db",
			connect_timeout = 300,
			use_unicode = True,
			charset = "utf8",
			)

	my_cursor = mydb.cursor()
	my_cursor.execute('SET GLOBAL connect_timeout=10')
	my_cursor.execute('SET GLOBAL wait_timeout=200')
	my_cursor.execute('SET SESSION wait_timeout=200')
	my_cursor.execute('SET GLOBAL interactive_timeout=200')
	my_cursor.execute('SET SESSION interactive_timeout=200')

	return mydb, my_cursor

def close(db, cur):
	cur.close()
	db.close()
	return