import asyncio
import discord
import itertools
import typing

from typing import Any

from discord import app_commands

from redbot.core import Config, commands

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
