import asyncio

import discord
from discord import app_commands
from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .scheduler import Schedule, Scheduler

bot_id = None #949857998753366056
test_guild = None #879602977046937630

# add tree
def setup(bot: Red) -> None:
    bot.add_cog(Scheduler(bot))
    try:
        if not hasattr(bot, "tree"):
            bot.tree = app_commands.CommandTree(bot)
    except AttributeError:
        raise CogLoadError("This cog requires the latest discord.py 2.0.0a.") from None
    asyncio.create_task(_setup(bot))

# add command and sync tree
async def _setup(bot: Red):
    assert isinstance(bot.tree, app_commands.CommandTree)
    await bot.wait_until_red_ready()
    assert bot.user
    if bot.user.id == bot_id:
        guild = discord.Object(id=test_guild)
    else:
        guild = None
    #GatheringList().name = "list"
    bot.tree.add_command(Schedule(), guild=guild)
    await bot.tree.sync(guild=guild)

# remove and resync tree
def teardown(bot: Red):
    if bot.user:
        assert isinstance(bot.tree, app_commands.CommandTree)
        if bot.user.id == bot_id:
            guild = discord.Object(id=test_guild)
        else:
            guild = None
        bot.tree.remove_command(Schedule().name, guild=guild)
        asyncio.create_task(bot.tree.sync(guild=guild))
