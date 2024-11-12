import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='+', intents=intents)

GUILD_ID = 13002
CATEGORY_TICKET_ID = 13002
ROLE_SUPPORT_ID = 13002

def load_message_ids():
    if os.path.exists('message_ids.json'):
        with open('message_ids.json', 'r') as f:
            return json.load(f)
    return {}

def save_message_ids(data):
    with open('message_ids.json', 'w') as f:
        json.dump(data, f)

message_ids = load_message_ids()

@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user.name}')
    
    if "ticket_message_id" in message_ids:
        try:
            channel = bot.get_channel(message_ids["ticket_channel_id"])
            message = await channel.fetch_message(message_ids["ticket_message_id"])
            await attach_ticket_buttons(message)
        except discord.NotFound:
            print("Le message du ticket n'existe plus, il sera recréé.")
        except Exception as e:
            print(f"Erreur lors de la récupération du message : {e}")

async def attach_ticket_buttons(message):
    button = Button(label="Créer un Ticket", style=discord.ButtonStyle.blurple, emoji="📩")

    async def create_ticket_callback(interaction):
        try:
            guild = interaction.guild
            member = interaction.user

            category = guild.get_channel(CATEGORY_TICKET_ID)
            existing_channel = discord.utils.get(category.text_channels, name=f"ticket-{member.name.lower()}")

            if existing_channel:
                await interaction.response.send_message("Vous avez déjà un ticket ouvert, un membre de notre équipe s'en occupera bientôt.", ephemeral=True)
            else:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    member: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
                    guild.get_role(ROLE_SUPPORT_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
                }

                ticket_channel = await category.create_text_channel(
                    f"ticket-{member.name}", 
                    topic=f"Ticket pour {member.name}",
                    overwrites=overwrites
                )
                
                await ticket_channel.send(f"{member.mention}, je suis la secrétaire des EMS, que puis-je faire pour vous ?")
                
                close_button = Button(label="Fermer le Ticket", style=discord.ButtonStyle.red)

                async def close_ticket_callback(interaction):
                    await ticket_channel.delete(reason="Ticket fermé")

                close_button.callback = close_ticket_callback
                close_view = View(timeout=None)
                close_view.add_item(close_button)
                
                await ticket_channel.send("Ce ticket est confidentiel : seuls le personnel et vous-même y avez accès.", view=close_view)
                await interaction.response.send_message("Votre ticket a été créé avec succès. Merci de patienter, un membre de notre équipe vous répondra bientôt.", ephemeral=True)
        except Exception as e:
            print(f"Erreur dans create_ticket_callback : {str(e)}")

    button.callback = create_ticket_callback
    view = View(timeout=None)
    view.add_item(button)

    await message.edit(view=view)

@bot.command()
@commands.has_role(ROLE_SUPPORT_ID)
async def ticket(ctx):
    embed = discord.Embed(
        title="Souhaitez-vous créer un ticket d'assistance ?",
        description=(
            "Pour toute demande, cliquez sur le bouton 'Créer un Ticket' ci-dessous. "
            "Notre équipe se fera un plaisir de vous assister dès que possible."
        ),
        color=0xF3C127
    )
    message = await ctx.send(embed=embed)
    await attach_ticket_buttons(message)
    
    message_ids["ticket_message_id"] = message.id
    message_ids["ticket_channel_id"] = ctx.channel.id
    save_message_ids(message_ids)

@ticket.error
async def ticket_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")

bot.run('TOKEN')
