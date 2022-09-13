from redbot.core.bot import Red
from .selectroles import SelectRoles

async def setup(bot: Red) -> None:
    await bot.add_cog(SelectRoles(bot))
