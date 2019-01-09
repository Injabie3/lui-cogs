import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help, settings
from collections import deque, defaultdict
from cogs.utils.chat_formatting import escape_mass_mentions, box
import os
import re
import logging
import asyncio

def check_folders():
    folders = ("data", "data/modcustom/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    plonked_perms = {"users": [], "roles": []}
    override_perms = {"users": [], "roles": []}

    files = {
        "plonked_perms.json"      : plonked_perms,
        "override_perms.json"      : override_perms
    }

    for filename, value in files.items():
        if not os.path.isfile("data/modcustom/{}".format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json("data/modcustom/{}".format(filename), value)


class ModCustom(object):
    """Custom mod tools for use outside of the standard Ren-bot Framework"""
    
    def __init__(self, bot):
        self.bot = bot
        self.override_perms = dataIO.load_json("data/modcustom/override_perms.json")
        self.plonked_perms = dataIO.load_json("data/modcustom/plonked_perms.json")
        
    def is_plonked(self, server, member): # note: message.server isnt needed
        if len([x for x in self.plonked_perms["users"] if member.id == x ]) == 0:
            return False
        else:
            return True
    
    def has_perms(self, server, member):
        perms = []
        overrides = [] # these roles have higher precedence than blacklist roles
        for role in member.roles:
            perms += [x for x in self.plonked_perms["roles"] if x in role.name]
            overrides += [x for x in self.override_perms["roles"] if x in role.name]
            
        if len(perms) == 0: # no blacklisted roles, we good to go
            return True
        elif len(perms) != 0 and len(overrides) != 0: # have a blacklisted role, but also have a whitelisted role, good to go
            return True
        else: # sorry, better luck next time
            return False
            
    @commands.group(pass_context=True)
    @checks.is_owner_or_permissions(administrator=True)
    async def plonked(self, ctx):
        """Bans user from using the bot"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @plonked.command(name="adduser")
    async def _blacklist_adduser(self, user: discord.Member):
        """Adds user to bot's blacklist"""
        if user.id not in self.plonked_perms["users"]:
            self.plonked_perms["users"].append(user.id)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonked_perms)
            await self.bot.say("User has been added to blacklist.")
        else:
            await self.bot.say("User is already blacklisted.")

    @plonked.command(name="addrole")
    async def _blacklist_addrole(self, role: str):
        """Adds role to bot's blacklist"""
        if role not in self.plonked_perms["roles"]:
            self.plonked_perms["roles"].append(role)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonked_perms)
            await self.bot.say("Role has been added to blacklist.")
        else:
            await self.bot.say("Role is already blacklisted.")

    @plonked.command(name="removeuser")
    async def _blacklist_removeuser(self, user: discord.Member):
        """Removes user from bot's blacklist"""
        if user.id in self.plonked_perms["users"]:
            self.plonked_perms["users"].remove(user.id)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonked_perms)
            await self.bot.say("User has been removed from blacklist.")
        else:
            await self.bot.say("User is not in blacklist.")

    @plonked.command(name="removerole")
    async def _blacklist_removerole(self, role: str):
        """Removes role to bot's blacklist"""
        if role in self.plonked_perms["roles"]:
            self.plonked_perms["roles"].remove(role)
            dataIO.save_json("data/modcustom/plonked_perms.json", self.plonked_perms)
            await self.bot.say("Role has been removed from blacklist.")
        else:
            await self.bot.say("Role is not in blacklist.")

    @plonked.command(name="clear")
    async def _blacklist_clear(self):
        """Clears the blacklist"""
        self.plonked_perms = {"users": [], "roles": []}
        dataIO.save_json("data/modcustom/plonked_perms.json", self.plonked_perms)
        await self.bot.say("Blacklist is now empty.")

    @commands.group(pass_context=True)
    @checks.is_owner_or_permissions(administrator=True)
    async def overridden(self, ctx):
        """Users who will be able to use the bot"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @overridden.command(name="adduser")
    async def _whitelist_adduser(self, user: discord.Member):
        """Adds user to bot's whitelist"""
        if user.id not in self.override_perms["users"]:
            if not self.override_perms["users"]:
                msg = "\nAll users not in whitelist will be ignored (owner, admins and mods excluded)"
            else:
                msg = ""
            self.override_perms["users"].append(user.id)
            dataIO.save_json("data/modcustom/override_perms.json", self.override_perms)
            await self.bot.say("User has been added to whitelist." + msg)
        else:
            await self.bot.say("User is already whitelisted.")

    @overridden.command(name="addrole")
    async def _whitelist_addrole(self, role: str):
        """Adds role to bot's whitelist"""
        if role not in self.override_perms["roles"]:
            if not self.override_perms["roles"]:
                msg = "\nAll roles not in whitelist will be ignored (owner, admins and mods excluded)"
            else:
                msg = ""
            self.override_perms["roles"].append(role)
            dataIO.save_json("data/modcustom/override_perms.json", self.override_perms)
            await self.bot.say("Role has been added to whitelist." + msg)
        else:
            await self.bot.say("Role is already whitelisted.")

    @overridden.command(name="removeuser")
    async def _whitelist_removeuser(self, user: discord.Member):
        """Removes user from bot's whitelist"""
        if user.id in self.override_perms["users"]:
            self.override_perms["users"].remove(user.id)
            dataIO.save_json("data/modcustom/override_perms.json", self.override_perms)
            await self.bot.say("User has been removed from whitelist.")
        else:
            await self.bot.say("User is not in whitelist.")

    @overridden.command(name="removerole")
    async def _whitelist_removerole(self, role: str):
        """Adds role to bot's whitelist"""
        if role in self.override_perms["roles"]:
            self.override_perms["roles"].remove(role)
            dataIO.save_json("data/modcustom/override_perms.json", self.override_perms)
            await self.bot.say("Role has been removed from whitelist.")
        else:
            await self.bot.say("Role is not in whitelist.")

    @overridden.command(name="clear")
    async def _whitelist_clear(self):
        """Clears the whitelist"""
        self.override_perms = {"users": [], "roles": []}
        dataIO.save_json("data/modcustom/override_perms.json", self.override_perms)
        await self.bot.say("Whitelist is now empty.")
        
def setup(bot):
    check_folders()
    check_files()
    n = ModCustom(bot)
    bot.add_cog(n)