from twitchio.ext import commands
import configparser

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
		
	if ctx.content in moves and not (ctx.author.name in votes):
		if len(votes) == 0:		
			ws = bot._ws
			await ws.send_privmsg(secrets['DEFAULT']['channel'], f"/me The first vote has been cast, a move will be made in 15 seconds")
		
		moves[ctx.content] += 1
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
