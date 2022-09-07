from .timeroles import TimeRoles

async def setup(bot):
    await bot.add_cog(TimeRoles(bot))
