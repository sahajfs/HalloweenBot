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

# ACTUAL RIGGED REWARDS (What players ACTUALLY WIN)
# Only 3 rewards with rigged percentages
FREEPLAY_REWARDS = [
    ("4 Tomato", 60.0),           # 60% chance
    ("2x Mango", 30.0),           # 30% chance
    ("2x 50-100k DPS", 10.0)      # 10% chance
]

class FreeplayButton(discord.ui.View):
    def __init__(self, target_user: discord.Member, admin: discord.Member, bot):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.admin = admin
        self.bot = bot
        self.played = False
    
    @discord.ui.button(label="Play Freeplay", style=discord.ButtonStyle.success)
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user.id:
            await interaction.response.send_message("This isn't for you!", ephemeral=True)
            return
        
        if self.played:
            await interaction.response.send_message("You already played!", ephemeral=True)
            return
        
        has_claimed = await self.bot.db.has_claimed_freeplay(self.target_user.id)
        if has_claimed:
            embed = discord.Embed(
                title="Already Claimed!",
                description="You have already claimed your freeplay! You can only claim it once.",
                color=discord.Color.red()
            )
            try:
                await interaction.response.edit_message(embed=embed, view=None)
            except:
                await interaction.followup.send(embed=embed)
            
            logging.info(f"FREEPLAY BLOCKED: {self.target_user.name} already claimed (Admin: {self.admin.name})")
            return
        
        self.played = True
        await self.bot.db.mark_freeplay_claimed(self.target_user.id)
        
        reward_name = self.get_freeplay_reward()
        display_percentage = DISPLAY_REWARDS[reward_name]
        
        embed = discord.Embed(
            title="🎁 Freeplay Gift!",
            description=f"Congratulations! You won the **{display_percentage}** reward: **{reward_name}**!",
            color=discord.Color.gold()
        )
        embed.set_footer(text="No points were used for this game!")
        
        logging.info(f"FREEPLAY: {self.target_user.name} -> {reward_name} (Shown: {display_percentage}, Admin: {self.admin.name})")
        
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
            description="Freeplay cancelled.",
            color=discord.Color.greyple()
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=None)
        except:
            await interaction.followup.send(embed=embed)
    
    def get_freeplay_reward(self):
        """Returns one of the 3 rigged rewards: 60% 4 Tomato, 30% 2x Mango, 10% 2x 50-100k DPS"""
        names, weights = zip(*FREEPLAY_REWARDS)
        reward_name = random.choices(names, weights=weights, k=1)[0]
        return reward_name


class Freeplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_perms(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return self.has_admin_perms(interaction)
    
    @app_commands.command(name="freeplay", description="Send a free Trick or Treat (one-time only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to send freeplay to")
    async def freeplay(self, interaction: discord.Interaction, user: discord.Member):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission!", ephemeral=True)
            return
        
        has_claimed = await self.bot.db.has_claimed_freeplay(user.id)
        if has_claimed:
            await interaction.response.send_message(
                f"❌ {user.mention} has already claimed their freeplay!\n\nUse `/resetfreeplay @{user.name}` to reset.",
                ephemeral=True
            )
            return
        
        rewards_text = "\n".join([f"• **{reward}** - {percent}" for reward, percent in DISPLAY_REWARDS.items()])
        
        embed = discord.Embed(
            title="🎁 Free Gift Time!",
            description=f"{user.mention}, you've received a **FREE** Trick or Treat!\n\n⚠️ **This is a ONE-TIME offer!**",
            color=discord.Color.gold()
        )
        embed.add_field(name="🎁 Possible Rewards", value=rewards_text, inline=False)
        embed.add_field(name="How to Play", value="Press **Play Freeplay** or **Cancel**.\n\n**Note:** You can only claim this once!", inline=False)
        embed.set_footer(text="No points required!")
        
        view = FreeplayButton(user, interaction.user, self.bot)
        
        try:
            await interaction.response.send_message(embed=embed, view=view)
            logging.info(f"ADMIN: {interaction.user.name} sent Freeplay to {user.name}")
        except:
            await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="resetfreeplay", description="Reset freeplay claim")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to reset (blank = reset ALL)")
    async def resetfreeplay(self, interaction: discord.Interaction, user: discord.Member = None):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission!", ephemeral=True)
            return
        
        if user is None:
            await self.bot.db.reset_all_freeplays()
            await interaction.response.send_message("✅ Reset ALL freeplay claims!", ephemeral=True)
            logging.info(f"ADMIN: {interaction.user.name} reset ALL freeplays")
        else:
            await self.bot.db.reset_freeplay(user.id)
            await interaction.response.send_message(f"✅ Reset freeplay for {user.mention}!", ephemeral=True)
            logging.info(f"ADMIN: {interaction.user.name} reset freeplay for {user.name}")

async def setup(bot):
    await bot.add_cog(Freeplay(bot))

