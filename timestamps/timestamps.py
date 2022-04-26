import discord
import typing
import datetime
import calendar
import time

from discord import app_commands

from redbot.core import Config

config = Config.get_conf(
    cog_instance=None, identifier=28613272024011950, force_registration=True, cog_name="Timestamps"
)
config.register_guild(
    common_times=[]
)
config.register_member(
   prev_times=[],
   prev_lens=[]
)

async def autocomplete_date(interaction: discord.Interaction, current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
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

async def autocomplete_time(interaction: discord.Interaction, current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
    autocomplete_list = await config.member(interaction.user).prev_times()
    return [
        app_commands.Choice(name=prev_time, value=prev_time)
        for prev_time in autocomplete_list if current in prev_time
    ]

async def autocomplete_len(interaction: discord.Interaction, current: str, namespace: app_commands.Namespace) -> typing.List[app_commands.Choice[str]]:
    autocomplete_list = await config.member(interaction.user).prev_lens()
    if len(autocomplete_list) == []:
        autocomplete_list.append(1)
        autocomplete_list.append(2)
    return [
        app_commands.Choice(name=f"{prev_len} Hour{'s' if prev_len > 1 else ''}", value=prev_len)
        for prev_len in autocomplete_list
    ]


@app_commands.command()
@app_commands.autocomplete(event_date=autocomplete_date, event_time=autocomplete_time, event_length=autocomplete_len)
@app_commands.describe(event_date = "The date for the timestamp. Format is DD/MM/YYYY.", event_time = "The time for the timestamp. Format is HH:MM.", event_length = "How many hours the event will last.")
async def timestamps(interaction: discord.Interaction, event_date: str, event_time: str, event_length: int = None):
        """Create a timestamp."""
        prev_time_list = await config.member(interaction.user).prev_times()
        prev_len_list = await config.member(interaction.user).prev_lens()
        split_date = event_date.split("/")
        time_split = event_time.split(":")
        # attempt to resolve 'am' or 'pm' times, can be done better but this works
        try:
            if time_split[1][2:] and time_split[1][2:].lower() in ['am', 'pm']:
                if time_split[1][2:].lower() == 'am':
                    time_split[0] = time_split[0]
                    time_split[1] = time_split[1].lower().strip('am')
                else:
                    time_split[0] = int(time_split[0]) + 12
                    time_split[1] = time_split[1].lower().strip('pm')
        except IndexError:
            if time_split[0][2:].lower() in ['am', 'pm']:
                if time_split[0][2:].lower() == 'am':
                    time_split[0] = time_split[0].lower().strip('am')
                    time_split.append('00')
                else:
                    time_split[0] = int(time_split[0].lower().strip('pm')) + 12
                    time_split.append('00')
            else:
                await interaction.response.send_message('The time you entered is not a valid time. (The time format is HH:MM. Example: 23:59)', ephemeral=True)
                return
        except:
            await interaction.response.send_message('The time you entered is not a valid time. (The time format is HH:MM. Example: 23:59)', ephemeral=True)
            return
        if int(time_split[0]) in [12, 24]:
            if int(time_split[0]) == 12:
                time_split[0] = 0
            else:
                time_split[0] = 12
        # why am i converting to int this way
        for num in split_date:
            index_num = split_date.index(num)
            split_date[index_num] = int(num)
        for num in time_split:
            index_num = time_split.index(num)
            time_split[index_num] = int(num)
        time_obj = datetime.datetime(split_date[2], split_date[1], split_date[0], time_split[0], time_split[1])
        utc_time = int(time.mktime(time_obj.timetuple()))
        if interaction.user.id in [129310857334226945, 127244746480549888, 378017188503879691] or interaction.user.id == 378017188503879691 and interaction.guild.id == 779821183285461052:
            utc_time = utc_time - 25200
        # for autocomplete_time's autocomplete list
        if event_time not in prev_time_list:
            prev_time_list.append(event_time)
            await config.member(interaction.user).prev_times.set(prev_time_list[:3])
        if event_length != None:
            if event_length not in prev_time_list:
                prev_len_list.append(event_length)
                await config.member(interaction.user).prev_lens.set(prev_len_list[:3])
            embed=discord.Embed(title="Event Timestamps", description=f"The following timestamp is for this time: <t:{utc_time}>. Please make sure that this time is correct, then copy the below text:\n\n```<t:{utc_time}:F> - <t:{utc_time+(event_length * 3600)}:t>```", color=0x00ff00)
            embed.add_field(name="Example Output", value=f"<t:{utc_time}:F> - <t:{utc_time+(event_length * 3600)}:t>", inline=False)
            await interaction.response.send_message(embed=embed)
            return
        embed=discord.Embed(title="Discord Timestamps", description=f"Discord time stamps for <t:{utc_time}>", color=0x00ff00)
        embed.add_field(name="Short Time", value=f"<t:{utc_time}:t>\n```<t:{utc_time}:t>```", inline=False)
        embed.add_field(name="Short Date", value=f"<t:{utc_time}:d>\n```<t:{utc_time}:d>```", inline=False)
        embed.add_field(name="Long Date", value=f"<t:{utc_time}:D>\n```<t:{utc_time}:D>```", inline=False)
        embed.add_field(name="Short Date + Time", value=f"<t:{utc_time}:f>\n```<t:{utc_time}:f>```", inline=False)
        embed.add_field(name="Long Date + Time", value=f"<t:{utc_time}:F>\n```<t:{utc_time}:F>```", inline=False)
        embed.add_field(name="Relative Time", value=f"<t:{utc_time}:R>\n```<t:{utc_time}:R>```", inline=False)
        await interaction.response.send_message(embed=embed)
