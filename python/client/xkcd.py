import sys
import discord
import logging
import asyncio
import json
import random

PATH = dict ()
if (sys.argv [1]):
    try:
        with open (sys.argv [1]) as path_file:
            PATH = json.load (path_file)
    except:
        print ('Unable to open file: {}'.format (sys.argv [1]))
        exit (2)
else:
    print ('Usage python xkcd.py /path/to/path.json')
    exit (1)


sys.path.insert (0, PATH['lib'])
import client_helpers as CLIENT
from collection import Collection

JSON = PATH['json']

# It's not too much of an issue if it's not there; it will be created.
# We hope the base db with the imported blacklist exists, though.
db = Collection(JSON + 'collection.sqlite')

# Yep you should rename your config.json and append priv to it
# This way you won't add even more private stuff on github
CONFIG = JSON + "xkcd.config.json.priv"

# This is displayed to the channel if requests need comics but
# the collection is empty.
EMPTY_COLLECTION_MSG = "My collection is empty :("

logging.basicConfig (level = logging.INFO)

wame_config = CLIENT.loadJson (CONFIG)

wame_help = discord.Embed \
        (title = wame_config['help']['title'], \
        colour = discord.Colour(0x123654), \
        url = wame_config['help']['url'], \
        description = wame_config['help']['description'])
wame_help.set_footer (text = wame_config['help']['footer'], \
        icon_url = wame_config['help']['icon_url'])

Wame = discord.Client ()
wgame = discord.Game (name = wame_config['game'])

@Wame.event
async def on_ready ():
    await Wame.change_presence (game = wgame)
    bug_channel = Wame.get_channel (wame_config['report_channel'])
    CLIENT.greet (Wame, channel = bug_channel)

@Wame.event
async def on_message (message):
    if not message.content.startswith (wame_config['prefix']):
        pass
    else:
        args = await CLIENT.parse_args (message.content, wame_config['prefix'])
        command = args[0]
        args = args[1:]
        logging.info ('\nFull mess: {}\nCommand  : {}\nArgs     : {}'\
                .format (message.content, command, args))

        if command == 'xkcd':
            tmp = await Wame.send_message (message.channel, 'Searching...')

            if len (args) is 0:
                # TODO: Create function for random comic -> embed process.
                # This process is repeated a few times here; replace it with
                # a function call.

                comic = db.get_random()
                if comic is None:
                    await Wame.edit_message(tmp, EMPTY_COLLECTION_MSG)
                else:
                    embed_comic = await CLIENT.create_embed(comic)
                    await Wame.edit_message (tmp, ' ', embed = embed_comic)
            else:
                comic = await CLIENT.search (' '.join(args), db)
                # 0 == comic found
                if comic[0] == 0:
                    # Create embed
                    embed_comic = await CLIENT.create_embed (comic[1])
                    await Wame.edit_message (tmp, ' ', embed = embed_comic)
                else:
                    # It hasn't been found, too bad
                    not_found = discord.Embed (description =
                        "_I found nothing. I'm so sawry and sad :(_. \
                    \nReply with **`random`** for a surprise\n", \
                    colour = (0x000000))
                    await Wame.edit_message (tmp, " ", embed = not_found)
                    msg = await Wame.wait_for_message \
                            (author = message.author, \
                            content = "random", timeout = 20)
                    if (msg):
                        comic = db.get_random()
                        if comic is None:
                            await Wame.edit_message(tmp, EMPTY_COLLECTION_MSG)
                        else:
                            embed_comic = await CLIENT.create_embed(comic)
                            await Wame.send_message(message.channel, embed = embed_comic)
                    else:
                        await Wame.edit_message (tmp, "Timeout")

        elif command == 'random':
            comic = db.get_random()
            if comic is None:
                await Wame.send_message(message.channel, EMPTY_COLLECTION_MSG)
            else:
                embed_comic = await CLIENT.create_embed(comic)
                await Wame.send_message(message.channel, embed=embed_comic)

        elif command == 'latest':
            # TODO: Check xkcd for a newer comic than what is kept locally.
            latest_local_comic = db.get_latest()
            print(latest_local_comic['img_url'])
            if latest_local_comic is not None:
                embed_comic = await CLIENT.create_embed (latest_local_comic)
                await Wame.send_message (message.channel, embed = embed_comic)
            else:
                await Wame.send_message(message.channel, EMPTY_COLLECTION_MSG)

        elif command == 'report':
            bug_channel = Wame.get_channel (wame_config['report_channel'])
            embed_report = await CLIENT.report_embed (message, \
                    {'type': 'User', 'color': (0xff0000), 'client': Wame})
            report = await Wame.send_message (bug_channel, embed = embed_report)
            await Wame.pin_message (report)

        elif command == 'help':
            await Wame.send_message (message.channel, \
                    embed = wame_help)

Wame.run (wame_config['token'])
