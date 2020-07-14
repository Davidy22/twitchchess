import sqlite3


class conn():
	def __init__(self):
		self.conn = sqlite3.connect("tpp.db")
		self.c = self.conn.cursor()
		
	def get_points(self, username, no_create = False):
		try:
			return self.c.execute('select points from accounts where name = ?', (username, )).fetchall()[0][0]
		except:
			if no_create:
				return None
			else:
				self.new_account(username)
				return 0

	def get_player_level(self, username, no_create = False):
		try:
			return self.c.execute('select level from accounts where name = ?', (username, )).fetchall()[0][0]
		except:
			if no_create:
				return None
			else:
				self.new_account(username)
				return 1
	
	
	def new_account(self, username, points = 0):
		self.c.execute('INSERT INTO accounts(name, points) VALUES (?, ?)', (username, int(points)))
		self.conn.commit()

	def game_end(self, result, level, voters, text):
		self.c.execute('INSERT INTO games(result, level, voters) VALUES (?, ?, ?)', (result, level, voters))
		self.conn.commit()
		gameno = self.c.execute('select seq from sqlite_sequence where name="games"').fetchall()[0][0]
		f = open("log/%s/%d.pgn" % (result, gameno), "w")
		f.write(text)
		f.close()
	
	def get_record(self):
		# Get [wins, draws, losses]
		return (self.c.execute('select count(*) from games where result = "w"').fetchall()[0][0],
		self.c.execute('select count(*) from games where result = "d"').fetchall()[0][0],
		self.c.execute('select count(*) from games where result = "l"').fetchall()[0][0])
	
	def get_game(self, gameid):
		#get game text
		try:
			temp = self.c.execute('select * from games where no = ?', (gameid,)).fetchall()[0]
			f = open("log/%s/%d.pgn" % (temp[1],temp[0]))
			
			if temp[1] == "w":
				return " ".join(f.readlines()[8:]) + " Win"
			elif temp[1] == "l":
				return " ".join(f.readlines()[8:]) + " Loss"
			else:
				return " ".join(f.readlines()[8:]) + " Draw"
				
			
		except:
			return "Invalid game ID"
	
	def get_round_no(self):
		return int(self.c.execute('select seq from sqlite_sequence where name="games"').fetchall()[0][0]) + 1
	
	def change_points(self, username, points):
		# If insufficient points for spending, return false
		if self.get_points(username) + points < 0:
			return False
		self.c.execute('UPDATE accounts set points = points + ? where name = ?', (int(points), username))
		self.conn.commit()
		return True

	def level_up(self, username):
		try:
			self.c.execute('UPDATE accounts set level = level + 1 where name = ?', (username,))
		except:
			self.new_account(username)
			self.c.execute('UPDATE accounts set level = level + 1 where name = ?', (username,))
			
		self.conn.commit()
		
	def get_level(self):
		try:
			return self.c.execute('select val from record where field = "level"').fetchall()[0][0]
		except:
			return None
		
	def set_level(self, level):
		self.c.execute('update record set val = ? where field = "level"', (level,))
		self.conn.commit()
	
	def new_game(self):
		self.c.execute('delete from current')
		self.c.execute('replace into record select * from next where field = "level"')
		self.c.execute('delete from next where field = "level"')
		self.c.execute('insert into current select * from next')
		self.c.execute('delete from next')
		self.conn.commit()
		return self.get_game_params()
		
	def get_game_params(self, param = None):
		if param == None:
			db = self.c.execute('select * from current').fetchall()
			if len(db) == 0:
				return None
			temp = {}
			for row in db:
				temp[row[0]] = row[1]
			return temp
		else:
			return self.c.execute('select val from current where field = ?', (param,)).fetchall()[0][0]
	
	def add_game_param(self, name, value):
		self.c.execute('INSERT INTO next(field, val) VALUES (?, ?)', (name, value))
		self.conn.commit()
