import asyncio
import discord

from typing import Any

from redbot.core import commands

from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)

class AddSelect(discord.ui.Select):
    def __init__(self):
        select_list = [
            discord.SelectOption(label=select_dict['label'], value=select_dict['value'], emoji=select_dict['emoji'], description=select_dict['description'])
            for select_dict in options
        ]
        super().__init__(placeholder=options[0]['add_placehold'], max_values=len(options), min_values=1, options=select_list)
    async def callback(self, interaction: discord.Interaction):
        failed_str = ""
        added_str = ""
        error_str = ""
        total_str = ""
        guild = interaction.guild
        member = interaction.user
        for role_id in self.values:
            role = discord.utils.get(guild.roles, id=int(role_id))
            if role in member.roles:
                if failed_str != "":
                    failed_str = failed_str + f", {role.mention}"
                else:
                    failed_str = failed_str + f"{role.mention}"
                continue
            try:
                await member.add_roles(role)
            except:
                error_str = error_str + f"\n{role_id} doesn't seem to exist. This is usually because a staff member has deleted the role without updating this select. ({role_id} is option {(self.values.index(role_id))+1} on the select.)\n"
                continue
            if added_str != "":
                added_str = added_str + f", {role.mention}"
            else:
                added_str = added_str + f"{role.mention}"
        if added_str != "":
            total_str = total_str + f"The following roles were added:\n{added_str}"
            embed_color = 0x00ff00
        if failed_str != "":
            total_str = total_str + f"\n\nYou already had the following roles:\n{failed_str}"
            embed_color = 0xffff00
        if error_str != "":
            total_str = total_str + error_str
            embed_color = 0xff0000
        embed=discord.Embed(title="Self-Assignable Roles", description=f"{total_str}", color=embed_color)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RemoveSelect(discord.ui.Select):
    def __init__(self):
        select_list = [
            discord.SelectOption(label=select_dict['label'], value=select_dict['value'], emoji=select_dict['emoji'], description=select_dict['rem_description'])
            for select_dict in options
        ]
        super().__init__(placeholder=options[0]['rem_placehold'], max_values=len(options), min_values=1, options=select_list)
    async def callback(self, interaction: discord.Interaction):
        failed_str = ""
        removed_str = ""
        error_str = ""
        total_str = ""
        guild = interaction.guild
        member = interaction.user
        for role_id in self.values:
            role = discord.utils.get(guild.roles, id=int(role_id))
            if role not in member.roles:
                if failed_str != "":
                    failed_str = failed_str + f", {role.mention}"
                else:
                    failed_str = failed_str + f"{role.mention}"
                continue
            try:
                await member.remove_roles(role)
            except:
                error_str = error_str + f"\n{role_id} doesn't seem to exist. This is usually because a staff member has deleted the role without updating this select. ({role_id} is option {(self.values.index(role_id))+1} on the select.)\n"
                continue
            if removed_str != "":
                removed_str = removed_str + f", {role.mention}"
            else:
                removed_str = removed_str + f"{role.mention}"
        if removed_str != "":
            total_str = total_str + f"The following roles were removed:\n{removed_str}"
            embed_color = 0x00ff00
        if failed_str != "":
            total_str = total_str + f"\n\nYou did not have the following roles:\n{failed_str}"
            embed_color = 0xffff00
        if error_str != "":
            total_str = total_str + error_str
            embed_color = 0xff0000
        embed=discord.Embed(title="Self-Assignable Roles", description=f"{total_str}", color=embed_color)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class SelectView(discord.ui.View):
    def __init__(self, *, timeout = None):
        super().__init__(timeout=timeout)
        self.add_item(AddSelect())
        self.add_item(RemoveSelect())



class SelectRoles(Cog):
    """
    Self-assignable role system.
    """

    def __init__(self, bot: Red):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    async def selectroles(self, ctx: commands.Context, *, role_message: str):
        """
        Create a menu for members to select roles from.

        Format:
        ```(Title)
        (Add placeholder text)
        (Remove placeholder text)
        (Title);(Role);(Add Description);(Remove Description);(emote)```
        Example:
        ```Notification Roles
        Select notification roles to add
        Select notification roles to remove
        Events;@events;Get pinged for server events.;Disable pings for server events.;🟢
        Announcements;@announcements;Get pinged for server announcements.;Disable pings for server announcements.;🔵```

        The maximum number of roles is 24.
        """
        select_options = role_message.split("\n")
        if len(select_options) > 27:
            await ctx.send("You can only have up to 24 roles per menu.")
            return
        # Define and remove first 3 lines
        msg_title = select_options[0]
        add_placeholder = select_options[1]
        remove_placeholder = select_options[2]
        select_options.pop(0)
        select_options.pop(0)
        select_options.pop(0)
        # Create select
        global options
        options = []
        error_str = ""
        curr_line = 0
        for select_info in select_options:
            curr_line = curr_line + 1
            # Get role ID
            info_split = select_info.split(";")
            if len(info_split) != 5:
                error_str = error_str + f"Error on line {curr_line + 3}: Not enough arguments (expected 5, got {len(info_split)})\n"
            info_split[4] = info_split[4].strip()
            info_split[1] = info_split[1].replace("<@&", "")
            info_split[1] = info_split[1].strip(">")
            # Get emote ID if custom emote
            try:
                emoji_split = info_split[4].split(":")
                emoji_str = emoji_split[2].strip(">")
                emoji_id = int(emoji_str)
                try:
                    emoji= self.bot.get_emoji(emoji_id)
                except:
                    error_str = error_str + f"Error on line {curr_line + 3}: Invalid Emote\n"
            except:
                emoji = info_split[4]
                emoji = emoji.strip()
            options.append({
                "add_placehold": add_placeholder,
                "rem_placehold": remove_placeholder,
                "label": info_split[0],
                "value": info_split[1],
                "description": info_split[2],
                "rem_description": info_split[3],
                "emoji": emoji
            })
        max_values = len(options)
        await ctx.send(f"> {msg_title}", view=SelectView())
