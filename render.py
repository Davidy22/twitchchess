#! /usr/bin/env python
'''Code to draw chess board and pieces.

FEN notation to describe the arrangement of peices on a chess board.

White pieces are coded: K, Q, B, N, R, P, for king, queen, bishop,
rook knight, pawn. Black pieces use lowercase k, q, b, n, r, p. Blank
squares are noted with digits, and the "/" separates ranks.

As an example, the game starts at:

rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR

See: http://en.wikipedia.org/wiki/Forsyth-Edwards_Notation
'''
import re
from PIL import Image, ImageDraw, ImageFont

class BadChessboard(ValueError):
	pass
	
def expand_blanks(fen):
	'''Expand the digits in an FEN string into spaces
	
	>>> expand_blanks("rk4q3")
	'rk    q   '
	'''
	def expand(match):
		return ' ' * int(match.group(0))
	return re.compile(r'\d').sub(expand, fen)
	
def check_valid(expanded_fen):
	'''Asserts an expanded FEN string is valid'''
	match = re.compile(r'([KQBNRPkqbnrp ]{8}/){8}$').match
	if not match(expanded_fen + '/'):
		raise BadChessboard()
	
def expand_fen(fen):
	'''Preprocesses a fen string into an internal format.
	
	Each square on the chessboard is represented by a single 
	character in the output string. The rank separator characters
	are removed. Invalid inputs raise a BadChessboard error.
	'''
	expanded = expand_blanks(fen)
	#check_valid(expanded)
	return expanded.replace('/', '')
	
def draw_board(n=8, sq_size=(20, 20)):
	'''Return an image of a chessboard.
	
	The board has n x n squares each of the supplied size.'''
	from itertools import cycle
	def square(i, j):
		return i * (sq_size[0]+10), j * (sq_size[1] + 10)
	opaque_grey_background = 192, 255
	board = Image.new('LA', square(n, n), opaque_grey_background) 
	draw_square = ImageDraw.Draw(board).rectangle
	whites = ((square(i, j), square(i + 1, j + 1))
			  for i_start, j in zip(cycle((0, 1)), range(n))
			  for i in range(i_start, n, 2))
	for white_square in whites:
		draw_square(white_square, fill='white')
	return board
	
class DrawChessPosition(object):
	'''Chess position renderer.
	
	Create an instance of this class, then call 
	'''
	def __init__(self):
		'''Initialise, preloading pieces and creating a blank board.''' 
		self.n = 8
		self.create_pieces()
		self.create_blank_board()
	
	def create_pieces(self):
		'''Load the chess pieces from disk.
		
		Also extracts and caches the alpha masks for these pieces. 
		'''
		whites = 'KQBNRP'
		piece_images = dict(
			zip(whites, (Image.open('pieces/%s.png' % p) for p in whites)))
		blacks = 'kqbnrp'
		piece_images.update(dict(
			zip(blacks, (Image.open('pieces/%s.png' % p) for p in blacks))))
		piece_sizes = set(piece.size for piece in piece_images.values())
		# Sanity check: the pieces should all be the same size
		assert len(piece_sizes) == 1
		self.piece_w, self.piece_h = piece_sizes.pop()
		self.piece_images = piece_images
		self.piece_masks = dict((pc, img.split()[3]) for pc, img in
								 self.piece_images.items())
	
	def create_blank_board(self):
		'''Pre-render a blank board.'''
		self.board = draw_board(sq_size=(self.piece_w, self.piece_h))
	
	def point(self, i, j):
		'''Return the top left of the square at (i, j).'''
		w, h = self.piece_w, self.piece_h
		return i * (h + 10) + 5, j * (w + 10) + 5
		
	def bot(self, i, j):
		'''Return the bottom right of the square at (i, j).'''
		w, h = self.piece_w, self.piece_h
		return i * (h + 10) + 57, j * (w + 10) + 46
	
	def square(self, i, j):
		return i * (self.piece_w+10), j * (self.piece_h + 10)
	
	def draw(self, fen, white, lastmove = None):
		'''Return an image depicting the input position.
		
		fen - the first record of a FEN chess position.
		Clients are responsible for resizing this image and saving it,
		if required.
		'''
		board = self.board.copy()
		
		if white:
			letters = ["a","b","c","d","e","f","g","h"]
			numbers = ["8","7","6","5","4","3","2","1"]
		else:
			letters = ["h","g","f","e","d","c","b","a"]
			numbers = ["1","2","3","4","5","6","7","8"]
		
		if not lastmove is None:
			ImageDraw.Draw(board).rectangle(
			(self.square(letters.index(lastmove[0]), numbers.index(lastmove[1])),
			self.square(letters.index(lastmove[0]) + 1, numbers.index(lastmove[1]) + 1)), fill="gray")
			ImageDraw.Draw(board).rectangle((self.square(letters.index(lastmove[2]), numbers.index(lastmove[3])), self.square(letters.index(lastmove[2]) + 1, numbers.index(lastmove[3]) + 1)), fill="gray")
		
		pieces = expand_fen(fen)
		images, masks, n = self.piece_images, self.piece_masks, self.n
		if white:
			pts = (self.point(i, j) for j in range(n) for i in range(n))
		else:
			pts = (self.point(7-i, 7-j) for j in range(n) for i in range(n))
		def not_blank(pt_pc):
			return pt_pc[1] != ' '
		for pt, piece in filter(not_blank, zip(pts, pieces)):
			board.paste(images[piece], pt, masks[piece])
		
		fnt = ImageFont.truetype('/usr/share/fonts/truetype/freefont/FreeSansBold.ttf', 20)
		
		for i in range(n):
			ImageDraw.Draw(board).text(self.bot(i,7), letters[i], font=fnt, fill="black")
			ImageDraw.Draw(board).text(self.point(0,i), numbers[i], font=fnt, fill="black")
		return board
