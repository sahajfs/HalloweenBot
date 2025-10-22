import discord
from discord import app_commands
from discord.ext import commands
import logging
import os

GUILD_ID = int(os.getenv('GUILD_ID'))

class Points(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_specific_role(self, interaction: discord.Interaction) -> bool:
        """Check if user has THE SPECIFIC role ID - NOT admin, NOT owner"""
        specific_role_id = self.bot.admin_role_id  # 1424952240220803203
        return any(role.id == specific_role_id for role in interaction.user.roles)
    
    async def safe_send(self, interaction: discord.Interaction, message: str = None, embed: discord.Embed = None, ephemeral: bool = False):
        """Safely send message with error handling"""
        try:
            if not interaction.response.is_done():
                if embed:
                    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
                else:
                    await interaction.response.send_message(message, ephemeral=ephemeral)
            else:
                if embed:
                    await interaction.followup.send(embed=embed, ephemeral=ephemeral)
                else:
                    await interaction.followup.send(message, ephemeral=ephemeral)
        except (discord.errors.HTTPException, ConnectionError) as e:
            logging.error(f"Failed to send message: {e}")
            try:
                if embed:
                    await interaction.followup.send(embed=embed, ephemeral=ephemeral)
                else:
                    await interaction.followup.send(message, ephemeral=ephemeral)
            except:
                pass
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Hide /point command from users without the specific role"""
        return self.has_specific_role(interaction)
    
    @app_commands.command(name="point", description="Manage user points (Specific Role Only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(
        action="Choose action: increase, decrease, reset, list",
        user="Target user (optional for 'list')",
        amount="Amount of points (for increase/decrease)"
    )
    async def point(
        self, 
        interaction: discord.Interaction, 
        action: str,
        user: discord.Member = None,
        amount: int = None
    ):
        # CRITICAL: Only the specific role ID can manage points
        if not self.has_specific_role(interaction):
            await self.safe_send(interaction, "❌ You don't have the required role to manage points!", ephemeral=True)
            return
        
        action = action.lower()
        
        # LIST command
        if action == "list":
            if user:
                points = await self.bot.db.get_points(user.id)
                embed = discord.Embed(
                    title=f"Points for {user.display_name}",
                    description=f"**{points}** points",
                    color=discord.Color.orange()
                )
                await self.safe_send(interaction, embed=embed)
            else:
                all_points = await self.bot.db.get_all_points()
                if not all_points:
                    await self.safe_send(interaction, "No users have points yet.")
                    return
                
                embed = discord.Embed(
                    title="All User Points",
                    color=discord.Color.orange()
                )
                
                for user_id, points in all_points[:10]:
                    member = interaction.guild.get_member(user_id)
                    name = member.display_name if member else f"User {user_id}"
                    embed.add_field(name=name, value=f"{points} points", inline=False)
                
                await self.safe_send(interaction, embed=embed)
            return
        
        if not user:
            await self.safe_send(interaction, "Please mention a user!", ephemeral=True)
            return
        
        # INCREASE
        if action == "increase":
            if not amount or amount <= 0:
                await self.safe_send(interaction, "Please provide a valid amount!", ephemeral=True)
                return
            
            await self.bot.db.add_points(user.id, amount)
            new_points = await self.bot.db.get_points(user.id)
            
            logging.info(f"ADMIN: {interaction.user.name} gave +{amount} points to {user.name} (Total: {new_points})")
            
            await self.safe_send(
                interaction,
                f"Added **{amount}** points to {user.mention}! They now have **{new_points}** points."
            )
        
        # DECREASE
        elif action == "decrease":
            if not amount or amount <= 0:
                await self.safe_send(interaction, "Please provide a valid amount!", ephemeral=True)
                return
            
            await self.bot.db.remove_points(user.id, amount)
            new_points = await self.bot.db.get_points(user.id)
            
            logging.info(f"ADMIN: {interaction.user.name} removed -{amount} points from {user.name} (Total: {new_points})")
            
            await self.safe_send(
                interaction,
                f"Removed **{amount}** points from {user.mention}! They now have **{new_points}** points."
            )
        
        # RESET
        elif action == "reset":
            await self.bot.db.reset_points(user.id)
            
            logging.info(f"ADMIN: {interaction.user.name} reset points for {user.name}")
            
            await self.safe_send(
                interaction,
                f"Reset points for {user.mention}! They now have **0** points."
            )
        
        else:
            await self.safe_send(
                interaction,
                "Invalid action! Use: increase, decrease, reset, or list",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Points(bot))