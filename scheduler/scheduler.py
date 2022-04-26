import asyncio
import calendar
import traceback
import discord
import typing
import datetime
import time

from typing import Any

from discord import app_commands

from redbot.core import Config, commands

Cog: Any = getattr(commands, "Cog", object)

config = Config.get_conf(
    cog_instance=None, identifier=62361398061272756, force_registration=True, cog_name="Scheduler"
)

global_defaults = {
    'reminders': [],
    'reminder_id': 1,
    'max_reminders': 24
}

config.register_global(**global_defaults)
config.register_user(
   failed_reminders=[]
)

def display_time(seconds, granularity=1):
    # Source: economy.py
    intervals = (
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
    if ", ".join(result[:granularity]) == "1 day":
        return "day"
    return ", ".join(result[:granularity])

class Scheduler(commands.Cog):
    """
    Get scheduled reminders.
    """
    def __init__(self, bot):
        """Set up the plugin."""
        super().__init__()
        self.bot = bot
        self.time = 10
        self.task = self.bot.loop.create_task(self.check_reminders())

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    async def send_reminder(self, reminder):
        try:
            user = discord.utils.get(self.bot.get_all_members(), id=reminder["user_id"])
            if user is not None:
                if reminder['recurring']:
                    await user.send(f"Hello! You previously asked me to remind you to {reminder['reminder_text']}.\nYou've asked me to remind you of this every {display_time(reminder['recurs_every'])}, so I'll remind you of this again on <t:{reminder['next_reminder'] + reminder['recurs_every']}:F>.")
                else:
                    await user.send(f"Hello! {display_time(reminder['next_reminder']-reminder['set_time'])} ago, you asked me to remind you to {reminder['reminder_text']}.")
                return reminder
            else:
                reminder['failed_count'] = 1
                return reminder
        except:
            # Debug
            traceback.print_exc()
            return reminder

    async def check_reminders(self):
        await self.bot.wait_until_ready()
        try:
            while self.bot.get_cog("Scheduler") == self:
                completed = []
                reminders = await config.reminders()
                for reminder in reminders:
                    try:
                        if int(time.time()) >= int(reminder["next_reminder"]):
                            reminder = await self.send_reminder(reminder)
                            completed.append(reminder)
                    except (discord.errors.Forbidden, discord.errors.NotFound):
                        # Could not find user or DMs disabled, remove reminder
                        completed.append(reminder)
                    except discord.errors.HTTPException:
                        pass
                    except Exception:
                        # Debug
                        traceback.print_exc()
                if completed != []:
                    async with config.reminders() as current_reminders:
                        for completed_reminder in completed:
                            for reminder in current_reminders:
                                if reminder["reminder_id"] == completed_reminder["reminder_id"]:
                                    current_reminders.pop(current_reminders.index(reminder))
                                    if completed_reminder['recurring'] and completed_reminder['failed_count'] < 1:
                                        completed_reminder['next_reminder'] += completed_reminder['recurs_every']
                                        current_reminders.append(completed_reminder)
                                    break
                await asyncio.sleep(self.time)
        except Exception:
            traceback.print_exc()

class Schedule(app_commands.Group):
    """Add, remove, and show schedule reminders."""

    async def autocomplete_date(self, interaction: discord.Interaction, current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
        date_obj = datetime.date.today()
        last_day = calendar.monthrange(date_obj.year, date_obj.month)[1]
        curr_day = (calendar.weekday(date_obj.year, date_obj.month, date_obj.day)) + 1
        if curr_day >= 7:
            curr_day = 0
        weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        autocomplete_list = []
        year_int = date_obj.year
        month_int = date_obj.month
        for i in range(7):
            day_int = date_obj.day + i
            if day_int > last_day:
                # subtract last_day to roll over into next month
                day_int -= last_day
                month_int = date_obj.month + 1
                # roll over year + month counters
                if month_int > 12:
                    year_int = date_obj.year + 1
                    month_int = 1
            if curr_day + i >= 7:
                curr_day -= 7
            date_dict = {
                "weekday_name": weekdays[curr_day + i],
                "date_str": f"{day_int}/{month_int}/{year_int}"
            }
            autocomplete_list.append(date_dict)
        return [
            app_commands.Choice(name=date_dict["weekday_name"], value=date_dict["date_str"])
            for date_dict in autocomplete_list
        ]

    async def autocomplete_id(self, interaction: discord.Interaction, current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
        user_reminders = []
        for event in await config.reminders():
            if event['user_id'] == interaction.user.id:
                user_reminders.append(event)
        return [
            app_commands.Choice(name=f"[{reminder['reminder_id']}]: '{reminder['reminder_text'] if len(reminder['reminder_text']) < 23 else reminder['reminder_text'][:20] + '...'}'", value=reminder['reminder_id'])
            for reminder in user_reminders
        ][:25]

    async def autocomplete_repeat(self, interaction: discord.Interaction, current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
        day_len = 86400
        suggested_values = [
                ('Day', day_len),
                ('2 days', day_len*2),
                ('3 days', day_len*3),
                ('4 days', day_len*4),
                ('5 days', day_len*5),
                ('6 days', day_len*6),
                ('Week', day_len*7),
                ('2 weeks', day_len*14),
                ('4 weeks', day_len*28)
        ]
        return [
            app_commands.Choice(name=f"{value[0]}", value=value[1])
            for value in suggested_values
        ]

    @app_commands.command()
    @app_commands.autocomplete(weekday=autocomplete_date, repeat_every=autocomplete_repeat)
    @app_commands.describe(weekday="The day of the week you want to schedule a reminder for.", reminder_time="The time you want to be reminded at. Format is HH:MM in the 24 hour format.", reminder_text="The message you want to be sent when this reminder is sent.", repeat_every="How often you should be sent this reminder")
    async def add(self, interaction: discord.Interaction, weekday: str, reminder_time: str, reminder_text: str, repeat_every: int = None):
        """Add events to your schedule."""
        events = await config.reminders()
        user_events = []
        for event in events:
            # only show current user
            if event['user_id'] != interaction.user.id:
                continue
            user_events.append(event)
        if len(user_events) >= 24:
            await interaction.response.send_message('I can\'t add any more reminders for you. Please use `/schedule remove` to remove reminders from your schedule before trying to add a new one.')
            return
        split_date = weekday.split("/")
        time_split = reminder_time.split(":")
        # attempt to resolve 'am' or 'pm' times, can be done better but this works
        try:
            if time_split[1][2:] and time_split[1][2:].lower() in ['am', 'pm']:
                if time_split[1][2:].lower() == 'am':
                    time_split[0] = time_split[0]
                    time_split[1] = time_split[1].lower().strip('am')
                else:
                    time_split[0] = int(time_split[0]) + 12
                    time_split[1] = time_split[1].lower().strip('pm')
                if int(time_split[0]) in [12, 24]:
                    if int(time_split[0]) == 12:
                        time_split[0] = 0
                    else:
                        time_split[0] = 12
        except IndexError:
            if time_split[0][2:].lower() in ['am', 'pm']:
                if time_split[0][2:].lower() == 'am':
                    time_split[0] = time_split[0].lower().strip('am')
                    time_split.append('00')
                else:
                    time_split[0] = int(time_split[0].lower().strip('pm')) + 12
                    time_split.append('00')
                if int(time_split[0]) in [12, 24]:
                    if int(time_split[0]) == 12:
                        time_split[0] = 0
                    else:
                        time_split[0] = 12
            else:
                await interaction.response.send_message('I don\'t really understand what time you want me to remind you at. (The time format is HH:MM. Example: 23:59)', ephemeral=True)
                return
        except:
            await interaction.response.send_message('I don\'t really understand what time you want me to remind you at. (The time format is HH:MM. Example: 23:59)', ephemeral=True)
            return
        if int(time_split[0]) in [12, 24]:
            if int(time_split[0]) == 12:
                time_split[0] = 0
            else:
                time_split[0] = 12
        # split and convert to int
        for num in split_date:
            index_num = split_date.index(num)
            split_date[index_num] = int(num)
        try:
            for num in time_split:
                index_num = time_split.index(num)
                time_split[index_num] = int(num)
        except ValueError:
            await interaction.response.send_message('I don\'t really understand what time you want me to remind you at. (The time format is HH:MM. Example: 23:59)', ephemeral=True)
            return
        if len(time_split) > 2 or time_split[0] > 23 or time_split[1] > 59:
            await interaction.response.send_message('I don\'t really understand what time you want me to remind you at. (The time format is HH:MM. Example: 23:59)', ephemeral=True)
            return
        time_obj = datetime.datetime(split_date[2], split_date[1], split_date[0], time_split[0], time_split[1])
        utc_time = int(time.mktime(time_obj.timetuple()))
        if int(time.time()) > utc_time:
            await interaction.response.send_message('I can\'t remind you of things in the past... well unless you\'ve got a time machine laying around. (Please use a time and date in the future.)', ephemeral=True)
            return
        reminder_idnum = await config.reminder_id()
        if repeat_every:
            recurring = True
        else:
            recurring = False
            repeat_every = 0
        schedule_event = {
            'user_id': interaction.user.id,
            'set_time': int(time.time()),
            'next_reminder': utc_time,
            'reminder_text': reminder_text,
            'recurring': recurring,
            'recurs_every': repeat_every,
            'reminder_id': f'EID{reminder_idnum}',
            'failed_count': 0
        }
        try:
            await interaction.user.send(f"Hello! I've added a reminder to your schedule. I will send a reminder here on <t:{utc_time}:F> to {reminder_text}.")
        except:
            await interaction.response.send_message('I don\'t seem to be able to send direct messages to you. (Please enable your direct messages.)', ephemeral=True)
            return
        async with config.reminders() as reminders:
            reminders.append(schedule_event)
        await config.reminder_id.set(reminder_idnum + 1)
        await interaction.response.send_message(f"I've added a reminder to {reminder_text} to your schedule. {f'I will remind you to do this every {display_time(repeat_every)} until you ask me to stop.' if recurring else 'I will only send you this reminder once.'}")

    @app_commands.command()
    @app_commands.autocomplete(reminder_id=autocomplete_id)
    @app_commands.describe(reminder_id="The ID of the reminder you are removing.")
    async def remove(self, interaction: discord.Interaction, reminder_id: str):
        """Remove events from your schedule."""
        for event in await config.reminders():
            if event['user_id'] == interaction.user.id and event['reminder_id'] == reminder_id:
                async with config.reminders() as current_reminders:
                    index_num = current_reminders.index(event)
                    current_reminders.pop(index_num)
                await interaction.response.send_message(f"Got it. I won't remind you to {event['reminder_text']} anymore.")

    @app_commands.command()
    async def show(self, interaction: discord.Interaction):
        """Shows all of your reminders"""
        events = await config.reminders()
        user_events = []
        for event in events:
            # only show current user
            if event['user_id'] != interaction.user.id:
                continue
            user_events.append(event)
        if len(user_events) <= 0:
            await interaction.response.send_message("You haven't asked me to remind you of anything yet.")
            return
        max_len = 24
        # use menus if discord embed limit reached
        user_events_div = [user_events[i * max_len:(i + 1) * max_len] for i in range((len(user_events) + max_len - 1) // max_len)]
        page_num = 0
        last_page = len(user_events_div)
        embed_list = []
        for lists in user_events_div:
            embed=discord.Embed(title="Current Schedule", description="Here is everything you've asked me to remind you about:", color=0x00ff00)
            page_num = page_num + 1
            embed.set_footer(text=f"Schedule for {interaction.user.display_name} | Page {page_num} of {last_page}")
            for event in lists:
                embed.add_field(name=f"Reminder ID: {event['reminder_id']}", value=f"**Next Reminder:** <t:{event['next_reminder']}:F>\n**Reminder Text**: {event['reminder_text']}\n**Recurs Weekly**: {event['recurring']}", inline=False)
            embed_list.append(embed)
        #TODO: Add menus for greater than 24 items
        #if len(embed_list) == 1:
        await interaction.response.send_message(embed=embed_list[0])
        #else:
        #    await menu(ctx, embed_list, DEFAULT_CONTROLS)
