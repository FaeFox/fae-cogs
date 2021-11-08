from .selectroles import SelectRoles

def setup(bot):
    bot.add_cog(SelectRoles(bot))
