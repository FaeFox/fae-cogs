import asyncio
import discord
import random
import textwrap

from PIL import Image, ImageFont, ImageDraw

from io import BytesIO
from redbot.core.data_manager import bundled_data_path


__author__ = "FaeFox"
# v1.0.1
# Added Button Compatibility to send_player_display
# TODO: Implement Siren, AI character class


class Player:
    def __init__(self, user: discord.Member, channel: discord.TextChannel, chosen_class, hp, attack, dodge, crit_chance, crit_damage) -> None:
        self.user = user
        self.channel = channel
        self.current_turn = 1
        self.move_type = ''
        self.attack_queue = []
        self.last_damage_taken = 0
        self.chosen_class = chosen_class
        self.hp = hp
        self.shield = 0
        self.max_hp = hp
        self.attack = attack
        self.dodge = dodge
        self.base_crit_chance = crit_chance
        self.crit_chance = crit_chance
        self.base_crit_damage = crit_damage
        self.crit_damage = crit_damage
        self.buffs = []
        self.debuffs = []
#move types: offensive, defensive, passive
#buff types: offensive, defensive, passive, invuln, counter, reduction, disable, stun, dot
    async def reduce_hp(self, damage, special_case: bool = False, true_damage = False):
        if special_case:
            return self.chosen_class.reduce_hp(damage)
        self.last_damage_taken = damage
        damage_str = ''
        min_hp = 0
        damage_reduction = 0
        for buff in self.buffs:
            if buff['type'] == 'invuln':
                min_hp = buff['value']
            if buff['type'] == 'reduction':
                damage_reduction = buff['value']
        if damage_reduction > 0 and not true_damage:
            damage = damage - (damage * (damage_reduction / 100))
            damage_str += f' (-{damage_reduction}%)'
        if self.shield > 0 and not true_damage:
            damage = damage - self.shield
            if damage < 0:
                damage_str += f' (**shielded** -{damage})'
                self.shield = abs(damage)
                damage = 0
            else:
                damage_str += f' (**shielded** -{self.shield})'
                self.shield = 0
        self.hp = self.hp - damage
        if self.hp < min_hp and min_hp > 0:
            damage_str += f' (**invulnerable** -{min_hp - self.hp})'
            damage = (damage - min_hp) if (damage - min_hp) > 0 else 0
            self.hp = min_hp
        if self.hp < min_hp and min_hp <= 0:
            self.hp = min_hp
        return str(damage) + damage_str

    async def heal(self, healing):
        healed_for = str(healing)
        self.hp += healing
        if self.hp > self.max_hp:
            healed_for = str(healing - (self.hp - self.max_hp))
            self.hp = self.max_hp
        return healed_for

    async def can_move(self):
        move_dict = {
            'can_move': True,
            'debuff_name': ''
        }
        for buff in self.debuffs:
            if buff["type"] == "stun":
                move_dict['can_move'] = False
                move_dict['debuff_name'] = buff['name']
                break
        return move_dict

    async def end_turn(self):
        self.current_turn += 1
        for buff in self.buffs:
            if self.current_turn == buff['active_until']:
                if buff['type'] == 'shield':
                    self.shield = 0
                self.buffs.pop(self.buffs.index(buff))
        for buff in self.debuffs:
            if self.current_turn == buff['active_until']:
                self.debuffs.pop(self.debuffs.index(buff))
        if self.current_turn > 5 and self.current_turn % 2 == 0:
            bonus_attack = int((self.current_turn - 4) / 2)
            self.attack += 1
            suddendeath_found = False
            for buff in self.buffs:
                if buff['type'] == 'internal_suddendeath':
                    buff['text'] = f"A chaotic power swells around the battlefield. Gain {bonus_attack} Attack."
                    return True
            buff = {
                "name": "Building Chaos",
                "text": f"A chaotic power swells around the battlefield. Gain {bonus_attack} Attack.",
                "type": "internal_suddendeath",
                "value": 1,
                "active_until": 9999
            }
            self.buffs.append(buff)
            return True
        return False

    async def send_player_display(self, opponent, view: discord.ui.View):
        image = Image.new('RGBA', (500, 400), (255, 0, 0, 0))
        hp_image = await self.hp_image(self, opponent)
        passive_image = await self.color_text(text=self.chosen_class.Passive(self).text)
        move1_image = await self.color_text(text=self.chosen_class.Slot1(self).text)
        move2_image = await self.color_text(text=self.chosen_class.Slot2(self).text)
        can_move = await self.can_move()
        if not can_move['can_move']:
            move_disabled = Image.open(str(bundled_data_path(self) /'move_disabled.png'))
            move1_image.paste(move_disabled, (0, 0), move_disabled)
            move2_image.paste(move_disabled, (0, 0), move_disabled)
        image.paste(hp_image, (0, 0))
        image.paste(passive_image, (0, 160))
        image.paste(move1_image, (0, 240))
        image.paste(move2_image, (0, 320))
        #return image
        temp = BytesIO() # this is a file object
        image.save(temp, format="png")
        temp.seek(0)
        embed = discord.Embed(title=f"Select a Move", description="*Text too small? Please click on the image to enlarge it.*\n*You have 60 seconds to choose a move.*", color=0xffff00) #creates embed
        embed.add_field(name=f"Buffs and Debuffs", value=f"__**YOU**__:\n{await self.build_buff_str(self)}\n\n**__Opponent__**:\n{await self.build_buff_str(opponent)}")
        embed.set_footer(text="Click the buttons below to select your move!")
        file = discord.File(temp, 'image.png')
        embed.set_image(url="attachment://image.png")
        msg = await self.channel.send(file=file, embed=embed)
        if not can_move['can_move']:
            embed=discord.Embed(title="You are stunned! (Turn skipped, Waiting on opponent...)", color=0xff0000)
            await self.channel.send(embed=embed)
            view.move1.disabled = True
            view.move2.disabled = True
            return msg
        view.move1.disabled = False
        view.move2.disabled = False
        return msg

    async def build_buff_str(self, player):
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

    async def color_text(self, text: str):
        """Generates image text with color. Uses specialized strings
        &0: Black; &1: Dark Blue; &2: Dark Green; &3: Sea foam blue; &4: Dark Red
        &5: Purple; &6: Orange; &7: Gray; &8: Dark Gray; &9: Blue; &a: Light Green;
        &b: Light Blue; &c: Red; &d Pink; &e Yellow; &f: White

        Args:
            text (str): The specially formatted text string
        """
        img_w, img_h = 350, 80
        title, text = text.split(": ")
        #start_time = time.time()
        image = Image.open(str(bundled_data_path(self) /'move_offensive.png'))
        font = ImageFont.truetype(str(bundled_data_path(self) /'pokemon_pixel_font.ttf'), size=15)
        draw = ImageDraw.Draw(image)
        title_x, title_y = 0, 10
        w, h = draw.textsize(title)
        title_x = (img_w - w)/2 + (len(title) - 5)
        x, y = 5, 90
        color_dict = {
            '0': (24,24,24),
            '1': (0,0,170),
            '2': (0,170,0),
            '3': (0,170,170),
            '4': (170,0,0),
            '5': (170,0,170),
            '6': (255,170,0),
            '7': (170,170,170),
            '8': (85,85,85),
            '9': (85,85,255),
            'a': (85,255,85),
            'b': (85,255,255),
            'c': (255,85,85),
            'd': (255,85,255),
            'e': (255,255,85),
            'f': (240,240,240)
        }
        color = (240,240,240)
        draw.text((title_x, title_y), title, fill=color, font=font, stroke_width=1, stroke_fill=(24,24,24))
        wrapped_text = textwrap.wrap(text=text, width=60)
        x, y = 5, 5
        color_change = False
        text_w, text_h = 0, 0
        total_h = 0
        for line in wrapped_text:
            w, h = draw.textsize(line)
            total_h += h
        y = (img_h - total_h)//2
        w, h = draw.textsize(wrapped_text[0])
        first_x = (img_w - w)//2 + (len(wrapped_text[0]) - 14)
        for line in wrapped_text:
            # w, h = draw.textsize(line)
            x = first_x
            text_list = line.split(' ')
            for word in text_list:
                for char in word:
                    if char == '&':
                        color_change = True
                        continue
                    if color_change:
                        color = color_dict[char]
                        color_change = False
                        continue
                    width, height = draw.textsize(char, font=font)
                    draw.text((x, y), char, fill=color, font=font, stroke_width=1, stroke_fill=(24,24,24))
                    x += width
                width, height = draw.textsize(' ', font=font)
                draw.text((x, y), ' ', fill=color, font=font, stroke_width=1, stroke_fill=(24,24,24))
                x += width
            y += height + 2
        return image

    async def hp_image(self, player1, player2, sfg=(255,176,235), bg=(240,240,240)):
            """Progress: Float 0.0 - 1.0"""
            image = Image.open(str(bundled_data_path(self) /'hp_all.png'))
            over_image = Image.open(str(bundled_data_path(self) /'hp_all.png'))
            font = ImageFont.truetype(str(bundled_data_path(self) /'pokemon_pixel_font.ttf'), size=20)
            font_italic = ImageFont.truetype(str(bundled_data_path(self) /'italicpx.ttf'), size=14)
            draw = ImageDraw.Draw(image)
            progress = player1.hp / player1.max_hp
            # HP bar width + height
            width, height = 92, 7
            # [P1] HP bar position
            x, y = 226, 119
            # [P1] HP colors
            if progress >= 0.51:
                fg=(10,255,10)
            if progress < 0.51 and progress >= 0.11:
                fg=(240, 240, 50)
            if progress < 0.11:
                fg=(240, 10, 10)
            # [P1] Draw the background
            draw.rectangle((x+(height/2), y, x+width+(height/2), y+height), fill=bg, width=10)
            draw.ellipse((x+width, y, x+height+width, y+height), fill=bg)
            draw.ellipse((x, y, x+height, y+height), fill=bg)
            # [P1] Draw shield
            shield = player1.shield / player1.max_hp
            if not progress <= 0:
                shield_width = int(width*progress + width*shield)
                draw.rectangle((x+(height/2), y, x+shield_width+(height/2), y+height), fill=sfg, width=10)
                draw.ellipse((x+shield_width, y, x+height+shield_width, y+height), fill=sfg)
                draw.ellipse((x, y, x+height, y+height), fill=sfg)
            # [P1] Draw HP
            if not progress <= 0:
                hp_width = int(width*progress)
                draw.rectangle((x+(height/2), y, x+hp_width+(height/2), y+height), fill=fg, width=10)
                draw.ellipse((x+hp_width, y, x+height+hp_width, y+height), fill=fg)
                draw.ellipse((x, y, x+height, y+height), fill=fg)
            #[P1] Paste PFP
            asset = player1.user.display_avatar.replace(size=128)
            data = BytesIO(await asset.read())
            pfp = Image.open(data)
            pfp.thumbnail((40, 40), Image.ANTIALIAS)
            image.paste(pfp, (155, 93), pfp.convert('RGBA'))

            progress = player2.hp / player2.max_hp
            # [P2] HP bar position
            x, y = 90, 35
            # [P2] Draw the background
            draw.rectangle((x+(height/2), y, x+width+(height/2), y+height), fill=bg, width=10)
            draw.ellipse((x+width, y, x+height+width, y+height), fill=bg)
            draw.ellipse((x, y, x+height, y+height), fill=bg)
            # [P2] Draw shield
            shield = player2.shield / player2.max_hp
            if not progress <= 0:
                shield_width = int(width*progress + width*shield)
                draw.rectangle((x+(height/2), y, x+shield_width+(height/2), y+height), fill=sfg, width=10)
                draw.ellipse((x+shield_width, y, x+height+shield_width, y+height), fill=sfg)
                draw.ellipse((x, y, x+height, y+height), fill=sfg)
            # [P2] Draw HP
            if not progress <= 0:
                hp_width = int(width*progress)
                draw.rectangle((x+(height/2), y, x+hp_width+(height/2), y+height), fill=fg, width=10)
                draw.ellipse((x+hp_width, y, x+height+hp_width, y+height), fill=fg)
                draw.ellipse((x, y, x+height, y+height), fill=fg)
            # [P2] Paste PFP
            asset = player2.user.display_avatar.replace(size=128)
            data = BytesIO(await asset.read())
            pfp = Image.open(data)
            pfp.thumbnail((40, 40), Image.ANTIALIAS)
            image.paste(pfp, (19, 9), pfp.convert('RGBA'))
            image.paste(over_image, (0,0), over_image)
            # [P1] Draw player name
            text = player1.user.display_name
            x, y = 231, 102
            outline = (24, 24, 24)
            # add outline
            draw.text((x-1, y-1), text, font=font, fill=outline)
            draw.text((x+1, y-1), text, font=font, fill=outline)
            draw.text((x-1, y+1), text, font=font, fill=outline)
            draw.text((x+1, y+1), text, font=font, fill=outline)
            draw.text((x-2, y-2), text, font=font, fill=outline)
            draw.text((x+2, y-2), text, font=font, fill=outline)
            draw.text((x-2, y+2), text, font=font, fill=outline)
            draw.text((x+2, y+2), text, font=font, fill=outline)
            # -----------
            draw.text((x, y), text, fill=bg, font=font)
            # [P1] Draw HP
            text = f'{player1.hp}/{player1.max_hp}'
            x, y = 255, 127
            # -----------
            draw.text((x, y), text, fill=bg, font=font_italic)
            # [P2] Draw player name
            text = player2.user.display_name
            if len(text) > 12:
                text = text[:12]
            x, y = 95, 18
            # add outline
            draw.text((x-1, y-1), text, font=font, fill=outline)
            draw.text((x+1, y-1), text, font=font, fill=outline)
            draw.text((x-1, y+1), text, font=font, fill=outline)
            draw.text((x+1, y+1), text, font=font, fill=outline)
            draw.text((x-2, y-2), text, font=font, fill=outline)
            draw.text((x+2, y-2), text, font=font, fill=outline)
            draw.text((x-2, y+2), text, font=font, fill=outline)
            draw.text((x+2, y+2), text, font=font, fill=outline)
            # -----------
            draw.text((x, y), text, fill=bg, font=font)
            # [P2] Draw HP
            text = f'{player2.hp}/{player2.max_hp}'
            x, y = 118, 44
            draw.text((x, y), text, fill=bg, font=font_italic)
            return image

class ButtonMoves(discord.ui.View):
    def __init__(self, player: Player):
        super().__init__()
        self.timeout = 60
        self.value = None
        self.player = player

    @discord.ui.button(label='Move 1', style=discord.ButtonStyle.green)
    async def move1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.player.user:
            await interaction.response.send_message('Selection locked in.', ephemeral=True)
            self.value = {'user': self.player.user, 'message': '1'}
            self.stop()
        else:
            await interaction.response.send_message("You do not have permission to use this button.")

    @discord.ui.button(label='Move 2', style=discord.ButtonStyle.grey)
    async def move2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.player.user:
            await interaction.response.send_message('Selection locked in.', ephemeral=True)
            self.value = {'user': self.player.user, 'message': '2'}
            self.stop()
        else:
            await interaction.response.send_message("You do not have permission to use this button.")

#class Siren:
#    def __init__(self) -> None:
#        self.hp = 100
#        self.attack = 9
#        self.crit_chance = 0
#        self.crit_damage = 1.25
#        self.evasion = 0
#
#    class Passive:
#        def __init__(self, player: Player) -> None:
#            self.player = player
#            self.text = "PASSIVE - Siren's Song:: Gradually invade your opponent's mind, weakening their senses and granting them 1 stack of &dVisions of Serenity &fper turn."
#
#        async def handle(self, opponent: Player):
#            current_crit = self.player.crit_chance
#            if current_crit >= int(self.player.base_crit_chance + ((1 - (self.player.hp / self.player.max_hp)) * 100)):
#                return f"**{self.player.user.display_name}'s** Battle Frenzy: **{self.player.user.display_name}** gains critical strike chance based on their missing health."
#            self.player.crit_chance = int(self.player.base_crit_chance + ((1 - (self.player.hp / self.player.max_hp)) * 100)) #store in whole number form
#            move_dict = f"**{self.player.user.display_name}'s** Battle Frenzy: **{self.player.user.display_name}** gains **{self.player.crit_chance - current_crit}% critical strike chance**. (Total {self.player.crit_chance}%, based on missing health.)"
#            return move_dict
#
#    class Slot1:
#        def __init__(self, player: Player) -> None:
#            self.player = player
#            self.priority = 1
#            self.type = 'offensive'
#            # % missing health shield value
#            self.seren_stacks = player.current_turn
#            self.text = f"@siren.abilityName.Slot1:: Charm your opponent, reducing their damage output by &b{self.seren_stacks * 5}% &f(&b+5% &fper &dVisions of Serenity &fstack). If your opponent has 10 or more &dVisions of Serenity&f stacks, &4execute &fthem."
#        async def handle(self, opponent: Player):
#            if int((1 - (self.player.hp / self.player.max_hp)) * self.shield_percent) > 0:
#                self.player.shield = int((1 - (self.player.hp / self.player.max_hp)) * self.shield_percent)
#            else:
#                return f"**{self.player.user.display_name}** used *Unwavering Will*... but it failed!"
#            buff = {
#                    "name": "Unwavering Will",
#                    "text": f"Negate {self.player.shield} damage.",
#                    "type": "shield",
#                    "value": 1,
#                    "active_until": self.player.current_turn + self.shield_duration
#                }
#            self.player.buffs.append(buff)
#            move_dict = f"**{self.player.user.display_name}** used *Unwavering Will*! **{self.player.user.display_name}** gains a shield equivalent to **{self.player.shield} health** for __{self.shield_duration} turn(s)__."
#            return move_dict
#
#    class Slot2:
#        def __init__(self, player: Player) -> None:
#            self.player = player
#            self.priority = 0
#            self.type = "offensive"
#            self.scaling_damage = 0
#            self.scale_per_use = 1
#            self.attack_percent = 100
#            self.text = f"@siren.abilityName.Slot2:: Create a soothing aura, healing both you and your opponent for 10% ()"
#
#        async def handle(self, opponent: Player):
#            """Adjusts the HP of the opposing player. Handles all operations.
#
#            Args:
#                opponent (Player): The opposing player.
#            """
#            crit_check = random.randint(1, 100)
#            dodge_check = random.randint(1, 100)
#            if dodge_check <= opponent.dodge:
#                move_text = f"**{self.player.user.display_name}** used *Reckless Swing*! The attack missed..."
#                self.player.attack += self.scale_per_use
#                return move_text
#            if crit_check <= self.player.crit_chance:
#                damage = await opponent.reduce_hp(int((self.player.attack + (self.scaling_damage)) * self.player.crit_damage))
#                move_text = f"**{self.player.user.display_name}** used *Reckless Swing*! __Critical Hit!__ **{opponent.user.display_name}** takes **{damage} damage**."
#                #opponent.last_damage_taken = damage
#                self.player.attack += self.scale_per_use
#                return move_text
#            damage = await opponent.reduce_hp(self.player.attack + self.scaling_damage)
#            move_text = f"**{self.player.user.display_name}** used *Reckless Swing*! **{opponent.user.display_name}** takes **{damage} damage**."
#            #opponent.last_damage_taken = damage
#            self.player.attack += self.scale_per_use
#            return move_text

class Berserker:
    def __init__(self) -> None:
        self.hp = 100
        self.attack = 9
        self.crit_chance = 0
        self.crit_damage = 1.25
        self.evasion = 0

    class Passive:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.name = "Battle Frenzy"
            self.text = "PASSIVE - Battle Frenzy:: Gain &e1% crit chance &ffor every &a1% missing health&f."

        async def handle(self, opponent: Player):
            current_crit = self.player.crit_chance
            if current_crit >= int(self.player.base_crit_chance + ((1 - (self.player.hp / self.player.max_hp)) * 100)):
                return f"**{self.player.user.display_name}'s** Battle Frenzy: **{self.player.user.display_name}** gains critical strike chance based on their missing health."
            self.player.crit_chance = int(self.player.base_crit_chance + ((1 - (self.player.hp / self.player.max_hp)) * 100)) #store in whole number form
            move_dict = f"**{self.player.user.display_name}'s** Battle Frenzy: **{self.player.user.display_name}** gains **{self.player.crit_chance - current_crit}% critical strike chance**. (Total {self.player.crit_chance}%, based on missing health.)"
            return move_dict

    class Slot1:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 3
            self.type = 'defensive'
            # % missing health shield value
            self.shield_percent = 30
            self.shield_duration = 2
            self.name = "Unwavering Will"
            self.text = f"Unwavering Will:: Gain a shield that &bblocks {int((1 - (player.hp / player.max_hp)) * self.shield_percent)} damage &f(&a30% missing health&f) for 2 turns. Does not stack."
        async def handle(self, opponent: Player):
            if int((1 - (self.player.hp / self.player.max_hp)) * self.shield_percent) > 0:
                self.player.shield = int((1 - (self.player.hp / self.player.max_hp)) * self.shield_percent)
            else:
                return f"**{self.player.user.display_name}** used *Unwavering Will*... but it failed!"
            buff = {
                    "name": "Unwavering Will",
                    "text": f"Negate {self.player.shield} damage.",
                    "type": "shield",
                    "value": 1,
                    "active_until": self.player.current_turn + self.shield_duration
                }
            self.player.buffs.append(buff)
            move_dict = f"**{self.player.user.display_name}** used *Unwavering Will*! **{self.player.user.display_name}** gains a shield equivalent to **{self.player.shield} health** for __{self.shield_duration} turn(s)__."
            return move_dict
        async def setup_view(self, view: discord.ui.View):
            view.move1.label = self.name
            # defensive move
            view.move1.style = discord.ButtonStyle.blurple
            view.move1.emoji = "🛡️"
            return

    class Slot2:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 0
            self.type = "offensive"
            self.scaling_damage = 0
            self.scale_per_use = 1
            self.attack_percent = 100
            self.name = "Reckless Swing"
            self.text = f"Reckless Swing:: Swing axes recklessly, dealing &6{player.attack + (self.scaling_damage)} &f(&6+{self.attack_percent}% Attack&f) &6damage&f. Gain an additional &6{self.scale_per_use} Attack &fpermanently."

        async def handle(self, opponent: Player):
            """Adjusts the HP of the opposing player. Handles all operations.

            Args:
                opponent (Player): The opposing player.
            """
            crit_check = random.randint(1, 100)
            dodge_check = random.randint(1, 100)
            if dodge_check <= opponent.dodge:
                move_text = f"**{self.player.user.display_name}** used *Reckless Swing*! The attack missed..."
                self.player.attack += self.scale_per_use
                return move_text
            if crit_check <= self.player.crit_chance:
                damage = await opponent.reduce_hp(int((self.player.attack + (self.scaling_damage)) * self.player.crit_damage))
                move_text = f"**{self.player.user.display_name}** used *Reckless Swing*! __Critical Hit!__ **{opponent.user.display_name}** takes **{damage} damage**."
                #opponent.last_damage_taken = damage
                self.player.attack += self.scale_per_use
                return move_text
            damage = await opponent.reduce_hp(self.player.attack + self.scaling_damage)
            move_text = f"**{self.player.user.display_name}** used *Reckless Swing*! **{opponent.user.display_name}** takes **{damage} damage**."
            #opponent.last_damage_taken = damage
            self.player.attack += self.scale_per_use
            return move_text
        async def setup_view(self, view: discord.ui.View):
            view.move2.label = self.name
            # offensive move
            view.move2.style = discord.ButtonStyle.green
            view.move2.emoji = "⚔️"
            return

    async def get_views(self, player):
        """Sets up how move selection buttons work. Returns `discord.ui.View`."""
        view = ButtonMoves(player)
        await self.Slot1(player).setup_view(view)
        await self.Slot2(player).setup_view(view)
        return view

class Assassin:
    def __init__(self) -> None:
        self.hp = 70
        self.attack = 12
        self.crit_chance = 30
        self.crit_damage = 1.5
        self.evasion = 0
    class Passive:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.name = "Swift Execution"
            self.text = f"PASSIVE - Swift Execution:: If your opponent is below &a20% max health &fat the end of their turn, &4execute &fthem."

        async def handle(self, opponent: Player):
            if opponent.hp / opponent.max_hp <= 0.2:
                damage = await opponent.reduce_hp(damage=opponent.max_hp, true_damage=True)
                if opponent.hp <= 0:
                    # '@' signals that new passive text must be displayed
                    return f"@**{self.player.user.display_name}** sensed weakness and __executed__ **{opponent.user.display_name}**."
            return f"**{self.player.user.display_name}'s** Swift Execution: **{self.player.user.display_name}** will show no mercy to the weak."

    class Slot1:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 3
            self.attack_ratio = 1
            self.type = 'defensive'
            self.name = "Fleeting Strike"
            self.text = f"Fleeting Strike:: If your opponent attacks, &bnegate all damage &fand deal &6{player.attack} &f(&6+{self.attack_ratio * 100}% Attack&f) &6damage&f. If your opponent does not attack, become &cStaggered&f."

        async def handle(self, opponent: Player):
            if opponent.move_type != 'offensive':
                move_text = f"**{self.player.user.display_name}** used *Fleeting Strike*, but it failed!\n**{self.player.user.display_name}** is caught off guard and becomes *Staggered*!"
                buff = {
                    "name": "Staggered",
                    "text": f"Footing is unstable. Cannot execute active abilities.",
                    "type": "stun",
                    "value": 1,
                    "active_until": self.player.current_turn + 2
                }
                self.player.debuffs.append(buff)
                return move_text
            crit_check = random.randint(1, 100)
            dodge_check = random.randint(1, 100)
            #self.player.dodge = 100
            buff = {
                    "name": "Invulnerability",
                    "text": f"Immune to all incoming damage.",
                    "type": "invuln",
                    "value": self.player.hp,
                    "active_until": self.player.current_turn + 1
                }
            self.player.buffs.append(buff)
            if dodge_check <= opponent.dodge:
                move_text = f"**{self.player.user.display_name}** used *Fleeting Strike*! The attack missed...\n**{self.player.user.display_name}** braces for an incoming attack."
                return move_text
            if crit_check <= self.player.crit_chance:
                damage = await opponent.reduce_hp(damage=int((self.player.attack * self.attack_ratio) * self.player.crit_damage))
                move_text = f"**{self.player.user.display_name}** senses an incoming attack and counter-attacks with *Fleeting Strike*! __Critical Hit!__ **{opponent.user.display_name}** takes **{damage} damage**.\n**{self.player.user.display_name}** braces for the incoming attack."
                return move_text
            damage = await opponent.reduce_hp(damage=int(self.player.attack * self.attack_ratio))
            move_text = f"**{self.player.user.display_name}** senses an incoming attack and counter-attacks with *Fleeting Strike*! **{opponent.user.display_name}** takes **{damage} damage**.\n**{self.player.user.display_name}** braces for the incoming attack."
            return move_text
        async def setup_view(self, view: discord.ui.View):
            view.move1.label = self.name
            # defensive move
            view.move1.style = discord.ButtonStyle.blurple
            view.move1.emoji = "🛡️"
            return

    class Slot2:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 1
            self.type = 'offensive'
            self.attack_ratio = 1
            #self.missing_hp_ratio = 0.25
            self.name = "Piercing Strike"
            self.text = f"Piercing Strike:: If your opponent uses a defensive move, deal &5{player.attack} &f(&5+{self.attack_ratio * 100}% Attack&f) &5true damage&f. If your opponent does not defend, become &cStaggered&f."

        async def handle(self, opponent: Player):
            if opponent.move_type != 'defensive':
                move_text = f"**{self.player.user.display_name}** used *Piercing Strike*! The attack missed...\n**{self.player.user.display_name}**'s momentum continues, causing them to become *Staggered*!"
                buff = {
                    "name": "Staggered",
                    "text": f"Footing is unstable. Cannot execute active abilities.",
                    "type": "stun",
                    "value": 1,
                    "active_until": self.player.current_turn + 2
                }
                self.player.debuffs.append(buff)
                return move_text
            crit_check = random.randint(1, 100)
            dodge_check = random.randint(1, 100)
            if dodge_check <= opponent.dodge:
                move_text = f"**{self.player.user.display_name}** used *Piercing Strike*! The attack missed..."
                return move_text
            if crit_check <= self.player.crit_chance:
                damage = await opponent.reduce_hp(damage=int((self.player.attack * self.attack_ratio) * self.player.crit_damage), true_damage=True)
                move_text = f"**{self.player.user.display_name}** used *Piercing Strike*! __Critical Hit!__ **{opponent.user.display_name}** takes **{damage} true damage**."
                return move_text
            damage = await opponent.reduce_hp(damage=int(self.player.attack * self.attack_ratio), true_damage=True)
            move_text = f"**{self.player.user.display_name}** used *Piercing Strike*! **{opponent.user.display_name}** takes **{damage} true damage**."
            return move_text
        async def setup_view(self, view: discord.ui.View):
            view.move2.label = self.name
            # offensive move
            view.move2.style = discord.ButtonStyle.green
            view.move2.emoji = "⚔️"
            return

    async def get_views(self, player):
        """Sets up how move selection buttons work. Returns `discord.ui.View`."""
        view = ButtonMoves(player)
        await self.Slot1(player).setup_view(view)
        await self.Slot2(player).setup_view(view)
        return view

class Tank:
    def __init__(self) -> None:
        self.hp = 140
        self.attack = 8
        self.crit_chance = 10
        self.crit_damage = 1.3
        self.evasion = 0
    class Passive:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.name = "Rage Shield"
            self.text = f"PASSIVE - Rage Shield:: Store &720% of damage taken &fas &cRage&f."

        async def handle(self, opponent: Player):
            rage_found = False
            for buff in self.player.buffs:
                if buff["name"] == "Rage":
                    buff["value"] += int(int(self.player.last_damage_taken) * 0.2)
                    rage_found = True
            if not rage_found:
                buff = {
                    "name": "Rage",
                    "text": f"{self.player.user.display_name}'s rage is building...",
                    "type": "passive",
                    "value": int(int(self.player.last_damage_taken) * 0.2),
                    "active_until": 9999
                }
                self.player.buffs.append(buff)
            move_dict = f"**{self.player.user.display_name}'s** Rage Shield: **{self.player.user.display_name}** is building **Rage**..."
            return move_dict

    class Slot1:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 3
            self.type = 'defensive'
            self.name = "Iron Will"
            self.text = f"Iron Will:: If the next hit would kill you, survive instead with &a1 HP&f. Cannot be used consecutively."

        async def handle(self, opponent: Player):
            faltering_will_found = False
            for debuff in self.player.debuffs:
                if debuff["name"] == "Faltering Will":
                    faltering_will_found = True
            if not faltering_will_found:
                buff = {
                    "name": "Iron Will",
                    "text": f"{self.player.user.display_name}'s HP cannot be reduced below **1**.",
                    "type": "invuln",
                    "value": 1,
                    "active_until": self.player.current_turn + 1
                }
                self.player.buffs.append(buff)
                buff = {
                    "name": "Faltering Will",
                    "text": f"Iron Will cannot be applied.",
                    "type": "disable",
                    "value": 1,
                    "active_until": self.player.current_turn + 2
                }
                self.player.debuffs.append(buff)
                move_dict = f"**{self.player.user.display_name}** used *Iron Will*! **{self.player.user.display_name}** gains the *Iron Will* buff for __1 turn(s)__."
                return move_dict
            move_dict = f"**{self.player.user.display_name}** used *Iron Will*! ...nothing happens."
            return move_dict
        async def setup_view(self, view: discord.ui.View):
            view.move1.label = self.name
            # defensive move
            view.move1.style = discord.ButtonStyle.blurple
            view.move1.emoji = "🛡️"
            return

    class Slot2:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 2
            self.type = 'offensive'
            # set to 0 if passive not initialized yet
            self.rage = 0 if player.buffs == [] else player.buffs[0]["value"]
            self.name = "Furious Bash"
            self.text = f"Furious Bash:: Consume stored &cRage&f, dealing &6{int(self.player.attack * 0.5 + self.rage)} &f(&6+50% Attack&f, &c+100% Rage&f) &6damage &fand restoring &a{self.rage} &f(&c+100% Rage&f) &ahealth &fto yourself."

        async def handle(self, opponent: Player):
            crit_check = random.randint(1, 100)
            dodge_check = random.randint(1, 100)
            if dodge_check <= opponent.dodge:
                move_text = f"**{self.player.user.display_name}** used *Furious Bash*! The attack missed...\n**{self.player.user.display_name}** restores **{await self.player.heal(self.rage)} health**."
                for buff in self.player.buffs:
                    if buff["name"] == "Rage":
                        buff["value"] = 0
                return move_text
            if crit_check <= self.player.crit_chance:
                damage = await opponent.reduce_hp(int((self.player.attack * 0.5) * self.player.crit_damage))
                move_text = f"**{self.player.user.display_name}** used *Furious Bash*! __Critical Hit!__ **{opponent.user.display_name}** takes **{damage} damage**.\n**{self.player.user.display_name}** restores **{await self.player.heal(self.rage)} health**."
                #opponent.last_damage_taken = damage
                for buff in self.player.buffs:
                    if buff["name"] == "Rage":
                        buff["value"] = 0
                return move_text
            damage = await opponent.reduce_hp(int((self.player.attack * 0.5) + self.rage))
            move_text = f"**{self.player.user.display_name}** used *Furious Bash*! **{opponent.user.display_name}** takes **{damage} damage**.\n**{self.player.user.display_name}** restores **{await self.player.heal(self.rage)} health**."
            #opponent.last_damage_taken = damage
            for buff in self.player.buffs:
                if buff["name"] == "Rage":
                    buff["value"] = 0
            return move_text
        async def setup_view(self, view: discord.ui.View):
            view.move2.label = self.name
            # offensive move
            view.move2.style = discord.ButtonStyle.green
            view.move2.emoji = "⚔️"
            return

    async def get_views(self, player):
        """Sets up how move selection buttons work. Returns `discord.ui.View`."""
        view = ButtonMoves(player)
        await self.Slot1(player).setup_view(view)
        await self.Slot2(player).setup_view(view)
        return view


class Boss1:
    def __init__(self) -> None:
        self.hp = 260
        self.attack = 8
        self.crit_chance = 10
        self.crit_damage = 1.3
        self.evasion = 0
        self.queued_move = []
    class Passive:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.text = f"Expert in disruption magic."

        async def handle(self, opponent: Player):
            rage_found = False
            for buff in self.player.buffs:
                if buff["name"] == "Rage":
                    buff["value"] += int(int(self.player.last_damage_taken) * 0.2)
                    rage_found = True
            if not rage_found:
                buff = {
                    "name": "Rage",
                    "text": f"{self.player.user.display_name}'s rage is building...",
                    "type": "passive",
                    "value": int(int(self.player.last_damage_taken) * 0.2),
                    "active_until": 9999
                }
                self.player.buffs.append(buff)
            move_dict = f"**{self.player.user.display_name}'s** Rage Shield: **{self.player.user.display_name}** is building **Rage**..."
            return move_dict

    class Slot1:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 3
            self.type = 'defensive'
            self.text = f"Absorb:: Opponent gains 50% critical strike chance. Upon crit, heal for the damage dealt instead of taking damage."

        async def handle(self, opponent: Player):
            faltering_will_found = False
            for debuff in self.player.debuffs:
                if debuff["name"] == "Faltering Will":
                    faltering_will_found = True
            if not faltering_will_found:
                buff = {
                    "name": "Iron Will",
                    "text": f"{self.player.user.display_name}'s HP cannot be reduced below **1**.",
                    "type": "invuln",
                    "value": 1,
                    "active_until": self.player.current_turn + 1
                }
                self.player.buffs.append(buff)
                buff = {
                    "name": "Faltering Will",
                    "text": f"Iron Will cannot be applied.",
                    "type": "disable",
                    "value": 1,
                    "active_until": self.player.current_turn + 2
                }
                self.player.debuffs.append(buff)
                move_dict = f"**{self.player.user.display_name}** used *Iron Will*! **{self.player.user.display_name}** gains the *Iron Will* buff for __1 turn(s)__."
                return move_dict
            move_dict = f"**{self.player.user.display_name}** used *Iron Will*! ...nothing happens."
            return move_dict

    class Slot2:
        def __init__(self, player: Player) -> None:
            self.player = player
            self.priority = 2
            self.type = 'offensive'
            # set to 0 if passive not initialized yet
            self.rage = 0 if player.buffs == [] else player.buffs[0]["value"]
            self.text = f"Furious Bash:: Consume stored &cRage&f, dealing &6{int(self.player.attack * 0.5 + self.rage)} &f(&6+50% Attack&f, &c+100% Rage&f) &6damage &fand restoring &a{self.rage} &f(&c+100% Rage&f) &ahealth &fto yourself."

        async def handle(self, opponent: Player):
            crit_check = random.randint(1, 100)
            dodge_check = random.randint(1, 100)
            if dodge_check <= opponent.dodge:
                move_text = f"**{self.player.user.display_name}** used *Furious Bash*! The attack missed...\n**{self.player.user.display_name}** restores **{await self.player.heal(self.rage)} health**."
                for buff in self.player.buffs:
                    if buff["name"] == "Rage":
                        buff["value"] = 0
                return move_text
            if crit_check <= self.player.crit_chance:
                damage = await opponent.reduce_hp(int((self.player.attack * 0.5) * self.player.crit_damage))
                move_text = f"**{self.player.user.display_name}** used *Furious Bash*! __Critical Hit!__ **{opponent.user.display_name}** takes **{damage} damage**.\n**{self.player.user.display_name}** restores **{await self.player.heal(self.rage)} health**."
                #opponent.last_damage_taken = damage
                for buff in self.player.buffs:
                    if buff["name"] == "Rage":
                        buff["value"] = 0
                return move_text
            damage = await opponent.reduce_hp(int((self.player.attack * 0.5) + self.rage))
            move_text = f"**{self.player.user.display_name}** used *Furious Bash*! **{opponent.user.display_name}** takes **{damage} damage**.\n**{self.player.user.display_name}** restores **{await self.player.heal(self.rage)} health**."
            #opponent.last_damage_taken = damage
            for buff in self.player.buffs:
                if buff["name"] == "Rage":
                    buff["value"] = 0
            return move_text
