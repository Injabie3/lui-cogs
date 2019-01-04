"""Ranks cog.
Keep track of active members on the server.
"""

import logging
import os
import random
import MySQLdb # The use of MySQL is debatable, but will use it to incorporate CMPT 354 stuff.
import discord
from discord.ext import commands
from __main__ import send_cmd_help # pylint: disable=no-name-in-module
from .utils.dataIO import dataIO # pylint: disable=relative-beyond-top-level

# Requires checks utility from:
# https://github.com/Rapptz/RoboDanny/tree/master/cogs/utils
from .utils import checks # pylint: disable=relative-beyond-top-level

# Global variables
LOGGER = None
SAVE_FOLDER = "data/lui-cogs/ranks/" # Path to save folder.

def checkFolder():
    """Used to create the data folder at first startup"""
    if not os.path.exists(SAVE_FOLDER):
        print("Creating " + SAVE_FOLDER + " folder...")
        os.makedirs(SAVE_FOLDER)

def checkFiles():
    """Used to initialize an empty JSON settings database at first startup"""
    base = {}

    theFile = SAVE_FOLDER + "settings.json"
    if not dataIO.is_valid_json(theFile):
        print("Creating default ranks settings.json...")
        dataIO.save_json(theFile, base)

    theFile = SAVE_FOLDER + "lastspoke.json"
    if not dataIO.is_valid_json(theFile):
        print("Creating default ranks lastspoke.json...")
        dataIO.save_json(theFile, base)

class Ranks:
    """Mee6-inspired guild rank management system.
    Not optimized for multi-guild deployments.
    """

    # Class constructor
    def __init__(self, bot):
        self.bot = bot
        checkFolder()
        checkFiles()
        self.settings = dataIO.load_json(SAVE_FOLDER + 'settings.json')
        self.lastspoke = dataIO.load_json(SAVE_FOLDER + 'lastspoke.json')

    ############
    # COMMANDS #
    ############

    # [p]levels
    @commands.command(name="levels", pass_context=True, no_pm=True)
    async def _ranksLevels(self, ctx):
        """Show the server ranking leaderboard"""
        # Execute a MySQL query to order and check.

        database = MySQLdb.connect(host=self.settings["mysql_host"],
                                   user=self.settings["mysql_username"],
                                   passwd=self.settings["mysql_password"])
        cursor = database.cursor()
        cursor.execute("SELECT userid, xp FROM renbot.xp WHERE guildid = {0} "
                       "order by xp desc limit 20".format(ctx.message.server.id))

        msg = ":information_source: **Ranks - Leaderboard (WIP)**\n```"

        rank = 1
        for row in cursor.fetchall():
            # row[0]: userID
            # row[1]: xp
            userID = row[0]
            userObject = ctx.message.server.get_member(str(userID))
            exp = row[1]

            # Lookup the ID against the guild
            if userObject is None:
                continue

            msg += str(rank).ljust(3)
            msg += (str(userObject.display_name) + " ").ljust(23)
            msg += str(exp).rjust(10) + "\n"

            rank += 1
            if rank == 11:
                break

        msg += "```\n Full rankings at https://ren.injabie3.moe/ranks/"
        await self.bot.say(msg)
        cursor.close()
        database.close()

    # [p]rank
    @commands.command(name="rank", pass_context=True, no_pm=True)
    async def _ranksCheck(self, ctx, ofUser: discord.Member = None): \
        # pylint: disable=too-many-locals
        """Check your rank in the server."""
        if ofUser is None:
            ofUser = ctx.message.author

        # Execute a MySQL query to order and check.
        database = MySQLdb.connect(host=self.settings["mysql_host"],
                                   user=self.settings["mysql_username"],
                                   passwd=self.settings["mysql_password"])
        cursor = database.cursor()

        # Using query code from:
        # https://stackoverflow.com/questions/13566695/select-increment-counter-in-mysql
        # This code is now included in the stored procedure in the database.

        cursor.execute("CALL renbot.getUserInfo({0},{1})".format(
            ctx.message.server.id, ofUser.id))
        embed = discord.Embed()
        data = cursor.fetchone() # Data from the database.

        try:
            LOGGER.info(data)
            rank = data[0]
            userID = data[1]
            level = data[2]
            levelXP = data[3]
            currentXP = data[4]
            totalXP = data[5]
            currentLevelXP = currentXP - totalXP
        except IndexError as error:
            await self.bot.say("Something went wrong when checking your level.  "
                               "Please notify the admin!")
            LOGGER.error(error)
            database.close()
            return


        userObject = ctx.message.server.get_member(str(userID))

        embed.set_author(name=userObject.display_name,
                         icon_url=userObject.avatar_url)
        embed.colour = discord.Colour.red()
        embed.add_field(name="Rank", value=int(rank))
        embed.add_field(name="Level", value=level)
        embed.add_field(name="Exp.", value="{0}/{1} (total {2})".format(
            currentLevelXP, levelXP, currentXP))
        embed.set_footer(text="Note: This EXP is different from Mee6.")

        await self.bot.say(embed=embed)
        database.close()

    @commands.group(name="ranks", pass_context=True, no_pm=True)
    async def _ranks(self, ctx):
        """Mee6-inspired guild rank management system. WIP"""
        # Display the help context menu
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    #######################
    # COMMANDS - SETTINGS #
    #######################
    #Ideally would be nice have this replaced by a web admin panel.

    # [p]ranks settings
    @_ranks.group(name="settings", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _settings(self, ctx):
        """Ranking system settings.  Only server admins should see this."""
        if str(ctx.invoked_subcommand).lower() == "ranks settings":
            await send_cmd_help(ctx)

    # [p]ranks settings default
    @_settings.command(name="default", pass_context=True, no_pm=True)
    async def _settingsDefault(self, ctx):
        """Set default for max points and cooldown."""
        sid = ctx.message.server.id

        self.settings[sid] = {}
        self.settings[sid]["cooldown"] = 0
        self.settings[sid]["maxPoints"] = 25

        await self.bot.say(":information_source: **Ranks - Default:** Defaults set, run "
                           "`{}rank settings show` to verify the settings.".format(ctx.prefix))

    # [p]ranks settings show
    @_settings.command(name="show", pass_context=True, no_pm=True)
    async def _settingsShow(self, ctx):
        """Show current settings."""
        sid = ctx.message.server.id

        try:
            cooldown = self.settings[sid]["cooldown"]
            maxPoints = self.settings[sid]["maxPoints"]
        except KeyError:
            # Not set.
            await self.bot.say(":warning: **Ranks - Current Settings**: The server is "
                               "not configured!  Please run `{}rank settings default` "
                               "first and try again.".format(ctx.prefix))
            return
        msg = ":information_source: **Ranks - Current Settings**:\n```"
        msg += "Cooldown time:  {0} seconds.\n".format(cooldown)
        msg += "Maximum points: {0} points per eligible message```".format(maxPoints)

        await self.bot.say(msg)

    # [p]rank settings cooldown
    @_settings.command(name="cooldown", pass_context=True)
    async def _settingsCooldown(self, ctx, seconds: int):
        """Set the cooldown required between XP gains (in seconds)"""
        sid = ctx.message.server.id

        if seconds is None:
            await self.bot.say(":negative_squared_cross_mark: **Ranks - Cooldown**: "
                               "Please enter a time in seconds!")
            return

        if seconds < 0:
            await self.bot.say(":negative_squared_cross_mark: **Ranks - Cooldown**: "
                               "Please enter a valid time in seconds!")
            return

        # Save settings
        self.settings = dataIO.load_json(SAVE_FOLDER + 'settings.json')

        # Make sure the server id key exists.
        if sid not in self.settings.keys():
            self.settings[sid] = {}

        self.settings[sid]["cooldown"] = seconds
        dataIO.save_json(SAVE_FOLDER + 'settings.json', self.settings)

        await self.bot.say(":white_check_mark: **Ranks - Cooldown**: Set to {0} "
                           "seconds.".format(seconds))
        LOGGER.info("Cooldown changed by %s#%s (%s)",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id)
        LOGGER.info("Cooldown set to %s seconds",
                    seconds)

    #[p]rank settings maxpoints
    @_settings.command(name="maxpoints", pass_context=True)
    async def _settingsMaxpoints(self, ctx, maxpoints: int = 25):
        """Set max points per eligible message.  Defaults to 25 points."""
        sid = ctx.message.server.id

        if maxpoints < 0:
            await self.bot.say(":negative_squared_cross_mark: **Ranks - Max Points**: "
                               "Please enter a positive number.")
            return

        # Save settings
        self.settings = dataIO.load_json(SAVE_FOLDER + 'settings.json')
        # Make sure the server id key exists.
        if sid not in self.settings.keys():
            self.settings[sid] = {}
        self.settings[sid]["maxPoints"] = maxpoints
        dataIO.save_json(SAVE_FOLDER + 'settings.json', self.settings)

        await self.bot.say(":white_check_mark: **Ranks - Max Points**: Users can gain "
                           "up to {0} points per eligible message.".format(maxpoints))
        LOGGER.info("Maximum points changed by %s#%s (%s)",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id)
        LOGGER.info("Maximum points per message set to %s.",
                    maxpoints)

    #[p]rank settings dbsetup
    @_settings.command(name="dbsetup", pass_context=True)
    @checks.serverowner()
    async def _settingsDbSetup(self, ctx):
        """Perform database set up. DO NOT USE if ranks is working."""
        await self.bot.say("MySQL Set up:\n"
                           "What is the host you wish to connect to?")
        host = await self.bot.wait_for_message(timeout=30,
                                               author=ctx.message.author,
                                               channel=ctx.message.channel)

        if host is None:
            await self.bot.say("No response received, not setting anything!")
            return

        await self.bot.say("What is the username you want to use to connect?")
        username = await self.bot.wait_for_message(timeout=30,
                                                   author=ctx.message.author,
                                                   channel=ctx.message.channel)

        if username is None:
            await self.bot.say("No response received, not setting anything!")
            return

        await self.bot.say("What is the password you want to use to connect?  You "
                           "can use a dummy password and manually change it in the "
                           "JSON config later.")
        password = await self.bot.wait_for_message(timeout=30,
                                                   author=ctx.message.author,
                                                   channel=ctx.message.channel)

        if password is None:
            await self.bot.say("No response received, not setting anything!")
            return

        # Save settings
        self.settings = dataIO.load_json(SAVE_FOLDER + 'settings.json')
        self.settings["mysql_host"] = host.content
        self.settings["mysql_username"] = username.content
        self.settings["mysql_password"] = password.content
        dataIO.save_json(SAVE_FOLDER + 'settings.json', self.settings)

        await self.bot.say("Settings saved.")
        LOGGER.info("Database connection changed by %s#%s (%s)",
                    ctx.message.author.name,
                    ctx.message.author.discriminator,
                    ctx.message.author.id)

    ####################
    # HELPER FUNCTIONS #
    ####################

    def addPoints(self, guildID, userID):
        """Add rank points between 0 and MAX_POINTS to the user"""
        try:
            pointsToAdd = random.randint(0, self.settings[guildID]["maxPoints"])
        except KeyError:
            # Most likely key error, use default 25.
            pointsToAdd = random.randint(0, 25)

        database = MySQLdb.connect(host=self.settings["mysql_host"],
                                   user=self.settings["mysql_username"],
                                   passwd=self.settings["mysql_password"])
        cursor = database.cursor()
        fetch = cursor.execute("SELECT xp from renbot.xp WHERE userid = {0} and "
                               "guildid = {1}".format(userID, guildID))

        currentXP = 0

        if fetch != 0: # This user has past XP that we can add to.
            result = cursor.fetchall()
            currentXP = result[0][0] + pointsToAdd
        else: # New user
            currentXP = pointsToAdd

        cursor.execute("REPLACE INTO renbot.xp (userid, guildid, xp) VALUES ({0}, "
                       "{1}, {2})".format(userID, guildID, currentXP))
        database.commit()
        cursor.close()
        database.close()

    async def checkFlood(self, message):
        """Check to see if the user is sending messages that are flooding the server.
        If yes, then do not add points.
        """
        # Decide whether to store last spoken user data in:
        #  - MySQL
        #  - JSON
        #  - or leave in RAM.
        # Check as follows:
        #  - Get the user ID and message time
        #  - Check the last message time that was used to add points to the current
        #    user.
        #  - If this time does not exceed COOLDOWN, return and do nothing.
        #  - If this time exceeds COOLDOWN, update the last spoken time of this user
        #    with the message time.
        #  - Add points between 0 and MAX_POINTS (use random).
        #  - Return.

        timestamp = message.timestamp.timestamp()

        if message.author.bot:
            return

        if message.channel.is_private:
            return

        sid = message.server.id
        uid = message.author.id

        try:
            # If the time does not exceed COOLDOWN, return and do nothing.
            if timestamp - self.lastspoke[sid][uid]["timestamp"] <= self.settings[sid]["cooldown"]:
                return
            # Update last spoke time with new message time.
        except KeyError:
            # Most likely key error, so create the key, then update
            # last spoke time with new message time.
            try:
                self.lastspoke[sid][uid] = {}
            except KeyError:
                self.lastspoke[sid] = {}
                self.lastspoke[sid][uid] = {}
            LOGGER.error("%s#%s (%s) has not spoken since last restart, adding new "
                         "timestamp",
                         message.author.name,
                         message.author.discriminator,
                         uid)

        self.lastspoke[sid][uid]["timestamp"] = timestamp
        self.addPoints(message.server.id, message.author.id)

def setup(bot):
    """Add the cog to the bot"""
    global LOGGER # pylint: disable=global-statement
    checkFolder()   # Make sure the data folder exists!
    checkFiles()    # Make sure we have a local database!
    LOGGER = logging.getLogger("red.Ranks")
    if LOGGER.level == 0:
        # Prevents the LOGGER from being loaded again in case of module reload.
        LOGGER.setLevel(logging.INFO)
        handler = logging.FileHandler(filename=SAVE_FOLDER+"info.log",
                                      encoding="utf-8",
                                      mode="a")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s",
                                               datefmt="[%d/%m/%Y %H:%M:%S]"))
        LOGGER.addHandler(handler)
    rankingSystem = Ranks(bot)
    bot.add_cog(rankingSystem)
    bot.add_listener(rankingSystem.checkFlood, 'on_message')
