from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image as kiImage
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from stockfish import Stockfish
import chess
import render
import configparser
from kivy.clock import Clock
from matplotlib import pyplot
import numpy as np
from kivy.config import Config
Config.set('graphics', 'width', '1150')
Config.set('graphics', 'height', '600')


class main(BoxLayout):
	def __init__(self, **kwargs):
		super(main, self).__init__(**kwargs)
		global moves
		global voted
		self.size_hint_y = 1
		self.orientation = "vertical"
		self.countdown = 0
		self.counting = False
		self.hold_message_ticks = 0
		self.lastmove = None
		
		#init from file
		self.stats = configparser.ConfigParser()
		temp = open("game.log")
		self.stats.read_file(temp)
		
		self.layer1 = BoxLayout(orientation = "horizontal", size_hint_y = 0.7)
		self.add_widget(self.layer1)
		self.render = kiImage()
		self.layer1.add_widget(self.render)
		self.fish = Stockfish(parameters={"Minimum Thinking Time": 400, "Slow Mover": 80})
		self.board = chess.Board()
		self.renderer = render.DrawChessPosition()
		self.moves_string = ""
		self.board.set_fen(self.stats["GAME"]["board"])
		self.is_white = self.board.turn
		
		self.skill = float(self.stats["DEFAULT"]["level"])
		self.fish.set_skill_level(self.skill)
		self.fish.depth = "14"
		
		self.update_board()
		
		self.move_ranks = kiImage()
		self.layer1.add_widget(self.move_ranks)
		
		self.info_text = "Stockfish level: %d" % self.skill
		self.info = Label(text = self.info_text, size_hint_y = 0.2, size_hint_x = 1)
		self.move_options = Label(text = self.moves_string, size_hint_y = 0.2, size_hint_x = 1)
		self.set_legal_moves()
		self.info.text_size = (300, 60)
		self.move_options.text_size = (700, 80)
		self.add_widget(self.info)
		self.add_widget(self.move_options)
		
		self.countdown = False
		
		Clock.schedule_interval(self.tally, 2)
		Clock.schedule_interval(self.update_info, 1)
		
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
			self.info.text = self.info_text
		else:
			self.info.text = text
		
	def update_board(self):
		Clock.schedule_once(self._update_board)
	
	def _update_board(self, dt):
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
	
	def player_move(self, dt):
		pyplot.clf()
		highmove = None
		highvote = -1
		for move in moves.keys():
			if moves[move] > highvote:
				highmove = move
				highvote = moves[move]
		
		self.counting = False
		if highmove == "resign":
			self.end_game("l")
			return
		elif highmove == "draw":
			# Evaluate draw, has_insufficient_material()
			return
		else:
			self.board.push_san(highmove)
			self.update_board()
		
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
	
	def end_game(self, result):
		#TODO: logging, rank change, etc
		self.log(result)
		self.lastmove = None
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
			total_voted.set(set())
			
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
		
		self.board.reset()
		self.is_white = not self.is_white
		if not self.is_white:
			self.fish_move()
		self.set_legal_moves()
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
			moves[self.board.san(move.from_uci(move.uci()))] = 0
		moves["resign"] = 0
		#moves["draw"] = 0
		self.moves_string = "Legal moves, type in chat to vote (case sensitive):\n" + ", ".join(moves.keys())
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
		pyplot.bar(y, quantity, align='center', alpha=0.5)
		pyplot.xticks(y, labels)
		pyplot.ylim(ymin=0)
		pyplot.gca().axes.get_yaxis().set_visible(False)
		self.update_plot()
		
		if len(voted.get()) > 0 and not self.counting:
			Clock.schedule_once(self.player_move, 15)
			self.countdown = 15
			self.counting = True
			
class chessApp(App):

	def build(self):
		return main()
