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
    "500k/s 67 (pvb)": "4%"
}

# ACTUAL probabilities for FREEPLAY (NEW RIGGED RATES - no Dragon)
FREEPLAY_REWARDS = [
    ("Mr Carrot or Los Carrot (pvb)", 60.0),
    ("Shroom (pvb)", 25.0),
    ("3 Shroom (pvb)", 7.5),
    ("3 Mango (pvb)", 4.5),
    ("3 Lucky Block (sab)", 2.0),
    ("500k/s 67 (pvb)", 1.0)
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
        
        # CHECK if already claimed before
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
            
            logging.info(f"FREEPLAY BLOCKED: {self.target_user.name} already claimed freeplay (Admin: {self.admin.name})")
            return
        
        self.played = True
        
        # Mark as claimed
        await self.bot.db.mark_freeplay_claimed(self.target_user.id)
        
        # 100% TREAT - Random rigged reward (no Dragon)
        reward_name = self.get_freeplay_reward()
        display_percentage = DISPLAY_REWARDS[reward_name]
        
        embed = discord.Embed(
            title="Freeplay Gift!",
            description=f"Congratulations! You won **{display_percentage}** reward: **{reward_name}**!",
            color=discord.Color.gold()
        )
        embed.set_footer(text="No points were used for this game!")
        
        logging.info(f"FREEPLAY: {self.target_user.name} played Freeplay -> {reward_name} (Displayed: {display_percentage}, Admin: {self.admin.name})")
        
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
        """Weighted random reward selection for freeplay with NEW percentages"""
        names, weights = zip(*FREEPLAY_REWARDS)
        reward_name = random.choices(names, weights=weights, k=1)[0]
        return reward_name


class Freeplay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_perms(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator permission"""
        return interaction.user.guild_permissions.administrator
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Hide commands from non-administrators"""
        return self.has_admin_perms(interaction)
    
    @app_commands.command(name="freeplay", description="Send a free Trick or Treat to a user (one-time only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to send the freeplay to")
    async def freeplay(self, interaction: discord.Interaction, user: discord.Member):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        # Check if user already claimed
        has_claimed = await self.bot.db.has_claimed_freeplay(user.id)
        if has_claimed:
            await interaction.response.send_message(
                f"❌ {user.mention} has already claimed their freeplay! They can only claim it once.\n\n"
                f"Use `/resetfreeplay @{user.name}` to reset their claim if needed.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="Free Gift Time!",
            description=f"{user.mention}, you've received a **FREE** Trick or Treat!\n\n⚠️ **This is a ONE-TIME offer!**",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="How to Play",
            value="Press **Play Freeplay** to claim your reward or **Cancel** to skip.\n\n**Note:** You can only claim this once!",
            inline=False
        )
        embed.set_footer(text="No points required!")
        
        view = FreeplayButton(user, interaction.user, self.bot)
        
        try:
            await interaction.response.send_message(embed=embed, view=view)
            logging.info(f"ADMIN: {interaction.user.name} sent Freeplay to {user.name}")
        except:
            await interaction.followup.send(embed=embed, view=view)
            logging.info(f"ADMIN: {interaction.user.name} sent Freeplay to {user.name}")
    
    @app_commands.command(name="resetfreeplay", description="Reset freeplay claim for a user")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to reset freeplay for (leave blank to reset ALL)")
    async def resetfreeplay(self, interaction: discord.Interaction, user: discord.Member = None):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        if user is None:
            # Reset ALL freeplays
            await self.bot.db.reset_all_freeplays()
            await interaction.response.send_message("✅ Reset ALL freeplay claims! Everyone can claim again.", ephemeral=True)
            logging.info(f"ADMIN: {interaction.user.name} reset ALL freeplay claims")
        else:
            # Reset specific user
            await self.bot.db.reset_freeplay(user.id)
            await interaction.response.send_message(f"✅ Reset freeplay for {user.mention}! They can claim again.", ephemeral=True)
            logging.info(f"ADMIN: {interaction.user.name} reset freeplay for {user.name}")

async def setup(bot):
    await bot.add_cog(Freeplay(bot))