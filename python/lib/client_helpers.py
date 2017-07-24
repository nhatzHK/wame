import asyncio
import json
import random
import discord
from collection import Collection
from urllib.request import urlopen

def is_someone (msg):
    return True

# Delete all messages in channel
async def purge (msg, wame):
    deleted = await wame.purge_from \
            (msg.channel, limit = 1000, check = is_someone)
    await wame.send_message \
            (msg.channel, 'Deleted {} message(s)'.format (len (deleted)))

# Load the content of a json file
# The return value isn't necessar a dictionary
# f is the file name (same dir or absolute path)
def loadJson (f):
    a = dict ()
    with open (f) as infile:
        a = json.load (infile)
    return a

# Notify a successful connection in the terminal
def greet (wame, channel = None):
    a = ""
    for i in wame.servers:
        a += "\n\t        : @" + i.name
    print ("Logged in as: " + \
            "\n\tName\t: " + wame.user.name +\
            "\n\tServers : " + str (len (wame.servers)) +\
            a +\
            "\n\tID  \t: " + wame.user.id +\
            "\n\tBug \t: " + channel.name + "@" + channel.server.name +\
            "\n")
    wame.change_presence (game = 'with Nerds')

# Ask the user to type a tring a number of times
# Felicitate when it's done
async def challenge (msg, wame):
    chal = "Wame is awesome"
    it = 4
    await wame.send_message (msg.channel, 'Type {} {} times.'.format (chal, it))
    for i in range (4):
        msg = await wame.wait_for_message (author = msg.author, content = chal)
        fmt = '{} left to go...'
        await wame.send_message (msg.channel, fmt.format (it - i -1))

    await wame.send_message (msg.channel, \
            'Not so dumb, heh?\nI mean great job wumpus!')

# Stop sending messages for a given time
async def pause (msg, wame):
    t = 5
    await asyncio.sleep (10)
    await wame.send_message (msg.channel, 'Came back, has the Jedi!')

# Count the number of messages a user has in a channel
async def count (msg, wame):
    counter = 0
    tmp = await wame.send_message (msg.channel, 'Calculating messages...')
    logs = wame.logs_from (msg.channel, limit = 10000)
    async for log in logs:
        if log.author == msg.author:
            counter += 1

    await wame.edit_message (tmp, 'You have {} messages.'.format (counter))

# Delete roles
async def clean (msg, wame):
    to_del = 'new role'
    rol = msg.server.roles
    count = len (rol)
    nr = [x for x in rol if x.name == to_del]
    to_del_count = len (nr)
    await wame.send_message \
            (msg.channel, 'Role count: {}\nTo delete: {}'.format \
            (count, to_del_count))
    for r in nr:
        await wame.delete_role (msg.server, r)
    await wame.send_message \
            (msg.channel, 'New role count: {}'.format (len (msg.server.roles)))

# Parse a string to extract the command and the arguments
# msg = "<prefix>command arg1 arg2 arg3 ..."
# return = [command, arg1, arg2, arg3, ...]
# NOTE: A prefix of length to is assumed
async def parse_args (msg, prefix):
    args = msg.split (' ')
    args[0] = args[0][len(prefix):]
    args = [a for a in args if a] # Take a wild guess: you missed. Try harder.
    return args

# TODO: Determine effectiveness for direct title search.
# get_xkcd may not provide the best result if they already know
# the comic title in advance.

# Retrieve the comic that best matches the phrase.
# "Best" is defined as the one with contents most similar to
# the words in the phrase list.
async def get_xkcd (phrase, db):
    if len (phrase) == 1 and phrase [0].isdigit ():
        if int(phrase[0]) <= db.get_latest()['number']:
            comic = db.get_comic(int(phrase[0]))
            return {'status': -1 if comic is None else 0, 'comic': comic}
        else:
            online_check = await get_online_xkcd(number = phrase[0])
            if online_check['status'] is 0:
                return online_check

    comic = db.get_from_phrase(phrase)
    return {'status': -1 if comic is None else 0, 'comic': comic}

# Clean up the query then call get_xkcd
async def search (q, db):
    import xkcd_helpers as XKCD
    query = XKCD.removePunk (q)
    qlist = list (set (query.split (' ')))
    qlist = [x for x in qlist if x and not (x == ' ')]
    return await get_xkcd (qlist, db)

async def create_embed (comic):
    #FIXME: Issue #11 
    if 'url' in list (comic.keys()):
        img_url = comic['img_url']
        img_url = "https://" + img_url
    else:
        img_url = comic['img_url']
    
    if 'number' in list (comic.keys ()):
        comic_number = comic['number']
    else:
        comic_number = comic['num']

    embed_comic = discord.Embed \
            (title = '{}: {}'.format (comic_number, comic['title']), \
            colour = discord.Colour(0x00ff00),
            url = comic['img_url'])

    embed_comic.set_footer (text = '{}'.format (comic['alt']))
    embed_comic.set_image (url = comic['img_url'])
    embed_comic.set_author (name = 'xkcd', url = 'https://xkcd.com/{}/'.format(comic['number']))

    return embed_comic

#FIXME: This is some kind of a special madness, I don't remember having
#coded while drunk
async def report_embed (msg, report):
    t = 'Report -> {}'.format (report['type'])
    c = report['color']

    d = '\n**Context**\nServer -> {}\nChannel -> {}\nUser -> {}\nTime -> {}\
            \n**Client**: \n\tName: -> {}\n\tId -> {}\n' \
            .format (msg.server, msg.channel, msg.author, msg.timestamp, \
            report['client'].user.name, report['client'].user.id)
    d+= '**Message**\n{}\n'.format (msg.content)
    if report['type'] is 'internal':
        d += '\n\n**Internal**{}'.format (report['internal_report'])

    embed_report = discord.Embed (title = t, description = d, colour = c)

    return embed_report

async def get_online_xkcd(number = 0):
    if number is 0:
        url ='https://xkcd.com/info.0.json'
    else:
        url = 'https://xkcd.com/{}/info.0.json'.format (number)

    response = {'status': 0, 'comic': ""}
    
    try:
        online_comic = urlopen(url).read()
        if type(online_comic) is bytes:
            online_comic = online_comic.decode('utf-8')

        # TODO: Use one key name for all comic image URLs.
        # This will probably fix itself when a Comic class is created.
        comic = json.loads(online_comic)
        response['comic'] = {
            'number': comic['num'],
            'img_url': comic['img'],  # The reason this is necessary
            'title': comic['title'],
            'alt': comic['alt'],
            'transcript': comic['transcript']
        }
    except:
        response['status'] = -1

    return response
