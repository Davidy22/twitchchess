from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image as kiImage
from kivy.graphics import Color, Rectangle
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from stockfish import Stockfish
import chess
import chess.pgn
import render
import configparser
from kivy.clock import Clock
from twitchio.ext import commands
from multiprocessing import Process, Manager
from matplotlib import pyplot
import numpy as np
from kivy.config import Config
from time import sleep
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')

secrets = configparser.ConfigParser()
temp = open("secrets.conf")
secrets.read_file(temp)


bot = commands.Bot(
		irc_token=secrets['DEFAULT']['oath'],
		client_id=secrets['DEFAULT']['client_id'],
		nick=secrets['DEFAULT']['nick'],
		prefix=secrets['DEFAULT']['prefix'],
		initial_channels=[secrets['DEFAULT']['channel']]
	)


class main(FloatLayout):
	def __init__(self, **kwargs):
		super(main, self).__init__(**kwargs)
		global moves
		global voted
		self.size = (1280,720)
		with self.canvas:
			Color(rgb=(1,1,1))
			Rectangle(size=self.size, pos=self.pos)
		self.orientation = "vertical"
		self.countdown = 0
		self.counting = False
		self.hold_message_ticks = 0
		self.lastmove = None
		
		#init from file
		self.stats = configparser.ConfigParser()
		temp = open("game.log")
		self.stats.read_file(temp)
		
		self.render = kiImage(pos = (-350,70))
		self.add_widget(self.render)
		self.fish = Stockfish(parameters={"Minimum Thinking Time": 4, "Slow Mover": 10, "Move Overhead": 1})
		self.board = chess.Board()
		self.renderer = render.DrawChessPosition()
		self.moves_string = ""
		self.board.set_fen(self.stats["GAME"]["board"])
		self.is_white = self.board.turn
		
		self.skill = float(self.stats["DEFAULT"]["level"])
		self.fish.set_skill_level(self.skill)
		self.fish.depth = "18"
		
		self.update_board()
		
		self.move_ranks = kiImage(pos = (140,223))
		self.add_widget(self.move_ranks)
		
		self.info_text = "Stockfish level: %d" % self.skill
		self.info = Label(text = self.info_text, size_hint_y = 1, size_hint_x = 1, markup = True, text_size = (500, 100), pos = (200, 36), valign = "top")
		self.add_widget(self.info)
		
		self.move_options = Label(text = self.moves_string, markup = True, text_size = (1260, 200), pos = (10, -320), valign = "top")
		self.set_legal_moves()
		self.add_widget(self.move_options)
		
		self.game_history = chess.pgn.Game()
		self.last_game_node = None
		self.move_history = Label(text = self.format_text("Move history:"), markup = True, text_size = (700, 240), pos = (300, -120), valign = "top")
		self.set_legal_moves()
		self.add_widget(self.move_history)
		
		self.countdown = False
		
		Clock.schedule_interval(self.tally, 2)
		Clock.schedule_interval(self.update_info, 1)
	
	def format_text(self, text, font_size = 23):
		return "[color=000000][size=%d][b]%s[/b][/size][/color]" % (font_size, text)
		
	def update_history(self, reset = False):
		if reset:
			self.game_history = chess.pgn.Game()
			self.last_game_node = None
		else:
			if self.last_game_node is None:
				self.last_game_node = self.game_history.add_main_variation(self.board.move_stack[-1])
			else:
				self.last_game_node = self.last_game_node.add_main_variation(self.board.move_stack[-1])
		self.move_history.text = self.format_text("Move history:\n%s" % str(self.game_history.mainline_moves()), font_size = 22)
		
	def update_info(self, dt = 0, text = None, hold = False):
		if self.hold_message_ticks > 0:
			self.hold_message_ticks -= 1
			return
		if hold:
			self.hold_message_ticks = 5
		
		if text is None:
			self.info_text = "Opponent: stockfish lvl %d, approx ELO %s\nHikaru approx ELO: 2800" % (self.skill, self.stats["ELO"][str(int(self.skill))])
			if self.countdown > 0:
				self.countdown -= dt
				if self.countdown < 0:
					self.countdown = 0
				self.info_text += "\n%d seconds left to vote this turn" % self.countdown
			self.info.text =  self.format_text(self.info_text)
		else:
			self.info.text = self.format_text(text)
	
	def update_board(self):
		image = self.renderer.draw(self.board.fen(), self.is_white, lastmove = self.lastmove)
		data = BytesIO()
		image.save(data, format='png')
		data.seek(0)
		im = CoreImage(BytesIO(data.read()), ext='png')
		self.render.texture = im.texture
		
	def update_plot(self):
		buf = BytesIO()
		pyplot.savefig(buf, format='png', bbox_inches='tight')
		buf.seek(0)
		im = CoreImage(BytesIO(buf.read()), ext='png')
		self.move_ranks.texture = im.texture

	def fish_move(self):
		self.fish.set_fen_position(self.board.fen())
		self.lastmove = self.fish.get_best_move()
		self.board.push_uci(self.lastmove)
		self.update_board()
		self.update_history()
	
	def player_move(self, dt):
		pyplot.clf()
		highmove = None
		highvote = -1
		for move in moves.keys():
			if moves[move] > highvote:
				highmove = move
				highvote = moves[move]
		
		if highmove == "resign":
			self.end_game("l")
			return
		elif highmove == "draw":
			# Evaluate draw, has_insufficient_material()
			return
		else:
			self.board.push_san(highmove)
			self.update_board()
		
		self.update_history()
		Clock.schedule_once(self.player_move_)
		
	def player_move_(self, dt):
		status = self.board.result()
		if status == "*":
			self.fish_move()
			status = self.board.result()
			if status == "*":
				self.set_legal_moves()
			elif status == "1/2-1/2":
				self.end_game("d")
			else:
				#pause before ending game
				self.end_game("l")
		elif status == "1/2-1/2":
			self.end_game("d")
		else:
			self.end_game("w")
		self.counting = False
		self.lastmove = None
	
	def end_game(self, result):
		#TODO: logging, rank change, etc
		self.log(result)
		if result == "w":
			a = accounts.value
			votes = total_voted.value
			for vote in votes:
				if vote in a["DEFAULT"]:
					a["DEFAULT"][vote] = str(int(int(a["DEFAULT"][vote]) + (self.skill * 100)))
				else:
					a["DEFAULT"][vote] = str(int(self.skill * 100))
			
			with open("accounts.conf", "w") as f:
				a.write(f)
			
			accounts.set(a)
			
			self.update_info(text = "Twitch chat won, %d points awarded to participants" % (self.skill * 100), hold = True)
			if self.skill < 20:
				self.skill += 1
				self.fish.set_skill_level(self.skill)
		elif result == "d":
			self.update_info(text = "You drew", hold = True)
		else:
			if self.skill > 1:
				self.skill -= 1
				self.fish.set_skill_level(self.skill)
			self.update_info(text = "Twitch chat lost", hold = True)
		
		total_voted.set(set())
			
		self.board.reset()
		self.update_history(reset=True)
		self.is_white = not self.is_white
		if not self.is_white:
			self.fish_move()
		self.set_legal_moves()
		self.counting = False
		
		Clock.schedule_once(self.end_game_, 4)
		
	def end_game_(self, dt):
		self.update_board()
	
	def log(self, result):
		if result == "w":
			self.stats["DEFAULT"]["win"] = str(int(self.stats["DEFAULT"]["win"]) + 1)
		elif result == "d":
			self.stats["DEFAULT"]["draw"] = str(int(self.stats["DEFAULT"]["draw"]) + 1)
		elif result == "l":
			self.stats["DEFAULT"]["loss"] = str(int(self.stats["DEFAULT"]["loss"]) + 1)
		
		#write back
	
	def set_legal_moves(self):
		global moves
		global voted
		moves.clear()
		for move in self.board.legal_moves:
			moves[self.board.san(move.from_uci(move.uci())).replace("+", "").replace("#","")] = 0
		moves["resign"] = 0
		#moves["draw"] = 0
		self.moves_string = self.format_text("Legal moves, type in chat to vote (case sensitive):\n" + ", ".join(moves.keys()))
		self.move_options.text = self.moves_string
		voted.set(set())
		
	def tally_count(self, val):
		return val[1]
	
	def tally(self, dt):
		global moves
		data = []
		for move in moves.keys():
			data.append((move, moves[move]))
		
		data.sort(key=self.tally_count, reverse = True)
		labels = []
		quantity = []
		for i in data[:7]:
			labels.append(i[0])
			quantity.append(i[1])
			
		y = np.arange(len(labels))
		pyplot.figure(figsize = (5,3))
		pyplot.bar(y, quantity, align='center', alpha=0.5, width=1.0)
		pyplot.xticks(y, labels)
		pyplot.ylim(ymin=0, ymax=quantity[0])
		pyplot.gca().axes.get_yaxis().set_visible(False)
		self.update_plot()
		pyplot.close()
		
		if len(voted.get()) > 0 and not self.counting:
			Clock.schedule_once(self.player_move, 15)
			self.countdown = 15
			self.counting = True
			
		
@bot.event
async def event_ready():
	print(f"{secrets['DEFAULT']['nick']} is online!")
	ws = bot._ws
	await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me bot now listening")

@bot.event
async def event_message(ctx):
	global moves
	global voted
	await bot.handle_commands(ctx)
	# Add move to tally if valid
	votes = voted.value
	comment = ctx.content.replace("+", "").replace("#","")
	if comment in moves and not (ctx.author.name in votes):
		if len(votes) == 0:
			ws = bot._ws
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me The first vote has been cast, a move will be made in 15 seconds")
		
		moves[comment] += 1
		votes.add(ctx.author.name)
		voted.set(votes)
		t = total_voted.value
		t.add(ctx.author.name)
		total_voted.set(t)

@bot.command(name="notation")
async def command_notation(ctx):
	ws = bot._ws
	await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Guide to voting move notation https://cheatography.com/davechild/cheat-sheets/chess-algebraic-notation/")

@bot.command(name="points")
async def command_points(ctx):
	ws = bot._ws
	a = accounts.value
	print(a)
	if ctx.author.name in a["DEFAULT"].keys():
		await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you have %s points." % (ctx.author.name, a["DEFAULT"][ctx.author.name]))
	else:
		a["DEFAULT"][ctx.author.name] = "0"
		await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you have %s points." % (ctx.author.name, "0"))
		accounts.set(a)


class chessApp(App):

	def build(self):
		return main()

if __name__ == '__main__':
	# TODO: Replace globals with SQLlite
	a = configparser.ConfigParser()
	temp = open("accounts.conf")
	a.read_file(temp)
	
	accounts = Manager().Value(configparser.ConfigParser, a)
	moves = Manager().dict()
	voted = Manager().Value(set, set())
	total_voted = Manager().Value(set, set())
	p1 = Process(target=bot.run)
	p2 = Process(target=chessApp().run)
	p1.start()
	p2.start()
	p1.join()
	p2.join()
