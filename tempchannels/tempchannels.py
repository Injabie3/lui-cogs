"""Temporary channel cog.

Creates a temporary channel.
"""
import asyncio
import os
import json # Will need this to use in conjunction with aiohttp below.
import itertools
import aiohttp # Using this to build own request to Discord API for NSFW.
import discord
from discord.ext import commands
from cogs.utils import checks, config
from cogs.utils.dataIO import dataIO

KEY_SETTINGS = "settings"
SAVE_FOLDER = "data/lui-cogs/tempchannels/"
SAVE_FILE = "settings.json"

def checkFilesystem():
    if not os.path.exists(SAVE_FOLDER):
        print("Temporary Channels: Creating folder: {} ...".format(SAVE_FOLDER))
        os.makedirs(SAVE_FOLDER)

    if not os.path.exists(SAVE_FILE):
        # Build a default settings.json
        defaultDict = {}
        dataIO.save_json(SAVE_FOLDER+SAVE_FILE, defaultDict)
        print("Temporary Channels: Creating file: {} ...".format(SAVE_FILE))

class TempChannels:
    """Creates a temporary channel."""

    def __init__(self, bot):
        self.bot = bot
        self.config = config.Config("settings.json",
                                    cogname="lui-cogs/tempchannels")
        self.settings = self.config.get(KEY_SETTINGS)

    def _sync_settings(self):
        await self.config.put(KEY_SETTINGS, self.settings)
        self.settings = self.config.get(KEY_SETTINGS)

    @commands.group(name="tempchannels", pass_context=True, no_pm=True, aliases=["tc"])
    @checks.serverowner()
    async def _tempchannels(self, ctx):
        """
        Temporary text-channel creation (only 1 at the moment).
        """
        #Display the help context menu
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_tempchannels.command(name="default", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_default(self, ctx):
        """RUN FIRST: Sets default settings.
        - Start at 00:00.
        - Duration of channel is 1 minute.
        - The creation and deletion of TempChannel is disabled.
        - NSFW prompt will not appear.
        - TempChannel will not be role restricted.
        - If present, the previous TempChannel (if any) will be forgotten, and not deleted.
        """
        try:
            self.settings[ctx.message.server.id]
        except:
            self.settings[ctx.message.server.id] = {}

        self.settings[ctx.message.server.id]["channelName"] = "tempchannel"
        self.settings[ctx.message.server.id]["channelTopic"] = "Created with TempChannels cog."
        self.settings[ctx.message.server.id]["channelPosition"] = 0
        self.settings[ctx.message.server.id]["channelCreated"] = False
        self.settings[ctx.message.server.id]["durationHours"] = 0
        self.settings[ctx.message.server.id]["durationMinutes"] = 1
        self.settings[ctx.message.server.id]["startHour"] = 20
        self.settings[ctx.message.server.id]["startMinute"] = 0
        self.settings[ctx.message.server.id]["enabled"] = False
        self.settings[ctx.message.server.id]["nsfw"] = False
        self.settings[ctx.message.server.id]["roleallow"] = []
        self.settings[ctx.message.server.id]["roledeny"] = []
        self.settings[ctx.message.server.id]["channel"] = None

        self._sync_settings()
        await self.bot.say(":white_check_mark: TempChannel: Setting default settings.")

    @_tempchannels.command(name="show", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_show(self,ctx):
        """Show current settings."""
        self._sync_settings()
        try:
            msg  = ":information_source: TempChannel - Current Settings\n```"
            if self.settings[ctx.message.server.id]["enabled"]:
                msg += "Enabled?          Yes\n"
            else:
                msg += "Enabled?          No\n"
            if self.settings[ctx.message.server.id]["nsfw"]:
                msg += "NSFW Prompt:      Yes\n"
            else:
                msg += "NSFW Prompt:      No\n"
            if len(self.settings[ctx.message.server.id]["roleallow"]) == 0:
                msg += "Role Allow:       None\n"
            else:
                msg += "Role Allow:       {0}\n".format(self.settings[ctx.message.server.id]["roleallow"])
            if len(self.settings[ctx.message.server.id]["roledeny"]) == 0:
                msg += "Role Deny:        None\n"
            else:
                msg += "Role Deny:        {0}\n".format(self.settings[ctx.message.server.id]["roledeny"])
            msg += "Channel Name:     {0}\n".format(self.settings[ctx.message.server.id]["channelName"])
            msg += "Channel Topic:    {0}\n".format(self.settings[ctx.message.server.id]["channelTopic"])
            msg += "Creation Time:    {0:002d}:{1:002d}\n".format(self.settings[ctx.message.server.id]["startHour"],self.settings[ctx.message.server.id]["startMinute"])
            msg += "Duration:         {0}h {1}m\n".format(self.settings[ctx.message.server.id]["durationHours"],self.settings[ctx.message.server.id]["durationMinutes"])
            msg += "Channel Position: {0}\n".format(self.settings[ctx.message.server.id]["channelPosition"])
            if self.settings[ctx.message.server.id]["channelCategory"] == 0:
                msg += "Channel Category: None.```"
            else:
                msg += "Channel Category: ID {}```".format(self.settings[ctx.message.server.id]["channelCategory"])
            await self.bot.say(msg)
        except:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: Cannot display settings.  Please set default settings by typing `{}tempchannels default` first.".format(ctx.prefix))

    @_tempchannels.command(name="toggle", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_toggle(self, ctx):
        """Toggle the creation/deletion of the temporary channel."""
        try:
            if self.settings[ctx.message.server.id]["enabled"]:
                self.settings[ctx.message.server.id]["enabled"] = False
                set = False
            else:
                self.settings[ctx.message.server.id]["enabled"] = True
                set = True
        except: #Typically a KeyError
            self.settings[ctx.message.server.id]["enabled"] = True
            set = True
        self._sync_settings()
        if set:
            await self.bot.say(":white_check_mark: TempChannel: Enabled.")
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: Disabled.")

    @_tempchannels.command(name="nsfw", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_nsfw(self, ctx):
        """Toggle NSFW requirements"""
        try:
            if self.settings[ctx.message.server.id]["nsfw"]:
                self.settings[ctx.message.server.id]["nsfw"] = False
                set = False
            else:
                self.settings[ctx.message.server.id]["nsfw"] = True
                set = True
        except: #Typically a KeyError
            self.settings[ctx.message.server.id]["nsfw"] = True
            set = True
        self._sync_settings()
        if set:
            await self.bot.say(":white_check_mark: TempChannel: NSFW requirement enabled.")
        else:
            await self.bot.say(":negative_squared_cross_mark: TempChannel: NSFW requirement disabled.")

    @_tempchannels.command(name="setstart", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_setstart(self, ctx, hour: int, minute: int):
        """Set the temp channel creation time. Use 24 hour time."""
        if (hour > 23) or (hour < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Start Time: Please enter a valid time.")
            return
        if (minute > 59) or (minute < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Start Time: Please enter a valid time.")
            return

        self.settings[ctx.message.server.id]["startHour"] = hour
        self.settings[ctx.message.server.id]["startMinute"] = minute
        self._sync_settings()
        await self.bot.say(":white_check_mark: TempChannel - Start Time: Start time set to {0:002d}:{1:002d}.".format(hour,minute))

    @_tempchannels.command(name="setduration", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_setduration(self, ctx, hours: int, minutes: int):
        """
        Sets the duration of the temp channel.  Maximum 100 hours.
        hours:    # of hours to make this channel available, and
        minutes:  # of minutes to make this channel available.

        Example:
        If hours = 1, and minutes = 3, then the channel will be available for
        1 hour 3 minutes.
        """
        if (hours >= 100) or (hours < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Duration: Please enter valid hours!")
            return
        elif (minutes >= 60) or (minutes < 0):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Duration: Please enter valid minutes!")
            return
        elif (hours >= 99) and (minutes >= 60):
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Duration: Please enter a valid duration!")
            return

        self.settings[ctx.message.server.id]["durationHours"] = hours
        self.settings[ctx.message.server.id]["durationMinutes"] = minutes
        self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Duration: Duration set to **{0} hours, {1} minutes**.".format(hours, minutes))

    @_tempchannels.command(name="settopic", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_settopic(self, ctx, *, topic: str):
        """Sets the topic of the channel."""
        if len(topic) > 1024:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Topic: Topic is too long.  Try again.")
            return

        self.settings[ctx.message.server.id]["channelTopic"] = topic
        self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Topic: Topic set to:\n```{0}```".format(topic))

    @_tempchannels.command(name="setname", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_setname(self, ctx, name: str):
        """Sets the #name of the channel."""
        if len(name) > 25:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Name: Name is too long.  Try again.")
            return

        self.settings[ctx.message.server.id]["channelName"] = name
        self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Name: Channel name set to: ``{0}``".format(name))

    @_tempchannels.command(name="setposition", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_setposition(self, ctx, position: int):
        """Sets the position of the text channel in the list."""
        if position > 100 or position < 0:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Position: Invalid position.  Try again.")
            return

        self.settings[ctx.message.server.id]["channelPosition"] = position
        self._sync_settings()

        await self.bot.say(":white_check_mark: TempChannel - Position: This channel will be at position {0}".format(position))

    @_tempchannels.command(name="setcategory", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_setcategory(self, ctx, id: int):
        """
        Sets the parent category of the text channel (ID ONLY).

        Enter an ID to enable, enter 0 to disable.

        Since the library does not support categories yet, we will use IDs.
        To retreive an ID:
        - Turn on Developer Mode.
        - Right click the category.
        - Click "Copy ID"
        - Run this command with the ID.
        """
        if id < 0:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Category: Please enter a valid ID.")
            return

        self.settings[ctx.message.server.id]["channelCategory"] = id
        self._sync_settings()

        if id == 0:
            await self.bot.say(":white_check_mark: TempChannel - Category: Parent category disabled.")
        else:
            await self.bot.say(":white_check_mark: TempChannel - Category: Parent category set to ID `{}`.".format(id))

    @_tempchannels.command(name="allowadd", pass_context=True, no_pm=True, aliases=["aa"])
    @checks.serverowner()
    async def _tempchannels_allowadd(self, ctx, *, role: str):
        """
        Add role to allow access to the channel. No @mention.
        Do not @mention the role, just type the name of the role.

        Upon creation of channel, will check for role names, not IDs,
        so you must update this list if you change the role name!
        """
        if len(role) > 25: # This is arbitrary.
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role: Role name is too long.  Try again.")
            return

        # Validate the role.
        result = discord.utils.get(ctx.message.server.roles, name=role)

        if result is None:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Allow: **`{}`** not found!  Not set.".format(role))
        else:
            if role not in self.settings[ctx.message.server.id]["roleallow"]:
                self.settings[ctx.message.server.id]["roleallow"].append(role)
                await self.bot.say(":white_check_mark: TempChannel - Role Allow: **`{0}`** will be allowed access.".format(role))
            else:
                await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Allow: **`{0}`** is already allowed.".format(role))

    @_tempchannels.command(name="allowremove", pass_context=True, no_pm=True, aliases=["ar"])
    @checks.serverowner()
    async def _tempchannels_allowremove(self, ctx, *, role: str):
        """
        Remove role from access to the channel. No @mention.
        Do not @mention the role, just type the name of the role.
        """

        if len(self.settings[ctx.message.server.id]["roleallow"]) == 0 or role not in self.settings[ctx.message.server.id]["roleallow"]:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Allow: **`{0}`** wasn't on the list.".format(role))
            return
        else:
            self.settings[ctx.message.server.id]["roleallow"].remove(role)
            self._sync_settings()
            await self.bot.say(":white_check_mark: TempChannel - Role Allow: **`{0}`** removed from the list.".format(role))

    @_tempchannels.command(name="denyadd", pass_context=True, no_pm=True, aliases=["da"])
    @checks.serverowner()
    async def _tempchannels_denyadd(self, ctx, *, role: str):
        """
        Add role to block sending to the channel. No @mention.
        Do not @mention the role, just type the name of the role.

        Upon creation of channel, will check for role names, not IDs,
        so you must update this list if you change the role name!

        This role should be HIGHER in the role hierarchy than the roles in
        the allowed list!  The bot will not check for this.
        """
        if len(role) > 25: # This is arbitrary.
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role: Role name is too long.  Try again.")
            return

        # Validate the role.
        result = discord.utils.get(ctx.message.server.roles, name=role)

        if result is None:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Deny: **`{}`** not found!  Not set.".format(role))
        else:
            if role not in self.settings[ctx.message.server.id]["roledeny"]:
                self.settings[ctx.message.server.id]["roledeny"].append(role)
                await self.bot.say(":white_check_mark: TempChannel - Role: **`{0}`** will be denied message sending, provided this role is higher than any of the ones in the allowed list.".format(role))
            else:
                await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Deny: **`{0}`** is already denied.".format(role))

    @_tempchannels.command(name="denyremove", pass_context=True, no_pm=True, aliases=["dr"])
    @checks.serverowner()
    async def _tempchannels_denyremove(self, ctx, *, role: str):
        """
        Remove role from being blocked sending to the channel. No @mention.
        Do not @mention the role, just type the name of the role.
        """

        if len(self.settings[ctx.message.server.id]["roledeny"]) == 0 or role not in self.settings[ctx.message.server.id]["roledeny"]:
            await self.bot.say(":negative_squared_cross_mark: TempChannel - Role Deny: **`{0}`** wasn't on the list.".format(role))
            return
        else:
            self.settings[ctx.message.server.id]["roledeny"].remove(role)
            self._sync_settings()
            await self.bot.say(":white_check_mark: TempChannel - Role Deny: **`{0}`** removed from the list.".format(role))

    @_tempchannels.command(name="delete", pass_context=True, no_pm=True)
    @checks.serverowner()
    async def _tempchannels_delete(self, ctx):
        """Deletes the temp channel, if it exists."""
        if self.settings[ctx.message.server.id]["channelCreated"]:
            # Channel created, see when we should delete it.
            self._sync_settings()
            try:
                if self.settings[ctx.message.server.id]["channel"] is not None:
                    try:
                        await self.bot.delete_channel(self.bot.get_channel(self.settings[ctx.message.server.id]["channel"]))
                        self.settings[ctx.message.server.id]["channel"] = None
                    except Exception as e:
                        print("TempChannel: "+e)
                    await self.bot.say(":white_check_mark: TempChannel: Channel deleted")
                else:
                    await self.bot.say(":negative_squared_cross_mark: TempChannel: No temp channel to delete.")
            except:
                self.settings[ctx.message.server.id]["channel"] = None
                await self.bot.say(":negative_squared_cross_mark: No temp channel to delete.")
            print("TempChannel: Channel deleted at "+format(time.strftime("%H:%M:%S")))
            self.settings[ctx.message.server.id]["channelCreated"] = False
            self._sync_settings()

    ###################
    # Background Loop #
    ###################
    async def _check_channels(self):
        """Loop to check whether or not we should create/delete the TempChannel"""
        while self == self.bot.get_cog("TempChannels"):
            await asyncio.sleep(15)
            # Create/maintain the channel during a valid time and duration, else delete it.
            try:
                for server in self.settings:
                    keys_settings = self.settings[server].keys()
                    keys_required = [ "channelName", "channelPosition", "channelCategory", "channelTopic", "channelCreated", "startHour", "startMinute", "durationHours", "durationMinutes", "nsfw", "roleallow", "roledeny", "enabled"]
                    missing = False
                    for key in keys_required:
                        if key not in keys_settings:
                            missing = True
                            print("TempChannels: Key {} is missing in settings! Run [p]tc default.".format(key))
                    if missing:
                        continue

                    if not self.settings[server]["enabled"]:
                        continue

                    if ( int(time.strftime("%H")) == self.settings[server]["startHour"]) and (int(time.strftime("%M")) == self.settings[server]["startMinute"]) and (self.settings[server]["channelCreated"] is False):
                        # Create the channel, and store the ID, and time to delete channel in the settings.

                        if self.settings[server]["channel"] is None:
                            # Start with permissions
                            allow_list = []
                            deny_list = []
                            allow_perms = [ discord.PermissionOverwrite(read_messages=True, send_messages=False) ]
                            allow_roles = [ self.bot.user ]
                            deny_perms = []
                            deny_roles = []

                            if len(self.settings[server]["roleallow"]) > 0:
                            # If we have allow roles, automatically deny @everyone read messages.
                                deny_perms.append(discord.PermissionOverwrite(read_messages=False, add_reactions=False))
                                deny_roles.append(self.bot.get_server(server).default_role)
                                for override_roles in self.settings[server]["roleallow"]:
                                    find_role = discord.utils.get(self.bot.get_server(server).roles, name=override_roles)
                                    allow_roles.append(find_role)

                            allow_list = itertools.zip_longest(allow_roles, allow_perms, fillvalue=discord.PermissionOverwrite(read_messages=True, add_reactions=False))


                            # Check for deny permissions.
                            if len(self.settings[server]["roledeny"]) > 0:
                                deny_perms.append(discord.PermissionOverwrite(send_messages=False, add_reactions=False))
                                for override_roles2 in self.settings[server]["roledeny"]:
                                    find_role2 = discord.utils.get(self.bot.get_server(server).roles, name=override_roles2)
                                    deny_roles.append(find_role2)
                            deny_list = itertools.zip_longest(deny_roles, deny_perms, fillvalue=discord.PermissionOverwrite(send_messages=False))

                            if self.settings[server]["nsfw"]:
                                created_channel = await self.bot.create_channel(self.bot.get_server(server), "nsfw-{}".format(self.settings[server]["channelName"]), *list(allow_list), *list(deny_list))

                                # This is most definitely not the best way of doing it, but since no NSFW method, we have this:
                                header = { "Authorization" : "Bot {}".format(self.bot.settings.token), "content-type" : "application/json" }
                                body = { "nsfw" : True }

                                async with aiohttp.ClientSession() as session:
                                    async with session.patch('https://discordapp.com/api/channels/{}'.format(created_channel.id),headers=header,data=json.dumps(body)) as resp:
                                        print(resp.status)
                                        print(await resp.text())
                            else: # Not NSFW
                                created_channel = await self.bot.create_channel(self.bot.get_server(server), self.settings[server]["channelName"], *list(allow_list), *list(deny_list))

                            self.settings[server]["channel"] = created_channel.id
                            self._sync_settings()
                            print("TempChannel: Channel created at "+format(time.strftime("%H:%M:%S")))

                            # Change topic.
                            await self.bot.edit_channel(created_channel, topic=self.settings[server]["channelTopic"],name=self.settings[server]["channelName"])

                            # Set parent category.  Must use this method because library does not
                            # have a method for this yet.
                            if self.settings[server]["channelCategory"] != 0:
                                header = { "Authorization" : "Bot {}".format(self.bot.settings.token), "content-type" : "application/json" }
                                body = { "parent_id" : self.settings[server]["channelCategory"] }

                                async with aiohttp.ClientSession() as session:
                                    async with session.patch('https://discordapp.com/api/channels/{}'.format(created_channel.id),headers=header,data=json.dumps(body)) as resp:
                                        print(resp.status)
                                        print(await resp.text())

                            # Move channel position.
                            try:
                                await self.bot.move_channel(created_channel, self.settings[server]["channelPosition"])
                            except:
                                print("TempChannel: Could not move channel position")

                            # Set delete times, and save settings.
                            self.settings[server]["stopTime"] = time.time() + (self.settings[server]["durationHours"]*60*60) + (self.settings[server]["durationMinutes"]*60)
                            self.settings[server]["channelCreated"] = True
                            self._sync_settings()

                    elif self.settings[server]["channelCreated"]:
                        # Channel created, see when we should delete it.
                        self._sync_settings()
                        if time.time() >= self.settings[server]["stopTime"]:
                            try:
                                if self.settings[server]["channel"] is not None:
                                    try:
                                        await self.bot.delete_channel(self.bot.get_channel(self.settings[server]["channel"]))
                                        self.settings[server]["channel"] = None
                                    except Exception as e:
                                        print("TempChannel: "+e)
                            except:
                                self.settings[server]["channel"] = None
                            print("TempChannel: Channel deleted at "+format(time.strftime("%H:%M:%S")))
                            self.settings[server]["channelCreated"] = False
                            self._sync_settings()
            except Exception as e:
                print("TempChannels: No servers. {}".format(e))

def setup(bot):
    checkFilesystem()
    tempchannels = TempChannels(bot)
    bot.add_cog(tempchannels)
    bot.loop.create_task(tempchannels._check_channels())
