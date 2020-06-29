import sqlite3
import configparser


#accounts
a = configparser.ConfigParser()
temp = open("accounts.conf")
a.read_file(temp)

#game
g = configparser.ConfigParser()
temp = open("game.log")
g.read_file(temp)

conn = sqlite3.connect("tpp.db")
c = conn.cursor()

for i in a["DEFAULT"]:
	c.execute('INSERT INTO accounts(name, points) VALUES ("%s", %s)' % (i, a["DEFAULT"][i]))

conn.commit()
conn.close()
