from redbot.core.bot import Red
from .textcommands import SelectRoles

def setup(bot: Red) -> None:
    bot.add_cog(SelectRoles(bot))