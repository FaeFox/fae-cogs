import asyncio
import discord
import itertools
import typing
import random

from typing import Any

from discord import app_commands
from discord.utils import get

from redbot.core import Config, commands
from redbot.core.utils.chat_formatting import box
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)

config = Config.get_conf(
    cog_instance=None, identifier=16548964843212888, force_registration=True, cog_name="Gathering"
)
# some idiot named Fae decided to store data in a stupid way that makes no sense. Why...
# could have used dictionaries to make everything easy and readable but NOoO of course not
config.register_guild(
    names=[],
    needed=[],
    gathered=[],
    category_list=[],
    list_msg_channel=0,
    list_msg_id=0,
    role_components = [],
    teamcraft="",
    # New system that isnt as stupid, WIP
    active_lists=[],
    item_list=[]
)
config.register_member(
   total_contribution=0,
   current_contribution=0,
   contribution_points=0
)


class Gathering(Cog):
    """
    Track Gathered Items
    """

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def gatherboard(self, ctx: commands.Context, flags: str = None):
        if flags == "-all":
            data = await config.all_members(ctx.guild)
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
                contribution = await config.member(a).total_contribution()
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
        data = await config.all_members(ctx.guild)
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
            contribution = await config.member(a).total_contribution()
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
        """Create a gathering list."""
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
            description=f"Please send a properly formatted message to create a new list. If you don't know the correct formatting, you can use `{ctx.clean_prefix}help list create`. This command will time out in 30 seconds.", 
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
            await config.guild(ctx.guild).teamcraft.set(teamcraft_link)
        else:
            await config.guild(ctx.guild).teamcraft.set("")
        list_str = list_str.content
        embed=discord.Embed(
            title="Checking data formatting...",
            description=f"If any errors are found, a message will be sent with the errors and what line they are on.",
            color=0x00ff00
        )
        await msg.edit(embed=embed)
        await asyncio.sleep(1)
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
        await config.guild(ctx.guild).category_list.set(category_lists)
        await self.gen_embed(ctx, category_lists, msg)

    async def gen_embed(self, ctx, category_lists, msg):
        """Generates a new embed for the list"""
        total_needed = 0
        category_count = len(category_lists)
        link = await config.guild(ctx.guild).teamcraft()
        if link != "":
            embed=discord.Embed(title="Production List", description=f"Please type `/list` to see avaliable commands.\n\n[Teamcraft Link]({link})")
        else:
            embed=discord.Embed(title="Production List", description=f"Please type `/list` to see avaliable commands.")
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
        await config.guild(ctx.guild).list_msg_channel.set(msg.channel.id)
        await config.guild(ctx.guild).list_msg_id.set(msg.id)
        await config.guild(ctx.guild).gathered.set(gathered_list)
        await config.guild(ctx.guild).needed.set(needed_list)
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

class List(app_commands.Group):
    """Production list commands."""

    async def autocomplete_item(self, interaction: discord.Interaction,current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
        category_lists = await config.guild(interaction.guild).category_list()
        category_lists_pop = category_lists
        for lists in category_lists_pop:
            lists.pop(0)
        item_only_list = list(itertools.chain.from_iterable(category_lists_pop))
        for i in range(len(item_only_list)):
            item_only_list[i] = item_only_list[i].lower()
            item_only_list[i] = item_only_list[i].split("*")[0]
        return [
            app_commands.Choice(name=item.title(), value=item.title())
            for item in item_only_list if current.lower() in item.lower()
        ][:25]

    @app_commands.command()
    @app_commands.autocomplete(item=autocomplete_item)
    @app_commands.describe(item="The name of the item you are adding.", amount="How many items you are adding.")
    async def add(self, interaction: discord.Interaction, item: str, amount: int):
        """Add items to the list"""
        guild = interaction.guild
        author = interaction.user
        item_name = item
        contribution = await config.member(author).total_contribution()
        curr_contribution = await config.member(author).current_contribution()
        needed_list = await config.guild(guild).needed()
        category_lists = await config.guild(guild).category_list()
        category_lists_pop = category_lists
        for lists in category_lists_pop:
            lists.pop(0)
        item_only_list = list(itertools.chain.from_iterable(category_lists_pop))
        gathered = await config.guild(guild).gathered()
        for i in range(len(item_only_list)):
            item_only_list[i] = item_only_list[i].lower()
            item_only_list[i] = item_only_list[i].split("*")[0]
        try:
            item_index = item_only_list.index(item_name.lower())
        except:
            embed=discord.Embed(title=f":x: Item not in list.", description=f"The item you are trying to add does not appear to be on the current production list.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if gathered[item_index] >= needed_list[item_index]:
            embed=discord.Embed(title=f":x: Item already completed", description=f"The item you are trying to add has already been completed.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        extra_items = 0
        embed=discord.Embed(title=f"✅ Item{'' if amount == 1 else 's'} Added", description=f"Successfully added {amount} {item.title()} to the list.{'' if gathered[item_index] + amount > needed_list[item_index] else f' (+{amount} contribution points)'}", color=0x00ff00)
        log_embed=discord.Embed(title=f"Item{'' if amount == 1 else 's'} Added", description=f"**{interaction.user.name}** added **{amount} __{item}__** to the list.", color=0x00ff00)
        if gathered[item_index] + amount > needed_list[item_index]:
            embed.add_field(name=":warning: Notice", value=f"You added {(gathered[item_index] + amount) - needed_list[item_index]} items over the requested amount. Your items have been successfully added, but you will only receive contribution points for the amount originally requested. (+{amount - ((gathered[item_index] + amount) - needed_list[item_index])} contribution points)")
            log_embed.set_footer(text=f"⚠️ Donated {(gathered[item_index] + amount) - needed_list[item_index]} over requested amount. Contribution score reduced accordingly.")
            extra_items = (gathered[item_index] + amount) - needed_list[item_index]
        gathered[item_index] = gathered[item_index] + amount
        new_contribution = (contribution + amount) - extra_items
        new_curr_contribution = (curr_contribution + amount) - extra_items
        await config.member(author).total_contribution.set(new_contribution)
        await config.member(author).current_contribution.set(new_curr_contribution)
        await config.guild(guild).gathered.set(gathered)
        await self.regen_embed(guild)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log_channel = discord.utils.get(guild.channels, id=953165177946243092)
        try:
            await log_channel.send(embed=log_embed)
        except:
            pass

    @app_commands.command()
    @app_commands.autocomplete(item=autocomplete_item)
    @app_commands.describe(item="The name of the item you are removing.", amount="How many items you are removing.")
    async def remove(self, interaction: discord.Interaction, item: str, amount: int):
        """Remove items from the list."""
        guild = interaction.guild
        author = interaction.user
        contribution = await config.member(author).total_contribution()
        curr_contribution = await config.member(author).current_contribution()
        guild = interaction.guild
        author = interaction.user
        item_name = item
        category_lists = await config.guild(guild).category_list()
        for lists in category_lists:
            lists.pop(0)
        item_only_list = list(itertools.chain.from_iterable(category_lists))
        gathered = await config.guild(guild).gathered()
        for i in range(len(item_only_list)):
            item_only_list[i] = item_only_list[i].lower()
            item_only_list[i] = item_only_list[i].split("*")[0]
        if item_name.lower() not in item_only_list:
            embed=discord.Embed(title=":x: Error", description="The item you are trying to add is not on the production list. Please check your spelling and try again.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        item_index = item_only_list.index(item_name.lower())
        gathered[item_index] = gathered[item_index] - amount
        if gathered[item_index] < 0:
            gathered[item_index] = 0
        await config.guild(guild).gathered.set(gathered)
        await self.regen_embed(guild)
        new_contribution = (contribution - amount)
        new_curr_contribution = (curr_contribution - amount)
        await config.member(author).total_contribution.set(new_contribution)
        await config.member(author).current_contribution.set(new_curr_contribution)
        embed=discord.Embed(title=f"✅ Item{'' if amount == 1 else 's'} Removed", description=f"Successfully removed {amount} {item.title()} from the list", color=0x00ff00)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        log_channel = discord.utils.get(guild.channels, id=953165177946243092)
        embed=discord.Embed(title=f"Item{'' if amount == 1 else 's'} Removed", description=f"**{interaction.user.name}** removed **{amount} __{item}__** from the list.", color=0xff0000)
        try:
            await log_channel.send(embed=embed)
        except:
            pass

    @app_commands.command()
    async def show(self, interaction: discord.Interaction):
        """Show the current production list."""
        embed = await self.regen_embed(interaction.guild, False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def regen_embed(self, guild, edit_existing=True):
        """Generates a new embed for the list"""
        category_lists = await config.guild(guild).category_list()
        gathered = await config.guild(guild).gathered()
        category_count = len(category_lists)
        link = await config.guild(guild).teamcraft()
        if link != "":
            embed=discord.Embed(title="Production List", description=f"Please see `/list` for a list of commands.\n\n[Teamcraft Link]({link})")
        else:
            embed=discord.Embed(title="Production List", description=f"Please see `/list` for a list of commands.")
        loopnum = 0
        # For percentage completed
        total_gathered = 0
        total_needed = 0
        # ---------------
        category_lists_rem = await config.guild(guild).category_list()
        # Remove Category Strings
        for lists in category_lists_rem:
            lists.pop(0)
        # List of only items
        item_only_list = list(itertools.chain.from_iterable(category_lists_rem))
        # Iterate through list, lowercase, and save position 0 [Unsure]
        for i in range(len(item_only_list)):
            item_only_list[i] = item_only_list[i].lower()
            item_only_list[i] = item_only_list[i].split("*")[0]
        finished_str = ""
        # While loop to index lists easier
        while loopnum < category_count:
            item_str = ""
            for items in category_lists[loopnum]:
                try:
                    item_name, item_amount = items.split("*")
                except:
                    continue
                item_index = item_only_list.index(item_name.lower())
                # Add commas to numbers over 1k
                comma_gathered = "{:,}".format(gathered[item_index])
                comma_needed = "{:,}".format(int(item_amount))
                # Show finished items at end of list
                if gathered[item_index] >= int(item_amount):
                    finished_str = finished_str + f"~~*{item_name}*~~ ({comma_gathered}/{comma_needed})\n"
                else:
                    item_str = item_str + f"{item_name} ({comma_gathered}/{comma_needed})\n"
                total_gathered = total_gathered + gathered[item_index]
                total_needed = total_needed + int(item_amount)
            if item_str == "":
                item_str = "*Category Completed.*"
            # Add item list to embed category
            embed.add_field(name=f"{category_lists[loopnum][0]}", value=f"{item_str}", inline=False)
            loopnum = loopnum + 1
        if finished_str != "":
            embed.add_field(name=f"Completed", value=f"{finished_str}", inline=False)
        channel = discord.utils.get(guild.channels, id=await config.guild(guild).list_msg_channel())
        # Get completion percent, handle divide by zero
        try:
            percent_done = int((total_gathered/total_needed)*100)
        except:
            percent_done = 0
        comma_needed = "{:,}".format(int(total_needed))
        comma_gathered = "{:,}".format(int(total_gathered))
        embed.set_footer(text=f"{percent_done}% Completed ({comma_gathered}/{comma_needed} items)")
        if edit_existing == False:
            return embed
        msg = await channel.fetch_message(await config.guild(guild).list_msg_id())
        await msg.edit(embed=embed)
        return
