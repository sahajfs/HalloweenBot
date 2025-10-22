import discord
from discord import app_commands
from discord.ext import commands
import random
import logging
import os

GUILD_ID = int(os.getenv('GUILD_ID'))

# DISPLAY rewards (what users see - FAKE)
DISPLAY_REWARDS = {
    "Mr Carrot or Los Carrot (pvb)": "35%",
    "Shroom (pvb)": "25%",
    "3 Shroom (pvb)": "15.5%",
    "3 Mango (pvb)": "12.5%",
    "3 Lucky Block (sab)": "7.5%",
    "500k/s 67 (pvb)": "4%",
    "Dragon canneiloni (sab)": "0.5%"
}

# ACTUAL probabilities (RIGGED RATES)
ACTUAL_REWARDS = [
    ("Mr Carrot or Los Carrot (pvb)", 60.0),
    ("Shroom (pvb)", 25.0),
    ("3 Shroom (pvb)", 7.5),
    ("3 Mango (pvb)", 4.5),
    ("3 Lucky Block (sab)", 2.0),
    ("500k/s 67 (pvb)", 1.0)
]

class TrickOrTreatButton(discord.ui.View):
    def __init__(self, target_user: discord.Member, admin: discord.Member, bot, is_secret: bool = False):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.admin = admin
        self.bot = bot
        self.is_secret = is_secret
        self.played = False
    
    @discord.ui.button(label="Trick or Treat", style=discord.ButtonStyle.primary)
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return
        
        if self.played:
            await interaction.response.send_message("You already played!", ephemeral=True)
            return
        
        self.played = True
        
        points = await self.bot.db.get_points(self.target_user.id)
        if points < 1:
            await interaction.response.send_message("You don't have enough points!", ephemeral=True)
            return
        
        await self.bot.db.remove_points(self.target_user.id, 1)
        new_points = await self.bot.db.get_points(self.target_user.id)
        
        # SECRET CODE - Guaranteed Dragon
        if self.is_secret:
            reward_name = "Dragon canneiloni (sab)"
            display_percentage = DISPLAY_REWARDS[reward_name]
            
            embed = discord.Embed(
                title="Congratulations!",
                description=f"You won **{display_percentage}** reward: **{reward_name}**!",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"Points remaining: {new_points}")
            
            logging.info(f"SECRET: {self.target_user.name} won SECRET Dragon canneiloni (0.5%) via code (Admin: {self.admin.name})")
            
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except:
                await interaction.followup.send(embed=embed)
            return
        
        # FIXED: 50% TRICK / 50% TREAT
        is_treat = random.random() < 0.50
        
        if not is_treat:
            # TRICK
            embed = discord.Embed(
                title="Oops...",
                description="Sorry, you got **tricked**! Better luck next time!",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Points remaining: {new_points}")
            
            logging.info(f"USER: {self.target_user.name} played Trick or Treat -> TRICK (Admin: {self.admin.name})")
            
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except:
                await interaction.followup.send(embed=embed)
        else:
            # TREAT - Rigged reward
            reward_name = self.get_rigged_reward()
            display_percentage = DISPLAY_REWARDS[reward_name]
            
            embed = discord.Embed(
                title="Congratulations!",
                description=f"You won **{display_percentage}** reward: **{reward_name}**!",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Points remaining: {new_points}")
            
            logging.info(f"USER: {self.target_user.name} played Trick or Treat -> TREAT: {reward_name} (Displayed: {display_percentage}, Admin: {self.admin.name})")
            
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except:
                await interaction.followup.send(embed=embed)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Cancelled",
            description="Game cancelled. No points were used.",
            color=discord.Color.greyple()
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except:
            await interaction.followup.send(embed=embed)
    
    def get_rigged_reward(self):
        """Weighted random reward selection using ACTUAL probabilities"""
        names, weights = zip(*ACTUAL_REWARDS)
        reward_name = random.choices(names, weights=weights, k=1)[0]
        return reward_name


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_perms(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator permission"""
        return interaction.user.guild_permissions.administrator
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Hide commands from non-administrators"""
        return self.has_admin_perms(interaction)
    
    @app_commands.command(name="trickortreat", description="Send Trick or Treat game (Admin Only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to send the game to (leave blank to play yourself)")
    async def trickortreat(self, interaction: discord.Interaction, user: discord.Member = None):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        # If no user mentioned, the admin plays themselves
        if user is None:
            user = interaction.user
        
        points = await self.bot.db.get_points(user.id)
        if points < 1:
            await interaction.response.send_message(
                f"{user.mention} doesn't have enough points! (Current: {points})",
                ephemeral=True
            )
            return
        
        is_secret = False
        
        embed = discord.Embed(
            title="Trick or Treat Time!",
            description=f"{user.mention}, you've been invited to play!\n\n**Cost:** 1 point\n**Your points:** {points}",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="How to Play",
            value="Press **Trick or Treat** to play or **Cancel** to skip.",
            inline=False
        )
        
        view = TrickOrTreatButton(user, interaction.user, self.bot, is_secret)
        
        try:
            await interaction.response.send_message(embed=embed, view=view)
            logging.info(f"ADMIN: {interaction.user.name} sent Trick or Treat to {user.name}")
        except:
            await interaction.followup.send(embed=embed, view=view)
            logging.info(f"ADMIN: {interaction.user.name} sent Trick or Treat to {user.name}")
    
    # HIDDEN MESSAGE COMMAND for secret Dragon (UNCHANGED)
    @commands.command(name="secretdragon")
    async def secretdragon_msg(self, ctx, user: discord.Member):
        """Secret message command - won't show in slash command list"""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permission!", delete_after=3)
            await ctx.message.delete()
            return
        
        points = await self.bot.db.get_points(user.id)
        if points < 1:
            await ctx.send(f"{user.mention} doesn't have enough points! (Current: {points})", delete_after=5)
            await ctx.message.delete()
            return
        
        # DELETE the command message immediately
        await ctx.message.delete()
        
        # SECRET MODE ENABLED
        is_secret = True
        
        embed = discord.Embed(
            title="Trick or Treat Time!",
            description=f"{user.mention}, you've been invited to play!\n\n**Cost:** 1 point\n**Your points:** {points}",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="How to Play",
            value="Press **Trick or Treat** to play or **Cancel** to skip.",
            inline=False
        )
        
        view = TrickOrTreatButton(user, ctx.author, self.bot, is_secret)
        
        await ctx.send(embed=embed, view=view)
        logging.info(f"SECRET: {ctx.author.name} activated SECRET DRAGON for {user.name}")

async def setup(bot):
    await bot.add_cog(Game(bot))