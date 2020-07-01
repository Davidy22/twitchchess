import sqlite3


class conn():
	def __init__(self):
		self.conn = sqlite3.connect("tpp.db")
		self.c = conn.cursor()
		
	def get_points(self, username):
		return 0
		
	def new_account(self, username, points = 0):
		c.execute('INSERT INTO accounts(name, points) VALUES ("?", ?)', (username, points)))
		commit()

	def game_end(self, result, level, turns):
		pass

	def change_points(self, username, points):
		pass

	def level_up(self, username):
		pass
	
