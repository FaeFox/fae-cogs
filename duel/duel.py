import asyncio
import logging
import time
import discord

from redbot.core import Config, commands, checks
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

from .game_classes import Player, Assassin, Tank, Berserker

__author__ = "FaeFox"

class Duel(commands.Cog):
    """Duel Game by FaeFox"""

    def __init__(self, bot):
        """Set up the plugin."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 18299301857102)
        self.config.register_guild(
            p1_channel_id = 0,
            p2_channel_id = 0,
            p1_role_id = 0,
            p2_role_id = 0
        )
        self.config.register_member(
            chosen_class = 'default'
        )
        #star breaker, suguri, mio

    def get_priority(self, move):
        return move['attack'].priority

    @commands.group(autohelp=True)
    @commands.guild_only()
    async def gameset(self, ctx):
        """Setup roles and channels"""
        pass

    @gameset.command(name="setup")
    @checks.admin_or_permissions(manage_server=True)
    async def gameset_setup(self, ctx: commands.Context, p1_role: discord.Role, p2_role: discord.Role):
        """Set up the game channels and roles."""
        await self.config.guild(ctx.guild).p1_role_id.set(p1_role.id)
        await self.config.guild(ctx.guild).p2_role_id.set(p2_role.id)

        p1_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True),
            p2_role: discord.PermissionOverwrite(read_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        p2_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True),
            p1_role: discord.PermissionOverwrite(read_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        p1_channel = await ctx.guild.create_text_channel("p1", overwrites=p1_overwrites)
        p2_channel = await ctx.guild.create_text_channel("p2", overwrites=p2_overwrites)
        await self.config.guild(ctx.guild).p1_channel_id.set(p1_channel.id)
        await self.config.guild(ctx.guild).p2_channel_id.set(p2_channel.id)
        await ctx.send(f"Setup complete. Two new channels were created ({p1_channel.mention}, {p2_channel.mention}). You can now move these channels to any category you wish to have them in.")
        pass

    @gameset.command(name="class")
    async def gameset_class(self, ctx: commands.Context):
        """Set the class you want to play."""
        def check(message: discord.Message):
            if message.content in ['tank', 'berserker', 'assassin'] and message.author == ctx.author:
                return True
            return False
        # wait for player responses
        try:
            embed=discord.Embed(title="Choose a Class", description="Please type the name of the class that you would like to play.\nValid responses: Tank, Berserker, Assassin\n\n*Note: Each class has its own move set. Please view classes using `,showclasses` before choosing.*", color=0x00ff00)
            await ctx.send(embed=embed)
            message = await self.bot.wait_for('message', check=check, timeout=60)
        except:
            await ctx.send('Command timed out.')
        await self.config.member(ctx.author).chosen_class.set(f"{message.content.lower()}")
        embed=discord.Embed(title="✅Class set", description=f"You have chosen the {message.content.title()} class.\n\nPlease note that each class has its own move set. __Please use `,showclasses {message.content.lower()}` at least once before participating.__ There will be limited time for reading during the move selection period.", color=0x00ff00)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def duel(self, ctx: commands.Context, target: discord.Member):
        p1_channel_id = await self.config.guild(ctx.guild).p1_channel_id()
        p2_channel_id = await self.config.guild(ctx.guild).p2_channel_id()
        p1_role_id = await self.config.guild(ctx.guild).p1_role_id()
        p2_role_id = await self.config.guild(ctx.guild).p2_role_id()

        class_dict = {
            "tank": Tank(),
            "berserker": Berserker(),
            "assassin": Assassin()
        }
        p1_class_name = await self.config.member(ctx.author).chosen_class()
        p2_class_name = await self.config.member(target).chosen_class()
        if p1_class_name == 'default' or p2_class_name == 'default':
            embed=discord.Embed(title=":x: Requirements not met", description=f"Players must select their class using `,gameset class` before continuing.", color=0x00ff00)
            await ctx.send(embed=embed)
            return
        chosen_class = class_dict[p1_class_name]
        chosen_class_2 = class_dict[p2_class_name]
        # TEMP: Get Test Channels
        try:
            p1channel = discord.utils.get(ctx.guild.channels, id=p1_channel_id)
            p2channel = discord.utils.get(ctx.guild.channels, id=p2_channel_id)
        except:
            embed=discord.Embed(title=":x: Error", description=f"The channels used for each player during the game couldn't be found. Please run `{ctx.clean_prefix}gameset setup` and try again.", color=0x00ff00)
            await ctx.send(embed=embed)
            return
        try:
            p1_role = discord.utils.get(ctx.guild.roles, id=p1_role_id)
            p2_role = discord.utils.get(ctx.guild.roles, id=p2_role_id)
        except:
            embed=discord.Embed(title=":x: Error", description=f"The player 1 and player 2 roles could not be found. Set them up with `{ctx.clean_prefix}gameset setup` and try again.", color=0x00ff00)
            await ctx.send(embed=embed)
            return
        await ctx.author.add_roles(p1_role)
        await target.add_roles(p2_role)
        embed=discord.Embed(title="Starting Soon", description=f"{ctx.author.mention} - Please use {p1channel.mention}\n\n{target.mention} - Please use {p2channel.mention}", color=0x00ff00)
        msg = await ctx.send(embed=embed)
        p1embed=discord.Embed(title="Starting Soon", description=f"You will input all of your move choices here.", color=0x00ff00)
        await p1channel.send(embed=p1embed)
        await p2channel.send(embed=p1embed)
        # [SLEEP]: Game load player reading
        await asyncio.sleep(5)
        # Initialize Players
        player1 = Player(ctx.author, p1channel, chosen_class, chosen_class.hp, chosen_class.attack, chosen_class.evasion, chosen_class.crit_chance, chosen_class.crit_damage)
        player2 = Player(target, p2channel, chosen_class_2, chosen_class_2.hp, chosen_class_2.attack, chosen_class_2.evasion, chosen_class_2.crit_chance, chosen_class_2.crit_damage)
        # Create player move selectors
        # TODO: Implement buttons or select menus
        # Initialize Player Passives
        #await Berserker.Passive(player1).handle()
        player1_passive = await player1.chosen_class.Passive(player1).handle(player2)
        player2_passive = await player2.chosen_class.Passive(player2).handle(player1)
        # p1 message
        embed = discord.Embed(title=f"Passives", description=f"{player1_passive}\n\n{player2_passive}", color=0x000fff)
        embed.add_field(name=f"{player2.user.display_name}'s stats", value=f"HP: {player2.hp}/{player2.max_hp}\nAttack: {player2.attack}\nCrit Chance: {player2.crit_chance}\n\n{await self.build_buff_str(player2)}", inline=False)
        embed.add_field(name=f"**Your** stats", value=f"HP: {player1.hp}/{player1.max_hp}\nAttack: {player1.attack}\nCrit Chance: {player1.crit_chance}\n\n{await self.build_buff_str(player1)}", inline=False)
        await player1.channel.send(embed=embed)
        # p2 message
        embed = discord.Embed(title=f"Passives", description=f"{player1_passive}\n\n{player2_passive}", color=0x000fff)
        embed.add_field(name=f"{player1.user.display_name}'s stats", value=f"HP: {player1.hp}/{player1.max_hp}\nAttack: {player1.attack}\nCrit Chance: {player1.crit_chance}\n\n{await self.build_buff_str(player1)}", inline=False)
        embed.add_field(name=f"**Your** stats", value=f"HP: {player2.hp}/{player2.max_hp}\nAttack: {player2.attack}\nCrit Chance: {player2.crit_chance}\n\n{await self.build_buff_str(player2)}", inline=False)
        await player2.channel.send(embed=embed)
        # [SLEEP]: Passive reading
        await asyncio.sleep(10)
        # announce sudden death
        chaos_announced = False
        # BATTLE LOOP
        while player1.hp > 0 and player2.hp > 0:
            attack_queue = []
            attack_selected = []
            player_moved = []
            # select moves
            # p1 message
            await player1.send_player_display(player2)
            # p2 message
            await player2.send_player_display(player1)
            # handle stunned players
            player1_can_move = await player1.can_move()
            player2_can_move = await player2.can_move()
            if not player1_can_move['can_move']:
                attack_selected.append({'user': player1.user, 'message': 'stunned'})
            if not player2_can_move['can_move']:
                attack_selected.append({'user': player2.user, 'message': 'stunned'})
            # check if both players stunned
            if len(attack_selected) < 2:
                # check for valid messages
                def check(message: discord.Message):
                    if ((message.channel == player1.channel or message.channel == player2.channel) and message.content.lower() in ['1', '2', 'ability 1', 'ability 2']) and message.author not in player_moved:
                        # Prevent double attack queue
                        attack_selected.append({'user': message.author, 'message': message.content})
                        player_moved.append(message.author)
                        # Notify user that attack was selected
                        if len(attack_selected) == 1:
                            embed=discord.Embed(title="Waiting on opponent...", color=0xffff00)
                            asyncio.get_running_loop().create_task(message.channel.send(embed=embed))
                        # Wait for both players to queue attack
                        if len(attack_selected) == 2:
                            return True
                    return False
                # wait for player responses
                try:
                    task = asyncio.get_running_loop().create_task(self.warn_before_timeout(attack_list=attack_selected, player1=player1, player2=player2, timeout_len=60), name='TimeoutWarning')
                    await self.bot.wait_for('message', check=check, timeout=60)
                    task.cancel()
                # if either player times out, automatically force them to use their slot 1 ability
                except asyncio.exceptions.TimeoutError:
                    player_list = []
                    for item in attack_selected:
                        player_list.append(item['user'])
                    if player1.user not in player_list:
                        attack_selected.append({'user': player1.user, 'message': '1'})
                    if player2.user not in player_list:
                        attack_selected.append({'user': player2.user, 'message': '1'})
                except Exception:
                    # this should never happen
                    logging.exception("FATAL ERROR")
                    await ctx.send(f"A fatal exception has occurred.\n\nBattle Cancelled.")
                    break
                    embed = discord.Embed(title=f"The air crackles with power... you are filled with paralyzing terror, and are unable to move... (Skipping Turn)", color=0xff0000)
                    await player1.channel.send(embed=embed)
                    await player2.channel.send(embed=embed)
                    await player1.end_turn()
                    await player2.end_turn()
                    continue
            else:
                # both players stunned
                embed = discord.Embed(title=f"Both players are stunned! Well this is awkward... don't worry, I won't tell anyone... well other than anyone who's watching. (Skipping Turn)", color=0xff0000)
                await player1.channel.send(embed=embed)
                await player2.channel.send(embed=embed)
                await player1.end_turn()
                await player2.end_turn()
                continue
            # convert player choices into attack classes
            for attack in attack_selected:
                # convert p1
                if attack['user'] == player1.user:
                    if attack['message'] == 'stunned':
                        # keeps last move type
                        pass
                    elif attack['message'][-1] == '1':
                        attack_queue.append({'attack': player1.chosen_class.Slot1(player1), 'opponent': player2})
                        # save type 'offensive' or 'defensive' to player class
                        player1.move_type = player1.chosen_class.Slot1(player1).type
                    elif attack['message'][-1] == '2':
                        attack_queue.append({'attack': player1.chosen_class.Slot2(player1), 'opponent': player2})
                        player1.move_type = player1.chosen_class.Slot2(player1).type
                    else:
                        embed = discord.Embed(title=f"Your resolve suddenly drains, causing your attack to fail... (Invalid Selection... wait how did you get here? This shouldn't be possible!)", color=0xff0000)
                        await player1.channel.send(embed=embed)
                # convert p2
                if attack['user'] == player2.user:
                    if attack['message'] == 'stunned':
                        # keeps last move type
                        pass
                    elif attack['message'][-1] == '1':
                        attack_queue.append({'attack': player2.chosen_class.Slot1(player2), 'opponent': player1})
                        player2.move_type = player2.chosen_class.Slot1(player2).type
                    elif attack['message'][-1] == '2':
                        attack_queue.append({'attack': player2.chosen_class.Slot2(player2), 'opponent': player1})
                        player2.move_type = player2.chosen_class.Slot2(player2).type
                    else:
                        embed = discord.Embed(title=f"Your resolve suddenly drains, causing your attack to fail... (Invalid Selection... wait how did you get here? This shouldn't be possible!)", color=0xff0000)
                        await player2.channel.send(embed=embed)
            # sort attacks by priority number
            attack_queue.sort(key=self.get_priority, reverse=True)
            move_text_complete = '** **'
            # send empty attack message
            embed = discord.Embed(title=f"Attack", description=move_text_complete, color=0x00ff00)
            msg1 = await player1.channel.send(embed=embed)
            msg2 = await player2.channel.send(embed=embed)
            move_text_complete = ''
            # handle attack, edit message
            for attack in attack_queue:
                move_text = await attack['attack'].handle(attack['opponent'])
                move_text_complete += f'{move_text}\n\n'
                embed = discord.Embed(title=f"Attack", description=move_text_complete, color=0x00ff00)
                # display stunned message, cancel second attack in queue
                if not (await attack['opponent'].can_move())['can_move']:
                    await asyncio.sleep(1)
                    move_text_complete += f'**{attack["opponent"].user.display_name}** got stunned and can\'t move!'
                    embed = discord.Embed(title=f"Attack", description=move_text_complete, color=0x00ff00)
                    await msg1.edit(embed=embed)
                    await msg2.edit(embed=embed)
                    break
                await msg1.edit(embed=embed)
                await msg2.edit(embed=embed)
                # display death message, cancel second attack in queue
                if attack['opponent'].hp <= 0:
                    move_text_complete += f'**{attack["opponent"].user.display_name}** died!'
                    embed = discord.Embed(title=f"Attack", description=move_text_complete, color=0x00ff00)
                    await msg1.edit(embed=embed)
                    await msg2.edit(embed=embed)
                    break
                await asyncio.sleep(3)
            # end turns and check chaos status
            chaos = await player1.end_turn()
            await player2.end_turn()
            # handle passives
            player1_passive = await player1.chosen_class.Passive(player1).handle(player2)
            player2_passive = await player2.chosen_class.Passive(player2).handle(player1)
            # '@' indicates an important passive message
            # display any passive string that starts with '@'
            if player1_passive[0] == '@':
                embed = discord.Embed(title=f"Passive", description=player1_passive[1:], color=0x00ff00)
                await player1.channel.send(embed=embed)
                await player2.channel.send(embed=embed)
            if player2_passive[0] == '@':
                embed = discord.Embed(title=f"Passive", description=player2_passive[1:], color=0x00ff00)
                await player1.channel.send(embed=embed)
                await player2.channel.send(embed=embed)
            # skip chaos if either player dies
            if player1.hp <= 0 or player2.hp <= 0:
                continue
            # 'Chaos' is an attack power increase that discourages games from continuing for too long
            # if chaos is active, display notification message
            if chaos:
                if not chaos_announced:
                    embed = discord.Embed(title=f"Chaos", description="A chaotic power swells around the battlefield! (*Attack* is increased.)", color=0xFF69B4)
                    chaos_announced = True
                else:
                    embed = discord.Embed(title=f"Chaos", description="The chaotic power grows stronger... (*Attack* is increased.)", color=0xFF69B4)
                await player1.channel.send(embed=embed)
                await player2.channel.send(embed=embed)
                await asyncio.sleep(2)
        # display winning message
        # TODO: Add 'winning' description
        if player1.hp >= 1:
            embed = discord.Embed(title="You Win!", description=f'placehold')
            embed.set_footer(text=f"Your HP: {player1.hp} | Opponent HP: {player2.hp}")
            await player1.channel.send(embed=embed)
            embed=discord.Embed(title="Game Over", color=0xff0000)
            embed.set_image(url='https://media.giphy.com/media/TbONGqAdpTWQW3Hz5V/giphy.gif')
            embed.set_footer(text=f"Your HP: {player2.hp} | Opponent HP: {player1.hp}")
            await player2.channel.send(embed=embed)
            return
        if player2.hp >= 1:
            embed = discord.Embed(title="You Win!", description=f'placehold')
            embed.set_footer(text=f"Your HP: {player2.hp} | Opponent HP: {player1.hp}")
            await player2.channel.send(embed=embed)
            embed=discord.Embed(title="Game Over", color=0xff0000)
            embed.set_image(url='https://media.giphy.com/media/TbONGqAdpTWQW3Hz5V/giphy.gif')
            embed.set_footer(text=f"Your HP: {player1.hp} | Opponent HP: {player2.hp}")
            await player1.channel.send(embed=embed)
            return

    async def warn_before_timeout(self, attack_list: list, player1: Player, player2: Player, timeout_len: int):
        """Asynchronous scheduled task. Used to warn a user when their window to select a move will end soon.

        Args:
            attack_list (list): Sorted list of all players and their selected attacks, if any.
            player1 (Player): User in the first slot.
            player2 (Player): User in the second slot.
            timeout_len (int): The time window (in seconds) that each player has to select a move.
        """
        # sleep until 10 seconds before the timeout window is reached
        await asyncio.sleep(timeout_len - 10)
        player_list = []
        for item in attack_list:
            player_list.append(item['user'])
        # send message to player channels for each player who has not selected a move
        embed=discord.Embed(title="⌛ 10 seconds remaining to pick!", color=0xff0000)
        if player1.user not in player_list:
            await player1.channel.send(embed=embed)
        if player2.user not in player_list:
            await player2.channel.send(embed=embed)

    async def build_buff_str(self, player: Player):
        """Builds the string of buffs and debuffs which is displayed for each player.

        Args:
            player (Player): The user for which the string is built for.

        Returns:
            str: Displayed buff string.
        """
        buff_str = ''
        if player.buffs != []:
            buff_str += '**__Buffs:__**\n'
            for buff in player.buffs:
                active_str = ''
                if int(buff['active_until']) < 5000:
                    active_str = f" (Active for __{buff['active_until'] - player.current_turn} turns__)"
                buff_str += f"**{buff['name']}**: {buff['text']}{active_str}\n"
        if player.debuffs != []:
            buff_str += '**__Debuffs:__**\n'
            for buff in player.debuffs:
                active_str = ''
                if int(buff['active_until']) < 5000:
                    active_str = f" (Active for __{buff['active_until'] - player.current_turn} turns__)"
                buff_str += f"**{buff['name']}**: {buff['text']}{active_str}\n"
        if buff_str == '':
            return 'None'
        return buff_str

    async def uncurse_text(self, text: str):
        """Removes color formatting from strings and replaces it with bold text.

        Args:
            text (str): The color formatted string.

        Returns:
            str: Readable text string with bold formatting.
        """
        text = text.replace(": ", " ")
        new_str = ''
        color_change = False
        for char in text:
            if char == '&':
                color_change = True
                continue
            if not color_change:
                    new_str += char
            if color_change:
                new_str += '**'
                color_change = False
        return new_str

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def showclasses(self, ctx):
        """Show classes for the duel game."""
        page_num = 0
        class_list = [Assassin(), Berserker(), Tank()]
        embed_list = []
        for game_class in class_list:
            player = Player(ctx.author, discord.utils.get(ctx.guild.channels, id=990363873624350752), game_class, game_class.hp, game_class.attack, game_class.evasion, game_class.crit_chance, game_class.crit_damage)
            page_num += 1
            start_time = time.time()
            embed = discord.Embed(title=f"{game_class.__class__.__name__}", description=f"Showing information about the {game_class.__class__.__name__} class.", color=0x00ff00) #creates embed
            embed.add_field(
                name='Stats',
                value=f"HP: {game_class.hp}\nAttack: {game_class.attack}\nCrit Chance: {game_class.crit_chance}%\nCrit Multiplier: {game_class.crit_damage*100}%\nEvasion: {game_class.evasion}",
                inline=False
            )
            # remove color formatting with 'uncurse_text' function before sending
            embed.add_field(
                name='Passive',
                value=await self.uncurse_text(game_class.Passive(player).text),
                inline=False
            )
            embed.add_field(
                name='Ability 1',
                value=await self.uncurse_text(game_class.Slot1(player).text),
                inline=False
            )
            embed.add_field(
                name='Ability 2',
                value=await self.uncurse_text(game_class.Slot2(player).text),
                inline=False
            )
            embed.set_footer(text=f"Showing class {page_num} of {len(class_list)} | Debug: {round(time.time() - start_time, 2)}")
            embed_list.append(embed)
        if len(embed_list) == 1:
            await ctx.send(embed=embed_list[0])
        else:
            await menu(ctx, embed_list, DEFAULT_CONTROLS)
