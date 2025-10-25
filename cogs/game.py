import discord
from discord import app_commands
from discord.ext import commands
import random
import logging
import os

GUILD_ID = int(os.getenv('GUILD_ID'))

# DISPLAY REWARDS (What players SEE) - Changed "8 Tomato" to "4 Tomato"
DISPLAY_REWARDS = {
    "4 Tomato": "35%",  # ← CHANGED FROM "8 Tomato"
    "2x Mango": "25%",
    "2x 50-100k DPS": "15%",
    "3x Lucky Block": "12.5%",
    "67": "7.5%",
    "Owner Collection Payout": "4.5%",
    "Secret Dragon Canneiloni (sab)": "0.5%"
}

# ACTUAL REWARDS for regular Trick or Treat (keeping original rigging)
ACTUAL_REWARDS = [
    ("4 Tomato", 55.5),  # ← CHANGED FROM "8 Tomato"
    ("2x Mango", 20.0),
    ("2x 50-100k DPS", 12.5),
    ("3x Lucky Block", 7.5),
    ("67", 3.5),
    ("Owner Collection Payout", 1.0)
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
        
        if self.is_secret:
            reward_name = "Secret Dragon Canneiloni (sab)"
            display_percentage = DISPLAY_REWARDS[reward_name]
            
            embed = discord.Embed(
                title="🎉 JACKPOT! 🎉",
                description=f"You won the **{display_percentage}** reward: **{reward_name}**!",
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"Points remaining: {new_points}")
            
            logging.info(f"SECRET: {self.target_user.name} won SECRET Dragon Canneiloni (Admin: {self.admin.name})")
            
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except:
                await interaction.followup.send(embed=embed)
            return
        
        is_treat = random.random() < 0.49
        
        if not is_treat:
            embed = discord.Embed(
                title="👻 Oops...",
                description="Sorry, you got **tricked**! Better luck next time!",
                color=discord.Color.red()
            )
            embed.set_footer(text=f"Points remaining: {new_points}")
            
            logging.info(f"USER: {self.target_user.name} -> TRICK (Admin: {self.admin.name})")
            
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except:
                await interaction.followup.send(embed=embed)
        else:
            reward_name = self.get_rigged_reward()
            display_percentage = DISPLAY_REWARDS[reward_name]
            
            embed = discord.Embed(
                title="🎃 Congratulations!",
                description=f"You won the **{display_percentage}** reward: **{reward_name}**!",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Points remaining: {new_points}")
            
            logging.info(f"USER: {self.target_user.name} -> TREAT: {reward_name} (Shown: {display_percentage}, Admin: {self.admin.name})")
            
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
        names, weights = zip(*ACTUAL_REWARDS)
        reward_name = random.choices(names, weights=weights, k=1)[0]
        return reward_name


class Game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_perms(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return self.has_admin_perms(interaction)
    
    @app_commands.command(name="trickortreat", description="Send Trick or Treat game (Admin Only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to send the game to")
    async def trickortreat(self, interaction: discord.Interaction, user: discord.Member = None):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission!", ephemeral=True)
            return
        
        if user is None:
            user = interaction.user
        
        points = await self.bot.db.get_points(user.id)
        if points < 1:
            await interaction.response.send_message(f"{user.mention} doesn't have enough points! (Current: {points})", ephemeral=True)
            return
        
        is_secret = False
        
        rewards_text = "\n".join([f"• **{reward}** - {percent}" for reward, percent in DISPLAY_REWARDS.items()])
        
        embed = discord.Embed(
            title="🎃 Trick or Treat Time!",
            description=f"{user.mention}, you've been invited to play!\n\n**Cost:** 1 point\n**Your points:** {points}",
            color=discord.Color.orange()
        )
        embed.add_field(name="🎁 Possible Rewards", value=rewards_text, inline=False)
        embed.add_field(name="How to Play", value="Press **Trick or Treat** to play or **Cancel** to skip.", inline=False)
        
        view = TrickOrTreatButton(user, interaction.user, self.bot, is_secret)
        
        try:
            await interaction.response.send_message(embed=embed, view=view)
            logging.info(f"ADMIN: {interaction.user.name} sent Trick or Treat to {user.name}")
        except:
            await interaction.followup.send(embed=embed, view=view)
    
    @commands.command(name="secretdragon")
    async def secretdragon_msg(self, ctx, user: discord.Member):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("You don't have permission!", delete_after=3)
            await ctx.message.delete()
            return
        
        points = await self.bot.db.get_points(user.id)
        if points < 1:
            await ctx.send(f"{user.mention} doesn't have enough points!", delete_after=5)
            await ctx.message.delete()
            return
        
        await ctx.message.delete()
        
        is_secret = True
        
        rewards_text = "\n".join([f"• **{reward}** - {percent}" for reward, percent in DISPLAY_REWARDS.items()])
        
        embed = discord.Embed(
            title="🎃 Trick or Treat Time!",
            description=f"{user.mention}, you've been invited to play!\n\n**Cost:** 1 point\n**Your points:** {points}",
            color=discord.Color.orange()
        )
        embed.add_field(name="🎁 Possible Rewards", value=rewards_text, inline=False)
        embed.add_field(name="How to Play", value="Press **Trick or Treat** to play or **Cancel** to skip.", inline=False)
        
        view = TrickOrTreatButton(user, ctx.author, self.bot, is_secret)
        
        await ctx.send(embed=embed, view=view)
        logging.info(f"SECRET: {ctx.author.name} activated SECRET DRAGON for {user.name}")

async def setup(bot):
    await bot.add_cog(Game(bot))
