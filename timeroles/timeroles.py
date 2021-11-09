import asyncio
import time
import traceback
import discord
import re

from redbot.core import Config, checks, commands
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

__author__ = "FaeFox"

class TimeRoles(commands.Cog):
    """Grant temporary roles."""

    default_global_settings = {
        "grants": [],
        "grant_idnum": 0
    }

    def __init__(self, bot):
        """Set up the plugin."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 12243648600909)
        self.config.register_global(**self.default_global_settings)
        self.config.register_guild(log_channel=0)
        self.units = {
            "minute": 60,
            "min": 60,
            "m": 60,
            "hour": 3600,
            "hr": 3600,
            "h": 3600,
            "day": 86400,
            "d": 86400,
            "week": 604800,
            "wk": 604800,
            "w": 604800,
            "month": 2592000,
            "mon": 2592000,
            "mo": 2592000,
        }
        self.time = 5
        self.task = self.bot.loop.create_task(self.check_role_grants())

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    @commands.command()
    @commands.guild_only()
    @commands.admin()
    @commands.bot_has_permissions(embed_links=True)
    async def showgrants(self, ctx):
        """Show all active grants for this guild."""
        grants = await self.config.grants()
        guild_grants = []
        for grant in grants:
            if grant['guild_id'] != ctx.guild.id:
                continue
            guild_grants.append(grant)
        if len(guild_grants) <= 0:
            embed=discord.Embed(title="Active Grants", description=f"There are currently no grants active in this server.", color=0x00ff00)
            await ctx.send(embed=embed)
            return
        max_len = 24
        guild_grants_div = [guild_grants[i * max_len:(i + 1) * max_len] for i in range((len(guild_grants) + max_len - 1) // max_len)]
        page_num = 0
        last_page = len(guild_grants_div)
        embed_list = []
        for lists in guild_grants_div:
            embed=discord.Embed(title="Active Grants", color=0x00ff00)
            page_num = page_num + 1
            embed.set_footer(text=f"Grants for {ctx.guild.name} | Page {page_num} of {last_page}")
            for grant in lists:
                embed.add_field(name=f"Grant ID: {grant['grant_id']}", value=f"Granted to: <@{grant['target_id']}>\nRole: <@&{grant['role_id']}>\nExpires in: {self.display_time(grant['expiration'] - int(time.time()))}")
            embed_list.append(embed)
        if len(embed_list) == 1:
            await ctx.send(embed=embed_list[0])
        else:
            await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @commands.command()
    @commands.guild_only()
    @commands.admin()
    @commands.bot_has_permissions(embed_links=True)
    async def revoke(self, ctx: commands.Context, grant_id: str):
        """Revoke an active grant for this guild."""
        grants = await self.config.grants()
        found = False
        for grant in grants:
            if int(grant['guild_id']) == ctx.guild.id and grant['grant_id'].lower() == grant_id.lower():
                found = True
                # Prevent grant expiring while waiting for confirmation reaction
                if grant['expiration'] - int(time.time()) <= 30:
                    embed=discord.Embed(title=":x: Error", description=f"You cannot revoke a grant that has less than 30 seconds remaining until it expires.", color=0xff0000)
                    await ctx.send(embed=embed)
                    break
                embed=discord.Embed(title=":warning: Revoke Grant", description="Are you sure you want to revoke this grant?", color=0xffff00)
                embed.add_field(name=f"Grant ID: {grant['grant_id']}", value=f"Granted to: <@{grant['target_id']}>\nRole: <@&{grant['role_id']}>\nExpires in: {self.display_time(grant['expiration'] - int(time.time()))}")
                msg = await ctx.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❌")
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) == '✅' or user == ctx.author and str(reaction.emoji) == '❌'
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30, check=check)
                if str(reaction.emoji) == "✅":
                    grant = await self.remove_grant_role(grant)
                    await self.send_grant_log(grant, True, ctx.author)
                    async with self.config.grants() as current_grants:
                        index_num = current_grants.index(grant)
                        current_grants.pop(index_num)
                    embed=discord.Embed(title="✅ Grant Revoked", description="Please check the log channel for more info.", color=0x00ff00)
                    await msg.edit(embed=embed)
                    break
                if str(reaction.emoji) == "❌":
                    embed=discord.Embed(title="❌ Cancelled", description="This grant was not revoked.", color=0x00ff00)
                    await msg.edit(embed=embed)
                    break
        if not found:
            embed=discord.Embed(title=":x: Error", description=f"A grant with that ID was not found for this server.", color=0xff0000)
            await ctx.send(embed=embed)
            return

    @commands.group()
    @commands.admin()
    async def timeroleset(self, ctx: commands.Context):
        """Manage TimeRoles settings."""

    @timeroleset.command()
    async def logchannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the log channel for role grants."""
        try:
            await channel.send("All logs for Time Roles will be sent this channel.")
        except:
            await ctx.send("I don't seem to have permissions to send messages to that channel.")
            return
        await self.config.guild(ctx.guild).log_channel.set(int(channel.id))
        await ctx.send(f"Done. All logs will now be sent to {channel.mention}.")

    @commands.group()
    @commands.admin()
    @commands.guild_only()
    async def grant(self, ctx: commands.Context):
        """Manage TimeRoles settings."""

    @grant.command()
    @commands.bot_has_permissions(embed_links=True)
    async def role(self, ctx, target: discord.Member, role: discord.Role, time_quantity: int, time_unit: str, *, reason: str = None):
        """Give a user a role for a specified amount of time. Time must be in minutes, hours, days, weeks, or months."""
        if reason == None:
            embed=discord.Embed(title=":x: Error", description=f"You must specify a reason for adding this role. This will allow the logs to be checked if there is any issues with removing the role in the future.", color=0xff0000)
            await ctx.send(embed=embed)
            return
        log_id = await self.config.guild(ctx.guild).log_channel()
        if log_id == 0:
            embed=discord.Embed(title=":x: Error", description=f"You must set a log channel using `{ctx.clean_prefix}timeroleset logchannel`. This log channel will be used to report errors and keep track of granted roles.\n\n__It is highly recommended to have these logs sent to a channel that will not be flooded with other messages!__", color=0xff0000)
            await ctx.send(embed=embed)
            return
        expires_str = await self.create_grant(ctx, target, role, time_quantity, time_unit, reason, ctx.author)
        log_channel = ctx.guild.get_channel(log_id)
        await target.add_roles(role)
        embed=discord.Embed(title="Role Added", color=0x00ff00)
        embed.add_field(name="Role", value=f"{role.mention}", inline=False)
        embed.add_field(name="Member", value=f"{target.mention}", inline=False)
        embed.add_field(name="Added by", value=f"{ctx.author.mention}", inline=False)
        embed.add_field(name="Added for", value=f"{reason}", inline=False)
        embed.add_field(name="Expires in", value=f"{expires_str}")
        embed.add_field(name="Grant ID", value=f"GID{await self.config.grant_idnum() + 1}", inline=False)
        try:
            user_msg=discord.Embed(title="Role Added", description="You have been granted a role.", color=0x00ff00)
            user_msg.add_field(name="Role", value=f"{role.name}", inline=False)
            user_msg.add_field(name="Added by", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
            user_msg.add_field(name="Reason", value=f"{reason}", inline=False)
            user_msg.set_footer(text=f"Expires in {expires_str}")
            await target.send(embed=user_msg)
        except:
            embed.set_footer("Failed to send notification to user: DMs not enabled.")
        try:
            await log_channel.send(embed=embed)
        except:
            # May want to send a message to guild owner..
            pass

    @grant.command()
    @commands.bot_has_permissions(embed_links=True)
    async def color(self, ctx, role: discord.Role, color: str, time_quantity: int, time_unit: str, *, reason: str = None):
        """Give a user a color for a specified amount of time. Time must be in minutes, hours, days, weeks, or months."""
        if reason == None:
            embed=discord.Embed(title=":x: Error", description=f"You must specify a reason for adding this role. This will allow the logs to be checked if there is any issues with removing the role in the future.", color=0xff0000)
            await ctx.send(embed=embed)
            return
        log_id = await self.config.guild(ctx.guild).log_channel()
        if log_id == 0:
            embed=discord.Embed(title=":x: Error", description=f"You must set a log channel using `{ctx.clean_prefix}timeroleset logchannel`. This log channel will be used to report errors and keep track of granted roles.\n\n__It is highly recommended to have these logs sent to a channel that will not be flooded with other messages!__", color=0xff0000)
            await ctx.send(embed=embed)
            return
        color_verify = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color)
        if color_verify:
            color = color.strip("#")
            color = f"0x{color}"
            color = int(color, 16)
        else:
            embed=discord.Embed(title=":x: Error", description=f"Invalid color. A hex code is required. Example: `#000000`", color=0xff0000)
            await ctx.send(embed=embed)
            return
        expires_str = await self.create_grant(ctx, None, role, time_quantity, time_unit, reason, ctx.author, color)
        if not expires_str:
            return
        log_channel = ctx.guild.get_channel(log_id)
        await role.edit(guild=ctx.guild, color=color)
        embed=discord.Embed(title="Color Added", color=color)
        embed.add_field(name="Role", value=f"{role.mention}", inline=False)
        embed.add_field(name="Color", value=f"{color}", inline=False)
        #embed.add_field(name="Member", value=f"{target.mention}", inline=False)
        embed.add_field(name="Added by", value=f"{ctx.author.mention}", inline=False)
        embed.add_field(name="Added for", value=f"{reason}", inline=False)
        embed.add_field(name="Expires in", value=f"{expires_str}")
        embed.add_field(name="Grant ID", value=f"GID{await self.config.grant_idnum() + 1}", inline=False)
        try:
            user_msg=discord.Embed(title="Color Added", description="One of your roles has been given a temporary color.", color=0x00ff00)
            user_msg.add_field(name="Role", value=f"{role.name}", inline=False)
            user_msg.add_field(name="Color", value=f"{color}", inline=False)
            user_msg.add_field(name="Added by", value=f"{ctx.author.name}#{ctx.author.discriminator}", inline=False)
            user_msg.add_field(name="Reason", value=f"{reason}", inline=False)
            user_msg.set_footer(text=f"Expires in {expires_str}")
            #await target.send(embed=user_msg)
        except:
            embed.set_footer("Failed to send notification to user: DMs not enabled.")
        try:
            await log_channel.send(embed=embed)
        except:
            # May want to send a message to guild owner..
            pass

    async def create_grant(self, ctx: commands.Context, target: discord.Member, role: discord.Role, quantity: int, time_unit: str, text: str, added_by: discord.User, color: int=None):
        time_unit = time_unit.lower()
        plural = ""
        if time_unit.endswith("s"):
            time_unit = time_unit[:-1]
        if quantity != 1:
            plural = "s"
        if time_unit not in self.units:
            await ctx.send("Invalid time unit. Valid time units are minutes/hours/days/weeks/months.")
            return False
        if quantity < 1:
            await ctx.send("Quantity must be greater than 0.")
            return False
        # Convert color to base 16
        before_color = str(role.color)
        before_color = before_color.strip("#")
        before_color = f"0x{before_color}"
        before_color = int(before_color, 16)
        # Get full name of time unit
        for unit_key, unit_value in self.units.items():
            if unit_value == self.units[time_unit]:
                time_unit = unit_key
                break
        seconds = self.units[time_unit] * quantity
        expiration = int(time.time() + seconds)
        expires_str = "{} {}".format(str(quantity), time_unit + plural)
        grant_num = await self.config.grant_idnum()
        await self.config.grant_idnum.set(grant_num + 1)
        # Use same system without requiring target in color command
        if target == None:
            target = role
        grant = {
            "target_id": target.id,
            "guild_id": ctx.guild.id,
            "role_id": role.id,
            "role_name": role.name,
            "color_grant": color,
            "before_color": before_color,
            "expiration": expiration,
            "expires_after": int(seconds),
            "added_time": int(time.time()),
            "reason": text,
            "added_by": added_by.id,
            "failed": "",
            "grant_id": f"GID{grant_num}"
        }
        async with self.config.grants() as grants:
            grants.append(grant)
        await ctx.send(f"Done. {role.mention} will be removed from {target.mention} in {expires_str}.")
        return expires_str

    async def remove_grant_role(self, grant):
        """Remove a role based on information saved in grants"""
        guild = self.bot.get_guild(int(grant["guild_id"]))
        member = guild.get_member(int(grant["target_id"]))
        if member is not None:
            role = discord.utils.get(guild.roles, id=int(grant["role_id"]))
            if role is not None:
                await member.remove_roles(role)
                return grant
            else:
                grant['failed'] = f"Role with ID {grant['role_id']} (previously named {grant['role_name']} and assigned to <@{grant['target_id']}>) no longer exists. This role was originally granted for the following reason: {grant['reason']}"
                return grant
        else:
            grant['failed'] = f"User with ID {grant['target_id']} is no longer in this guild."
            return grant

    async def remove_grant_color(self, grant):
        """Remove a role based on information saved in grants"""
        guild = self.bot.get_guild(int(grant["guild_id"]))
        #member = guild.get_member(int(grant["target_id"]))
        #if member is not None:
        role = discord.utils.get(guild.roles, id=int(grant["role_id"]))
        if role is not None:
            await role.edit(guild=guild, color=discord.Color(grant["before_color"]))
            #await member.edit_roles(role=role, color=discord.Color(int(grant[color_grant])))
            return grant
        else:
            grant['failed'] = f"Role with ID {grant['role_id']} (previously named {grant['role_name']} and assigned to <@{grant['target_id']}>) no longer exists. This role was originally granted for the following reason: {grant['reason']}"
            return grant
        #else:
        #    grant['failed'] = f"User with ID {grant['target_id']} is no longer in this guild."
        #    return grant

    async def send_grant_log(self, grant, revoked: bool = False, revoked_by: discord.Member = None):
        """Send a message to the log channel and the user who had the role"""
        # Compatibility
        try:
            grant["color_grant"]
        except:
            grant["color_grant"] = None
        guild = self.bot.get_guild(int(grant["guild_id"]))
        member = guild.get_member(int(grant["target_id"]))
        role = discord.utils.get(guild.roles, id=int(grant["role_id"]))
        log_id = await self.config.guild(guild).log_channel()
        log_channel = guild.get_channel(log_id)
        if grant['failed'] !="":
            embed=discord.Embed(title=":x: Failed to remove roles", description=f"{grant['failed']}", color=0xff0000)
            await log_channel.send(embed=embed)
            return
        if grant["color_grant"] != None:
            grant_type = "Color grant"
        else:
            grant_type = "Role grant"
        if revoked:
            reason = f"{grant_type} revoked by {revoked_by.mention}.\n*This role was granted {self.display_time(int(time.time())-int(grant['added_time']))} ago, and was originally set to expire after {self.display_time(int(grant['expires_after']))}.*"
            user_reason = f"{grant_type} revoked by {revoked_by.name}#{revoked_by.discriminator}.\n*This role was granted {self.display_time(int(time.time())-int(grant['added_time']))} ago, and was originally set to expire after {self.display_time(int(grant['expires_after']))}.*"
        else:
            reason = f"{grant_type} expired.\n*This role was granted {self.display_time(int(time.time())-int(grant['added_time']))} ago, and was set to expire after {self.display_time(int(grant['expires_after']))}.*"
            user_reason = f"{grant_type} expired.\n*This role was granted {self.display_time(int(time.time())-int(grant['added_time']))} ago, and was set to expire after {self.display_time(int(grant['expires_after']))}.*"
        embed=discord.Embed(title="{} Removed".format("Color" if grant["color_grant"] != None else "Role"), color=0xffff00)
        embed.add_field(name="Role", value=f"{role.mention}", inline=False)
        if grant["color_grant"] != None:
            embed.add_field(name="Color", value=f"{grant['color_grant']}", inline=False)
        else:
            embed.add_field(name="Member", value=f"{member.mention}", inline=False)
        embed.add_field(name="Added by", value=f"<@{grant['added_by']}>", inline=False)
        embed.add_field(name="Added for", value=f"{grant['reason']}", inline=False)
        embed.add_field(name="Reason", value=reason)
        if grant["color_grant"] == None:
            try:
                user_msg=discord.Embed(title="{} Removed".format("Color" if grant["color_grant"] != None else "Role"), description="A role has been removed.", color=0xffff00)
                user_msg.add_field(name="Role", value=f"{role.name}", inline=False)
                user_msg.add_field(name="Reason", value=user_reason)
                await member.send(embed=user_msg)
            except:
                embed.set_footer("Failed to send notification to user: DMs not enabled.")
        try:
            await log_channel.send(embed=embed)
        except:
            # No permissions to send to log channel
            pass
        return

    async def check_role_grants(self):
        await self.bot.wait_until_ready()
        try:
            while self.bot.get_cog("TimeRoles") == self:
                completed = []
                grants = await self.config.grants()
                for grant in grants:
                    try:
                        if int(time.time()) >= int(grant["expiration"]):
                            # Handle Legacy
                            try:
                                grant["color_grant"]
                            except KeyError:
                                grant["color_grant"] = None
                            if grant["color_grant"] == None:
                                grant = await self.remove_grant_role(grant)
                            else:
                                grant = await self.remove_grant_color(grant)
                            completed.append(grant)
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        grant['failed'] = f"User not found or insufficient permissions. Please remove <@{grant['role_id']}> manually from <@{grant['target_id']}>. This role was originally granted for the following reason: {grant['reason']}"
                        completed.append(grant)
                    except discord.errors.HTTPException:
                        pass
                    except Exception:
                        traceback.print_exc()
                if completed != []:
                    for grant in completed:
                        await self.send_grant_log(grant)
                    async with self.config.grants() as current_grants:
                        for completed_grant in completed:
                            for grant in current_grants:
                                if grant["grant_id"] == completed_grant["grant_id"]:
                                    current_grants.pop(current_grants.index(grant))
                                    break
                await asyncio.sleep(self.time)
        except Exception:
            traceback.print_exc()

    @staticmethod
    def display_time(seconds, granularity=2):
        intervals = (  # Source: from economy.py, months added
            (("months"), 2592000),
            (("weeks"), 604800),
            (("days"), 86400),
            (("hours"), 3600),
            (("minutes"), 60),
            (("seconds"), 1),
        )
        result = []
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip("s")
                result.append("{} {}".format(value, name))
        return ", ".join(result[:granularity])