import asyncio
import discord
import random
import time
import itertools

from typing import Any
from discord.utils import get

from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)

listener = getattr(commands.Cog, "listener", None)  # Trusty + Sinbad
if listener is None:

    def listener(name=None):
        return lambda x: x


class Gathering(Cog):
    """
    Track Gathered Items
    """

    def __init__(self, bot: Red):
        self.bot = bot

        self.config = Config.get_conf(
            cog_instance=None, identifier=16548964843212888, force_registration=True, cog_name="Gathering"
        )
        self.config.register_guild(
            names=[],
            needed=[],
            gathered=[],
            category_list=[],
            list_msg_channel=0,
            list_msg_id=0,
            role_components = [],
            teamcraft="",
            # New system that isnt as stupid
            active_lists=[],
            item_list=[]
        )
        self.config.register_member(
           total_contribution=0,
           current_contribution=0,
           contribution_points=0
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def gatherboard(self, ctx: commands.Context, flags: str = None):
        if flags == "-all":
            data = await self.config.all_members(ctx.guild)
            accs = sorted(data, key=lambda x: data[x]["total_contribution"], reverse=True)
            list = []
            pos = 1
            pound_len = len(str(len(accs)))
            header = "{pound:{pound_len}}{score:{bar_len}}{name:2}\n".format(
                pound="#",
                name="Name",
                score="Items",
                pound_len=pound_len + 3,
                bar_len=pound_len + 9,
            )
            temp_msg = header
            for a_id in accs:
                a = get(ctx.guild.members, id=int(a_id))
                if a is None:
                    continue
                name = a.display_name
                contribution = await self.config.member(a).total_contribution()
                if a_id != ctx.author.id:
                    temp_msg += (
                        f"{f'{pos}.': <{pound_len+2}} {contribution: <{pound_len+8}} {name}\n"
                    )
                else:
                    temp_msg += (
                        f"{f'{pos}.': <{pound_len+2}} "
                        f"{contribution: <{pound_len+8}} "
                        f"<<{name}>>\n"
                    )
                if pos % 10 == 0:
                    list.append(box(temp_msg, lang="md"))
                    temp_msg = header
                pos += 1
            if temp_msg != header:
                list.append(box(temp_msg, lang="md"))
            if list:
                await menu(ctx, list, DEFAULT_CONTROLS)
            return
        data = await self.config.all_members(ctx.guild)
        accs = sorted(data, key=lambda x: data[x]["current_contribution"], reverse=True)
        list = []
        pos = 1
        pound_len = len(str(len(accs)))
        header = "{pound:{pound_len}}{score:{bar_len}}{name:2}\n".format(
            pound="#",
            name="Name",
            score="Items",
            pound_len=pound_len + 3,
            bar_len=pound_len + 9,
        )
        temp_msg = header
        for a_id in accs:
            a = get(ctx.guild.members, id=int(a_id))
            if a is None:
                continue
            name = a.display_name
            contribution = await self.config.member(a).total_contribution()
            if a_id != ctx.author.id:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} {contribution: <{pound_len+8}} {name}\n"
                )
            else:
                temp_msg += (
                    f"{f'{pos}.': <{pound_len+2}} "
                    f"{contribution: <{pound_len+8}} "
                    f"<<{name}>>\n"
                )
            if pos % 10 == 0:
                list.append(box(temp_msg, lang="md"))
                temp_msg = header
            pos += 1
        if temp_msg != header:
            list.append(box(temp_msg, lang="md"))
        if list:
            await menu(ctx, list, DEFAULT_CONTROLS)

    @commands.group(autohelp=True)
    @commands.guild_only()
    async def list(self, ctx):
        """Quest System"""
        pass

    @commands.mod()
    @list.command(name="create")
    async def list_create(self, ctx: commands.Context, *, list_str: str=None):
        """
        Create a gathering list.
        Format:
        ```category:(category name)
        (item name)*(amount needed)```

        The maximum number of categories is 24, and maximum character count is about 3,900. This is a Discord limitation.

        Example:
        ```category:Important Items
        Peacock Ore*927
        Lignum Vitae Logs*1800
        category:Cheap Items
        Gold Ore*87```
        """
        confirm_code = random.randint(1000,9999)
        embed=discord.Embed(
            title=":warning: Dangerous Command!",
            description=f"You are about to create a new list. Doing this will __**reset any previous list data**__, and permanently disable adding or removing from previous lists.\nThis action is __**irreversible**__\n\nTo confirm your action, please type the following numbers: `{confirm_code}`", 
            color=0xff0000
        )
        embed.set_footer(text="Type 'cancel' to cancel | Action will time out in 30 seconds")
        msg = await ctx.send(embed=embed)
        invalid = True
        while invalid:
            try:
                confirmation = await self.bot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=30)
            except asyncio.TimeoutError:
                embed=discord.Embed(
                    title="Cancelled: Action timed out.",
                    color=0xff0000
                )
                await msg.edit(embed=embed)
                invalid = False
                return
            if confirmation.content == f"{confirm_code}":
                invalid = False
            elif confirmation.content.lower() == "cancel":
                embed=discord.Embed(
                    title="Cancelled: Cancelled by user.",
                    color=0xff0000
                )
                await msg.edit(embed=embed)
                invalid = False
                return
            else:
                embed=discord.Embed(
                    title=":x: Invalid input",
                    description="Please try again.",
                    color=0xff0000
                )
                await msg.edit(embed=embed)
        embed=discord.Embed(
            title="Data Reset.",
            description=f"Please send a properly formatted message to create a new list. If you don't know the correct formatting, you can use `,help list create`. This command will time out in 30 seconds.", 
            color=0x00ff00
        )
        await msg.edit(embed=embed)
        try:
            list_str = await self.bot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=30)
        except asyncio.TimeoutError:
            embed=discord.Embed(
                title="Cancelled: Action timed out.",
                color=0xff0000
            )
            await msg.edit(embed=embed)
            return
        embed=discord.Embed(
            title="External Links",
            description=f"Send a link to an external listing program such as Teamcraft. Reply with 'None' if there is no link.",
            color=0x00ff00
        )
        await msg.edit(embed=embed)
        try:
            teamcraft_link = await self.bot.wait_for("message", check=lambda message: message.author == ctx.author, timeout=30)
        except asyncio.TimeoutError:
            embed=discord.Embed(
                title="Cancelled: Action timed out.",
                color=0xff0000
            )
            await msg.edit(embed=embed)
            return
        if teamcraft_link.content.lower() != "none":
            teamcraft_link = teamcraft_link.content
            await self.config.guild(ctx.guild).teamcraft.set(teamcraft_link)
        else:
            await self.config.guild(ctx.guild).teamcraft.set("")
        list_str = list_str.content
        embed=discord.Embed(
            title="Checking data formatting...",
            description=f"If any errors are found, a message will be sent with the errors and what line they are on.",
            color=0x00ff00
        )
        await msg.edit(embed=embed)
        time.sleep(1)
        invalid_format = await self.check_format(list_str)
        if invalid_format != "None":
            embed=discord.Embed(
            title=":x: Formatting error",
            description=f"{invalid_format}",
            color=0xff0000
            )
            await msg.edit(embed=embed)
            return
        category_split = list_str.split("category:")
        category_lists = []
        for items in category_split:
            category_lists.append(items.split("\n"))
        while [""] in category_lists:
            category_lists.remove([""])
        for lists in category_lists:
            while "" in lists:
                lists.remove("")
        await self.config.guild(ctx.guild).category_list.set(category_lists)
        await self.gen_embed(ctx, category_lists, msg)

    async def gen_embed(self, ctx, category_lists, msg):
        """Generates a new embed for the list"""
        total_needed = 0
        category_count = len(category_lists)
        link = await self.config.guild(ctx.guild).teamcraft()
        if link != "":
            embed=discord.Embed(title="Production List", description=f"Use `,add (amount) (item name)` to add items or `,remove (amount) (item name)` to remove items from the list.\n\nExample: `,add 187 copper ore`\n\n[Teamcraft Link]({link})")
        else:
            embed=discord.Embed(title="Production List", description=f"Use `,add (amount) (item name)` to add items or `,remove (amount) (item name)` to remove items from the list.\n\nExample: `,add 187 copper ore`")
        loopnum = 0
        needed_list = []
        while loopnum < category_count:
            item_str = ""
            for items in category_lists[loopnum]:
                try:
                    item_name, item_amount = items.split("*")
                except:
                    continue
                needed_list.append(int(item_amount))
                total_needed = total_needed + int(item_amount)
                comma_needed = "{:,}".format(int(item_amount))
                item_str = item_str + f"{item_name} (0/{comma_needed})\n"
            embed.add_field(name=f"{category_lists[loopnum][0]}", value=f"{item_str}", inline=False)
            loopnum = loopnum + 1
        for lists in category_lists:
            lists.pop(0)
        item_only_list = list(itertools.chain.from_iterable(category_lists))
        gathered_list = []
        for items in item_only_list:
            gathered_list.append(0)
        embed.set_footer(text=f"0% Completed (0/{total_needed} items)")
        await msg.edit(embed=embed)
        await self.config.guild(ctx.guild).list_msg_channel.set(msg.channel.id)
        await self.config.guild(ctx.guild).list_msg_id.set(msg.id)
        await self.config.guild(ctx.guild).gathered.set(gathered_list)
        await self.config.guild(ctx.guild).needed.set(needed_list)
        return

    async def check_format(self, list_str):
        """Attempts to notify of errors in formatting."""
        invalid_format = "None"
        if list_str[:9] != "category:":
            invalid_format = "Error on line 1: List must start with 'category:'. Please use `,help list create` for an example of the correct formatting."
        if "\n" not in list_str:
            invalid_format = "Error on line 2: List must have at least one item. Please use `,help list create` for an example of the correct formatting."
        line_split = list_str.split("\n")
        loopnum = 0
        category_count = 0
        for lines in line_split:
            loopnum = loopnum + 1
            try:
                if lines[:9] == "category:":
                    category_count = category_count + 1
                    if category_count > 24:
                        return "You have too many categories. The maximum number of categories is 24."
                    continue
            except:
                pass
            if len(list(lines.split("*"))) != 2:
                invalid_format = f"Error on line {loopnum}: Expected 2 arguments: name, amount. Received {len(list(lines.split('*')))} arguments. Please use `,help list create` for an example of the correct formatting."
            if len(lines.split("|")) > 1:
                item = lines.split("*")
                extra = item[1].split("|")
                item[1] = extra[0]
                while len(extra) < 3:
                    extra.append(0)
                if type(extra[1]) is str:
                    extra[2] = extra[1]
                    extra[1] = 1
                if extra[2] not in ['special', 1]:
                    invalid_format = f"Error on line {loopnum}: '{extra[2]}' is not a valid item type. Please use `,help list create` for a list of all valid item types."
                try:
                    float(extra[1])
                except:
                    invalid_format = f"Error on line {loopnum}: '{extra[1]}' is not a valid contribution multiplier. Must be a number. Please use `,help list create` for an example of the correct formatting."
        return invalid_format
