import sqlite3
import datetime

class conn():
	def __init__(self):
		self.conn = sqlite3.connect("tpp.db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
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
		self.c.execute('INSERT INTO accounts(name, points, daily) VALUES (?, ?, ?)', (username, int(points), datetime.datetime(2000,1,1,1,1,1)))
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
	
	def add_game_param(self, name, value, replace = False):
		try:
			self.c.execute('INSERT INTO next(field, val) VALUES (?, ?)', (name, value))
		except:
			if replace:
				self.c.execute('UPDATE next set val = ? where field = ?', (value, name))
			else:
				return False
		self.conn.commit()
		return True
	
	def challenge(self, challenger, victim, amount):
		try:
			result = self.c.execute('select timestamp from challenges where victim = ?', (victim,)).fetchall()[0][0]
			if (datetime.datetime.now() - result).seconds > 900:
				self.delete_challenge(victim)
			else:
				return False
		except:
			pass
		try:
			result = self.c.execute('select timestamp, victim from challenges where challenger = ?', (victim,)).fetchall()[0]
			if (datetime.datetime.now() - result[0]).seconds > 900:
				self.delete_challenge(result[1])
			else:
				return False
		except:
			pass
		try:
			self.c.execute('insert into challenges(challenger,victim,amount,timestamp) Values (?, ?, ?, ?)', (challenger, victim, amount, datetime.datetime.now()))
			self.conn.commit()
			return True
		except:
			return False
	
	def accept_challenge(self, victim):
		try:
			result = self.c.execute('select challenger,victim,amount,timestamp from challenges where victim = ?', (victim,)).fetchall()[0]
			if (datetime.datetime.now() - result[3]).seconds > 900:
				self.delete_challenge(victim)
				return None
			
			return result
		except:
			return None
		
	def delete_challenge(self, victim):
		self.c.execute('delete from challenges where victim = ?', (victim,))
		self.conn.commit()

	def get_daily_status(self, user):
		#79200
		try:
			result = self.c.execute('select daily from accounts where name = ?', (user,)).fetchall()[0][0]
			diff = (datetime.datetime.now() - result)
			if diff.days > 0:
				return True
			
			if diff.seconds > 79200:
				return True
			else:
				return diff.seconds
		except:
			import traceback
			traceback.print_exc()
			return None
	
	def reset_account_date(self, user):
		self.c.execute("update accounts set daily=? where name=?", (datetime.datetime.now(),user))
		self.conn.commit()

	def add_vip_points(self, user, amount):
		prevrank = self.get_vip_rank(user)
		self.c.execute("update accounts set vip=vip+? where name=?", (amount,user))
		self.conn.commit()
		badges = 20 # Change constants with VIP badge count
		newrank = self.get_vip_rank(user)
		if prevrank[0] > badges and newrank[0] <= badges:
			return self.get_vip_list()[badges][0]
		return newrank
	
	def get_vip_rank(self, user):
		return self.c.execute("SELECT (SELECT COUNT(*) FROM accounts AS x WHERE x.vip >= t.vip) AS Rank, t.vip FROM accounts as t where name = ?", (user,)).fetchall()[0]
	
	def get_vip_list(self): #TODO: Make this cache
		return self.c.execute("SELECT t.name, t.vip, (SELECT COUNT(*) FROM accounts AS x WHERE x.vip >= t.vip) AS Rank FROM accounts as t order by Rank, t.id").fetchall()
