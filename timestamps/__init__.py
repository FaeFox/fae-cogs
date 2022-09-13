import asyncio

import discord
from discord import app_commands
from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .timestamps import timestamps

bot_id = None #949857998753366056
test_guild = None #779821183285461052

# add tree
async def setup(bot: Red) -> None:
    try:
        if not hasattr(bot, "tree"):
            await bot.tree = app_commands.CommandTree(bot)
    except AttributeError:
        raise CogLoadError("This cog requires at least discord.py 2.0.0a") from None
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
    bot.tree.add_command(timestamps, guild=guild)
    await bot.tree.sync(guild=guild)

# remove and resync tree
await def teardown(bot: Red):
    if bot.user:
        assert isinstance(bot.tree, app_commands.CommandTree)
        if bot.user.id == bot_id:
            guild = discord.Object(id=test_guild)
        else:
            guild = None
        await bot.tree.remove_command(timestamps.name, guild=guild)
        asyncio.create_task(bot.tree.sync(guild=guild))
