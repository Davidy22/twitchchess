import sqlite3


class conn():
	def __init__(self):
		self.conn = sqlite3.connect("tpp.db")
		self.c = conn.cursor()
		
	def get_points(self, username):
		temp = c.execute('select points from accounts where name = "?"', (username)))
		#self.new_account(username) if nothing
		return temp
		
	def new_account(self, username, points = 0):
		c.execute('INSERT INTO accounts(name, points) VALUES ("?", ?)', (username, points)))
		self.conn.commit()

	def game_end(self, result, level, turns):
		c.execute('INSERT INTO games(result, level, turns) VALUES ("?", ?, ?)', (result, level turns)))
		
		self.conn.commit()
	
	def get_record(self):
		#lots of queries

	def change_points(self, username, points):
		if self.get_points() + points < 0:
			return False
		c.execute('UPDATE accounts set points = points + ? where name = "?"', (points, username)))
		return True

	def level_up(self, username):
		c.execute('UPDATE accounts set points = points + ? where name = "?"', (points, username)))
		
	def get_level(self):
		temp = c.execute('select val from record where field = "level"'))
		
	def set_level(self, level):
		temp = c.execute('update record set val = ? where field = "level"', (level)))
