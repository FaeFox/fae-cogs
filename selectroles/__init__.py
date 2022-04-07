from redbot.core.bot import Red
from .selectroles import SelectRoles

def setup(bot: Red) -> None:
    bot.add_cog(SelectRoles(bot))
