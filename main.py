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
from multiprocessing import Process, Manager, Array
from matplotlib import pyplot
import numpy as np
from kivy.config import Config
from time import sleep
from datetime import date
from collections import deque
import tpcdb
from util import *
import random
from textwrap import wrap
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')

secrets = configparser.ConfigParser()
temp = open("secrets.conf")
secrets.read_file(temp)

db = tpcdb.conn()

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
		self.board_evaluations = deque([], 4)
		
		#init from file
		#self.stats = configparser.ConfigParser()
		#temp = open("game.log")
		#self.stats.read_file(temp)
		
		self.render = kiImage(pos = (-350,70))
		self.add_widget(self.render)
		self.fish = Stockfish(parameters={"Minimum Thinking Time": 4, "Slow Mover": 10, "Move Overhead": 1})
		self.board = chess.Board()
		self.renderer = render.DrawChessPosition()
		self.moves_string = ""
		#self.board.set_fen("4r1k1/B4p2/PPPPPPPP/bpbbbpbp/PPPPPPPP/1P2P2P/4q3/6K1 b - - 8 43")
		#self.is_white = False
		self.is_white = self.board.turn
		self.record = db.get_record()
		self.round = db.get_round_no()
		
		self.fish.set_skill_level(db.get_level())
		self.fish.depth = "18"
		
		self.custom_init()
		
		self.update_board()
		
		self.move_ranks = kiImage(pos = (140,223))
		self.add_widget(self.move_ranks)
		
		self.info_text = "Stockfish level: %d" % db.get_level()
		self.info = Label(text = self.info_text, size_hint_y = 1, size_hint_x = 1, markup = True, text_size = (660, 100), pos = (280, 45), valign = "top")
		self.add_widget(self.info)
		
		self.move_options = Label(text = self.moves_string, markup = True, text_size = (1260, 200), pos = (2, -317), valign = "top")
		self.add_widget(self.move_options)
		
		self.game_history = chess.pgn.Game()
		self.last_game_node = None
		self.set_legal_moves()
		self.update_history(reset=True)
		
		self.thinking_label = Label(text = self.format_text("Thinking...", font_size = 65), markup = True, text_size = (1260, 200), pos = (6000, 180), valign = "top")
		self.add_widget(self.thinking_label)
		
		self.countdown = False
		self.update_plot(init = True)
		self.evaluate_position()
		
		Clock.schedule_interval(self.tally, 2)
		Clock.schedule_interval(self.update_info, 1)
	
	def format_text(self, text, font_size = 27):
		return "[color=000000][size=%d][b]%s[/b][/size][/color]" % (font_size, text)
		
	def evaluate_draw(self):
		if len(self.board_evaluations) < 4:
			return False
			
		if self.board.has_insufficient_material(not self.is_white):
			return True
		for i in self.board_evaluations:
			#assume fish white
			if self.is_white:
				const = -1
			else:
				const = 1
			if i["type"] == "mate" and i["value"] * const > 0:
				return False
			if i["type"] == "cp" and not i["value"] == 0:
				return False
		
		return True
	
	def evaluate_position(self):
		try:
			self.fish.set_fen_position(self.board.fen())
			self.board_evaluations.append(self.fish.get_evaluation())
		except:
			# No eval given on finished games
			pass
	
	def evaluate_resign(self):
		try:
			if self.board_evaluations[-1]["type"] == "mate":
				return (self.is_white and self.board_evaluations[-1]["value"] > 0) or (not self.is_white and self.board_evaluations[-1]["value"] < 0)
			else:
				for i in self.board_evaluations:
					#assume fish white
					if self.is_white:
						const = -1
					else:
						const = 1
					if i["type"] == "mate" and i["value"] * const > 0:
						return False
					if i["type"] == "cp" and i["value"] * const > -900:
						return False
				
				return True
		except:
			return False
		
	def update_history(self, reset = False):
		if reset:
			c = custom_game.value
			self.game_history = chess.pgn.Game()
			self.game_history.setup(self.board.fen())
			self.last_game_node = None
			self.game_history.headers["Event"] = "Twitch plays chess"
			self.game_history.headers["Site"] = "Twitch.tv"
			self.game_history.headers["Date"] = date.today().strftime("%Y/%m/%d")
			self.game_history.headers["Round"] = self.round
			if not c is None and "challenger" in c:
				opp = c["challenger"]
			else:
				opp = "Stockfish %d" % db.get_level()
			
			if self.is_white:
				self.game_history.headers["White"] = "Twitch chat"
				self.game_history.headers["Black"] = opp
			else:
				self.game_history.headers["White"] = opp
				self.game_history.headers["Black"] = "Twitch chat"
			#self.game_history["Result"]
		else:
			if self.last_game_node is None:
				self.last_game_node = self.game_history.add_main_variation(self.board.move_stack[-1])
			else:
				self.last_game_node = self.last_game_node.add_main_variation(self.board.move_stack[-1])
		hist = str(self.game_history.mainline_moves())
		history.set(hist)
		
	def update_info(self, dt = 0, text = None, hold = False):
		c = custom_game.value
		if self.hold_message_ticks > 0:
			self.hold_message_ticks -= 1
			return
		if hold:
			self.hold_message_ticks = 5
		
		if text is None:
			if not c is None and "challenger" in c:
				self.info_text = "Opponent: %s\n" % c["challenger"]
				if not c["turn"]:
					self.info_text += "Twitch chat's turn"
				else:
					self.info_text += "%s's turn" % c["challenger"]
			else:
				skill = db.get_level()
				self.info_text = "Opponent: stockfish lvl %d, approx ELO %d" % (skill, int(1000 + skill * 90))
			
				if self.board_evaluations[-1]["type"] == "mate":
					if self.board_evaluations[-1]["value"] > 0:
						self.info_text += "\nWhite mate in %d" % self.board_evaluations[-1]["value"]
					else:
						self.info_text += "\nBlack mate in %d" % (self.board_evaluations[-1]["value"] * -1)
				elif self.evaluate_draw():
					self.info_text += "\nFish requesting draw"
				else:
					self.info_text += "\nBoard evaluation: %.2f" % (self.board_evaluations[-1]["value"] / 100)

			
			self.info_text += ", Game %d, W:%d, D:%d, L:%d" % (self.round, self.record[0], self.record[1], self.record[2])
			if self.countdown > 0:
				self.countdown -= dt
				if self.countdown < 0:
					self.countdown = 0
				self.info_text += "\n%d seconds left to vote this turn" % self.countdown
			self.info.text =  self.format_text(self.info_text, font_size = 23)
		else:
			self.info.text = self.format_text(text, font_size = 23)
	
	def update_board(self):
		image = self.renderer.draw(self.board.fen(), self.is_white, lastmove = self.lastmove)
		data = BytesIO()
		image.save(data, format='png')
		data.seek(0)
		im = CoreImage(BytesIO(data.read()), ext='png')
		self.render.texture = im.texture
		
	def update_plot(self, init = False):
		if init:
			pyplot.figure(figsize = (5,3))
			pyplot.bar([], [], align='center', alpha=0.5, width=1.0)
			pyplot.xticks([], [])
			pyplot.gca().axes.get_yaxis().set_visible(False)
		
		buf = BytesIO()
		pyplot.savefig(buf, format='png', bbox_inches='tight')
		buf.seek(0)
		im = CoreImage(BytesIO(buf.read()), ext='png')
		self.move_ranks.texture = im.texture
		
		if init:
			pyplot.close()

	def fish_move(self):
		c = custom_game.value
		if not c is None and "turn" in c:
			c["turn"] = not c["turn"]
			custom_game.set(c)
			self.set_legal_moves()
			return
		if self.evaluate_resign():
			self.end_game("w")
			return
		self.thinking_label.pos = (600, 180)
		Clock.schedule_once(self.fish_move_)
	
	def fish_move_(self, dt):
		status = self.board.result()
		if status == "*":
			pass
		elif status == "1/2-1/2":
			self.end_game("d")
		else:
			#pause before ending game
			self.end_game("l")
		self.fish.set_fen_position(self.board.fen())
		self.lastmove = self.fish.get_best_move()
		self.board.push_uci(self.lastmove)
		self.update_board()
		self.update_history()
		self.evaluate_position()
		self.set_legal_moves()
		self.thinking_label.pos = (6000, 180)
	
	def player_move(self, dt):
		pyplot.clf()
		highmove = None
		highvote = -1
		
		notation_moves_list = notation_moves.value
			
		for move in notation_moves_list:
			temp = 0
			for i in notation_moves_list[move]:
				temp += moves[i]
			if temp > highvote:
				highmove = move
				highvote = temp
		
		if highmove == "resign":
			c = custom_game.value
			if not c is None and "turn" in c:
				if c["turn"]:
					self.end_game("w")
				else:
					self.end_game("l")
			else:
				self.end_game("l")
			return
		elif highmove == "draw":
			if self.evaluate_draw():
				self.end_game("d")
			else:
				self.update_info(text = "Draw rejected", hold = True)
				self.set_legal_moves()
				self.counting = False
				self.update_plot(init = True)
			return
		else:
			self.board.push_san(highmove)
			self.update_board()
			self.evaluate_position()
		
		self.update_history()
		self.update_plot(init = True)
		self.update_info()
		Clock.schedule_once(self.player_move_)
		
	def player_move_(self, dt):
		status = self.board.result()
		if status == "*":
			self.fish_move()
		elif status == "1/2-1/2":
			self.end_game("d")
		else:
			c = custom_game.value
			if not c is None and "turn" in c:
				if c["turn"]:
					self.end_game("l")
				else:
					self.end_game("w")
			else:
				self.end_game("w")
		self.counting = False
		self.lastmove = None
	
	def end_game(self, result):
		#TODO: logging, rank change, etc
		self.lastmove = None
		self.board_evaluations = deque([], 4)
		votes = total_voted.value
		skill = db.get_level()
		self.log(result, skill, votes)
		if result == "w":
			c = custom_game.value
			if not c is None and "challenger" in c:
				payout = 2000
			else:
				payout = skill * 100
				
			for vote in votes:
				db.change_points(vote, payout)
			
			self.update_info(text = "Twitch chat won, %d points awarded to participants" % payout, hold = True)
			if skill < 20:
				skill += 1
				self.fish.set_skill_level(skill)
				db.set_level(skill)
		elif result == "d":
			for vote in votes:
				db.change_points(vote, 50)
			self.update_info(text = "You drew, 50 points awarded to participants", hold = True)
		else: #TODO: Add prize for challenge winner
			if skill > 1:
				skill -= 1
				self.fish.set_skill_level(skill)
				db.set_level(skill)
			self.update_info(text = "Twitch chat lost", hold = True)
		
		total_voted.set(set())
			
		self.board.reset()
		self.update_plot(init = True)
		self.is_white = not self.is_white
		self.update_history(reset=True)
		self.custom_init()
		if not self.is_white:
			self.evaluate_position()
			c = custom_game.value
			if not c is None and "challenger" in c:
				self.set_legal_moves()
			else:
				self.fish_move()
		else:
			self.set_legal_moves()
		self.counting = False
		self.evaluate_position()
		
		Clock.schedule_once(self.end_game_, 4)
	
	def custom_init(self):
		c = db.new_game()
		if c is None:
			custom_game.set(None)
		# 1 v many
		if not c is None and "challenger" in c:
			c["turn"] = not self.is_white
		
		# custom board
		
		# custom mode
		custom_game.set(c)
	
	def end_game_(self, dt):
		self.update_board()
	
	def log(self, result, level, voters):
		self.round += 1
		
		if self.is_white:
			self.game_history.headers["White"] = ", ".join(voters)
		else:
			self.game_history.headers["Black"] = ", ".join(voters)
		
		if result == "d":
			self.game_history.headers["Result"] = "1/2-1/2"
		elif result == "w":
			if self.is_white:
				self.game_history.headers["Result"] = "1-0"
			else:
				self.game_history.headers["Result"] = "0-1"
		else:
			if self.is_white:
				self.game_history.headers["Result"] = "0-1"
			else:
				self.game_history.headers["Result"] = "1-0"
		
		db.game_end(result, level, len(voters), str(self.game_history))
		self.record = db.get_record()
			
	def set_legal_moves(self):
		moves.clear()
		notation_moves_temp = {}
		for move in self.board.legal_moves:
			temp = set()
			san = self.board.san(move.from_uci(move.uci())).replace("+", "").replace("#","")
			if san in moves:
				for i in notation_moves_temp:
					try:
						notation_moves_temp[i].remove(san)
						moves.pop(san)
					except:
						pass
			temp.add(move.uci())
			temp.add(san.casefold())
			temp.add(san)
			remove = []
			for i in temp:
				if not i in moves:
					moves[i] = 0
				else:
					remove.append(i)
			for i in remove:
				temp.remove(i)
			notation_moves_temp[self.board.san(move.from_uci(move.uci())).replace("+", "").replace("#","")] = temp
		moves["resign"] = 0
		notation_moves_temp["resign"] = ["resign"]
		moves["draw"] = 0
		notation_moves_temp["draw"] = ["draw"]
		self.moves_string = self.format_text("Legal moves, type in chat to vote. UCI ok, eg. a2a4:\n" + ", ".join(notation_moves_temp))
		self.move_options.text = self.moves_string
		voted.set(set())
		notation_moves.set(notation_moves_temp)
		
	def tally_count(self, val):
		return val[1]
	
	def tally(self, dt):
		data = []
		if len(voted.value) == 0:
			return
		
		c = custom_game.value
		if not c is None and "challenger" in c and c["turn"] and not self.counting:
			self.counting = True
			self.player_move(0)
			return
		
		notation_moves_list = notation_moves.value
		for move in notation_moves_list:
			temp = 0
			for i in notation_moves_list[move]:
				temp += moves[i]
			data.append((move, temp))
		
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
		
		if not self.counting:
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
	await bot.handle_commands(ctx)
	if ctx.author.name == "twitch_plays_chess_":
		return
	if len(ctx.content) > 10:
		return
	
	# Challenger voting
	c = custom_game.value
	if not c is None and "challenger" in c and ctx.author.name == c["challenger"]:
		if c["turn"]:
			votes = voted.value
			processed = ctx.content.replace("+", "").replace("#","").casefold()
			if processed in moves and not (ctx.author.name in votes):
				ws = bot._ws
				
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s has gone with move %s." % (c["challenger"], processed))
				
				if ctx.content in moves:
					moves[ctx.content] += 1
				else:
					moves[processed] += 1
				db.change_points(ctx.author.name, 1)
				votes.add(ctx.author.name)
				voted.set(votes)
		return

	# Add move to tally if valid
	votes = voted.value
	processed = ctx.content.replace("+", "").replace("#","").casefold()
	if processed in moves and not (ctx.author.name in votes):
		ws = bot._ws
		if processed == "resign":
			if not db.change_points(ctx.author.name, -5):
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you need 5 points to resign" % ctx.author.name)
				return
		
		if len(votes) == 0:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me The first vote has been cast, a move will be made in 15 seconds")
		
		if ctx.content in moves:
			moves[ctx.content] += db.get_player_level(ctx.author.name)
		else:
			moves[processed] += db.get_player_level(ctx.author.name)
		db.change_points(ctx.author.name, 1)
		votes.add(ctx.author.name)
		voted.set(votes)
		t = total_voted.value
		t.add(ctx.author.name)
		total_voted.set(t)

@bot.command(name="notation")
async def command_notation(ctx):
	ws = bot._ws
	await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Guide to voting move notation https://cheatography.com/davechild/cheat-sheets/chess-algebraic-notation/. You can also type your moves as the starting square followed by the ending square, eg. a4a6, b1d3")

@bot.command(name="points")
async def command_points(ctx):
	ws = bot._ws
	params = get_params(ctx.content)
	if len(params) > 0:
		name = process_name(params[0])
		points = db.get_points(name, no_create = True)
		if points is None:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Invalid username given.")
		else:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s has %s points." % (name, points))
	else:
		await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you have %s points." % (ctx.author.name, db.get_points(ctx.author.name)))

@bot.command(name="pgn")
async def command_pgn(ctx):
	ws = bot._ws
	params = get_params(ctx.content)
	if len(params) > 0:
		for line in wrap(db.get_game(get_params(ctx.content)[0]), 490):
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s" % line)
	else:
		# TODO: Line wrap this one too
		await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s" % history.value)

@bot.command(name="gamble")
async def command_gamble(ctx):
	ws = bot._ws
	params = get_params(ctx.content)
	if len(params) > 0:
		if params[0] == "all":
			delta = db.get_points(ctx.author.name)
		else:
			try:
				delta = int(params[0])
			except:
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me You must choose a number to gamble")
				return
		
		if delta < 69:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Minimum gamble amount is 69")
			return
		
		if db.change_points(ctx.author.name, -delta):
			if random.choice([True, False]):
				db.change_points(ctx.author.name, delta * 2)
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me PogChamp %s wagered %d points and won, now they have %d points PogChamp" % (ctx.author.name, delta, db.get_points(ctx.author.name)))
			else:
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me BibleThump %s wagered %d points and lost, now they have %d points BibleThump" % (ctx.author.name, delta, db.get_points(ctx.author.name)))
		else:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you only have %d points." % (ctx.author.name, db.get_points(ctx.author.name)))
			
	else:
		await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me You must choose a number to gamble")

@bot.command(name="buy")
async def command_buy(ctx):
	# Make flexible, add more
	ws = bot._ws
	params = get_params(ctx.content)
	if params[0] == "level":
		cur = db.get_player_level(ctx.author.name)
		cost = 500 * pow(10, cur)
		if db.change_points(ctx.author.name, -cost):
			db.level_up(ctx.author.name)
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s is now level %d! PogChamp" % (ctx.author.name, cur + 1))
		else:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you only have %d points, the next level costs %d." % (ctx.author.name, db.get_points(ctx.author.name), cost))
	elif params[0] == "vip":
		pass
	elif params[0] == "difficulty":
		pass
	elif params[0] == "challenge":
		# TODO: Add existence check
		if db.change_points(ctx.author.name, -100000):
			db.add_game_param("challenger", ctx.author.name)
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s will fight the rest of twitch chat next game. Bring it!" % ctx.author.name)
		else:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s, you only have %d points, a challenge costs 100000." % (ctx.author.name, db.get_points(ctx.author.name)))

@bot.command(name="song")
async def command_song(ctx):
	ws = bot._ws
	await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Music courtesy of Chilled Cow: https://www.youtube.com/c/chilledcow")
	
@bot.command(name="pgnplay")
async def command_pgnplay(ctx):
	ws = bot._ws
	await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Analysis board for viewing PGNs here: https://www.chess.com/analysis")

#!duel

#!give
@bot.command(name="give")
async def command_give(ctx):
	ws = bot._ws
	params = get_params(ctx.content)
	if len(params) > 1:
		name = process_name(params[0])
		try:
			amount = int(params[1])
		except:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Invalid number given.")
		points = db.get_points(name, no_create = True)
		if points is None:
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me Invalid username given.")
		else:
			if db.change_points(ctx.author.name, -amount):
				db.change_points(name, amount)
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me %s now has %s points." % (name, db.get_points(name)))
			else:
				await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me You don't have that many points to give DansGame")
	
class chessApp(App):
	def build(self):
		return main()

if __name__ == '__main__':
	m = Manager()
	moves = m.dict()
	notation_moves = m.Value(dict, {})
	voted = m.Value(set, set())
	total_voted = m.Value(set, set())
	history = m.Value(str, "")
	custom_game = m.Value(dict, None)
	p1 = Process(target=bot.run)
	p2 = Process(target=chessApp().run)
	p1.start()
	p2.start()
	p1.join()
	p2.join()
