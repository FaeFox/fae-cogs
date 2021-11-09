import discord
# Experimental
from discord_components import DiscordComponents, Select, SelectOption
from typing import Any

from redbot.core import commands
from redbot.core.bot import Red

Cog: Any = getattr(commands, "Cog", object)

listener = getattr(commands.Cog, "listener", None)  # Trusty + Sinbad
if listener is None:
    def listener(name=None):
        return lambda x: x

class SelectRoles(Cog):
    """
    Create self-role menus.
    """

    def __init__(self, bot: Red):
        self.bot = bot
        DiscordComponents(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        DiscordComponents(self.bot, change_discord_methods=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        await interaction.defer()
        #embed=discord.Embed(title="Roles Added", description=f"The following roles were added:", color=0xff0000)
        #await interaction.respond(embed=embed)
        #await interaction.respond(content=f"{interaction.values[0].split('|')}")
        if interaction.values != []:
            if interaction.values[0].split("|")[0] == "sra":
                await self.selfrole_add(interaction)
            if interaction.values[0].split("|")[0] == "srr":
                await self.selfrole_remove(interaction)
        else:
            return interaction

    async def selfrole_remove(self, interaction):
        """Remove roles"""
        failed_str = ""
        removed_str = ""
        error_str = ""
        total_str = ""
        guild = self.bot.get_guild(interaction.guild.id)
        member = guild.get_member(interaction.author.id)
        for values in interaction.values:
            role_id = values.split("|")[1]
            role = discord.utils.get(guild.roles, id=int(role_id))
            if role not in member.roles:
                if failed_str != "":
                    failed_str = failed_str + f", {role.mention}"
                else:
                    failed_str = failed_str + f"{role.mention}"
                continue
            try:
                await interaction.author.remove_roles(role)
            except:
                error_str = error_str + f"\n{role_id} doesn't seem to exist. This is usually because an admin deleted the role without updating the list. ({role_id} is option {(interaction.values.index(values))+1} that you selected)\n"
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
        await interaction.respond(embed=embed)
        return

    async def selfrole_add(self, interaction):
        """Add roles"""
        failed_str = ""
        added_str = ""
        error_str = ""
        total_str = ""
        guild = self.bot.get_guild(interaction.guild.id)
        member = guild.get_member(interaction.author.id)
        for values in interaction.values:
            role_id = values.split("|")[1]
            role = discord.utils.get(guild.roles, id=int(role_id))
            if role in member.roles:
                if failed_str != "":
                    failed_str = failed_str + f", {role.mention}"
                else:
                    failed_str = failed_str + f"{role.mention}"
                continue
            try:
                await interaction.author.add_roles(role)
            except:
                error_str = error_str + f"\n{role_id} doesn't seem to exist. This is usually because an admin deleted the role without updating the list. ({role_id} is option {(interaction.values.index(values))+1} that you selected)\n"
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
        await interaction.respond(embed=embed)
        return

    # interaction IDs --------------------
    #sra = self role add
    #srr = self role remove
    # ------------------------------------

    @commands.command()
    @commands.guild_only()
    @commands.admin()
    @commands.bot_has_permissions(embed_links=True)
    async def selectrole(self, ctx, *, self_roles: str):
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
        try:
            select_options = self_roles.split("\n")
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
            options = []
            remove_options = []
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
                options.append(SelectOption(label= info_split[0], value=f"sra|{info_split[1]}", description=info_split[2], emoji=emoji))
                remove_options.append(SelectOption(label= info_split[0], value=f"srr|{info_split[1]}", description=info_split[3], emoji=emoji))
            max_values = len(options)
            components = [Select(placeholder= add_placeholder, options= options, max_values= max_values), Select(placeholder= remove_placeholder, options= remove_options, max_values= max_values)]
            await ctx.send(f"> {msg_title}", components = components)
        except discord.errors.HTTPException as error:
            #if "Invalid Emoji" in error:
            #    await ctx.send(f"One or more emotes were invalid.")
            #else:
            #    await ctx.send(f"Your formatting was correct, however a value you input was not valid.")
            await ctx.send(error)
        except Exception as e:
            await ctx.send(f"Invalid formatting, please use `{ctx.clean_prefix}help selectrole` for an example of how to format your message.\nDetails:\n {error_str}\nDebug:{e}")