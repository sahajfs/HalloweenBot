import discord
from discord import app_commands
from discord.ext import commands
import logging
import os

GUILD_ID = int(os.getenv('GUILD_ID'))

# YOUR CHANNELS - Messages counted ONLY in these 2 channels
COUNTED_CHANNELS = [
    1391149229594116427,  # Channel 1
    1407443051768447006,  # Channel 2
]

# Messages needed for 1 point - CHANGED FROM 300 TO 500
MESSAGES_PER_POINT = 500

class MessageCounter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def has_admin_perms(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator permission"""
        return interaction.user.guild_permissions.administrator
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only count in specific channels
        if COUNTED_CHANNELS and message.channel.id not in COUNTED_CHANNELS:
            return
        
        # Increment message count
        new_count = await self.bot.db.increment_message_count(message.author.id)
        
        # Check if user reached 500 messages (changed from 300)
        if new_count >= MESSAGES_PER_POINT:
            # Award 1 point
            await self.bot.db.add_points(message.author.id, 1)
            
            # Reset message counter
            await self.bot.db.reset_message_count(message.author.id)
            
            # Get new point total
            total_points = await self.bot.db.get_points(message.author.id)
            
            # Send congratulations message
            embed = discord.Embed(
                title="🎉 Congratulations!",
                description=f"{message.author.mention} reached **{MESSAGES_PER_POINT}** messages and earned **1 point**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="Total Points", value=f"**{total_points}** points", inline=False)
            embed.set_footer(text=f"Keep chatting to earn more points!")
            
            await message.channel.send(embed=embed)
            
            logging.info(f"AUTO POINT: {message.author.name} earned 1 point from {MESSAGES_PER_POINT} messages (Total: {total_points})")
    
    @app_commands.command(name="messagecount", description="Check your message progress")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def messagecount(self, interaction: discord.Interaction):
        user = interaction.user
        
        message_count = await self.bot.db.get_message_count(user.id)
        points = await self.bot.db.get_points(user.id)
        
        remaining = MESSAGES_PER_POINT - message_count
        progress_percent = (message_count / MESSAGES_PER_POINT) * 100
        
        # Progress bar
        filled = int(progress_percent / 5)  # 20 bars total
        bar = "█" * filled + "░" * (20 - filled)
        
        embed = discord.Embed(
            title=f"📊 Your Message Stats",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Progress to Next Point",
            value=f"{bar} {progress_percent:.1f}%\n**{message_count}/{MESSAGES_PER_POINT}** messages",
            inline=False
        )
        embed.add_field(name="📝 Messages Remaining", value=f"**{remaining}** more", inline=True)
        embed.add_field(name="🎯 Total Points", value=f"**{points}** points", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="pointdisplay", description="Check your total points")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def pointdisplay(self, interaction: discord.Interaction):
        user = interaction.user
        points = await self.bot.db.get_points(user.id)
        
        embed = discord.Embed(
            title=f"🎯 Your Points",
            description=f"You currently have **{points}** points!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Earn more by sending messages in counted channels!")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="View point leaderboard (2+ points)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def leaderboard(self, interaction: discord.Interaction):
        all_points = await self.bot.db.get_all_points()
        
        # Filter users with 2+ points
        filtered_points = [(user_id, pts) for user_id, pts in all_points if pts >= 2]
        
        if not filtered_points:
            await interaction.response.send_message("No one has 2+ points yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Point Leaderboard",
            description="Users with 2+ points (highest to lowest)",
            color=discord.Color.gold()
        )
        
        for i, (user_id, pts) in enumerate(filtered_points[:10], 1):
            member = interaction.guild.get_member(user_id)
            if not member:
                continue
            
            medal = ""
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"#{i}"
            
            embed.add_field(
                name=f"{medal} {member.display_name}",
                value=f"🎯 **{pts}** points",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="resetmessages", description="Reset message count for a user (Admin only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    @app_commands.describe(user="User to reset message count for")
    async def resetmessages(self, interaction: discord.Interaction, user: discord.Member):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        await self.bot.db.reset_message_count(user.id)
        await interaction.response.send_message(f"✅ Reset message count for {user.mention}", ephemeral=True)
        logging.info(f"ADMIN: {interaction.user.name} reset message count for {user.name}")
    
    @app_commands.command(name="setchannel", description="View counted channels (Admin only)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def setchannel(self, interaction: discord.Interaction):
        if not self.has_admin_perms(interaction):
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return
        
        channel_list = []
        for channel_id in COUNTED_CHANNELS:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                channel_list.append(f"• {channel.mention}")
            else:
                channel_list.append(f"• Unknown Channel (ID: {channel_id})")
        
        embed = discord.Embed(
            title="📢 Counted Channels",
            description="Messages are counted in these channels:\n\n" + "\n".join(channel_list),
            color=discord.Color.green()
        )
        
        embed.set_footer(text=f"Every {MESSAGES_PER_POINT} messages = 1 point")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(MessageCounter(bot))
