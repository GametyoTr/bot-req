# NykoPlus Discord Bot
# Railway deployment uyumlu ve Slash Komut altyapili

import discord
from discord.ext import commands
from discord import app_commands
import os
import json

# Bot Yetkileri ve Intents Ayarlari
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Ayarların Saklanacağı Veri Yapısı (Ticket Ayarları İçin)
TICKET_CONFIG_FILE = "ticket_config.json"

def load_ticket_config():
    if os.path.exists(TICKET_CONFIG_FILE):
        with open(TICKET_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_ticket_config(data):
    with open(TICKET_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Ticket Butonlari ve Etkilesim Menusu
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Ac", style=discord.ButtonStyle.primary, custom_id="nkop_create_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_id = str(interaction.guild_id)
        config = load_ticket_config()

        if guild_id not in config or "destek_rol" not in config[guild_id]:
            await interaction.response.send_message("Lutfen once /ticket-ayarlar komutu ile destek ekibi rolunu belirleyin", ephemeral=True)
            return

        destek_rol_id = config[guild_id]["destek_rol"]
        destek_rol = interaction.guild.get_role(destek_rol_id)
        kategori_id = config[guild_id].get("kategori")
        kategori = interaction.guild.get_channel(kategori_id) if kategori_id else None

        if not destek_rol:
            await interaction.response.send_message("Ayarlanan destek ekibi rolu sunucuda bulunamadi Lutfen tekrar ayarlayin", ephemeral=True)
            return

        # Kanal Yetkileri Ayarlama
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            destek_rol: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel_name = f"ticket-{interaction.user.name}"
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=kategori,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"Ticket kanaliniz olusturuldu: {ticket_channel.mention}", ephemeral=True)

        embed = discord.Embed(
            title=f"Ticket Destek - {interaction.guild.name}",
            description=f"Merhaba {interaction.user.mention} Destek ekibimiz en kisa sürede sizinle ilgilenecektir\nIslemler icin asagidaki butonlari kullanabilirsiniz",
            color=discord.Color.green()
        )

        await ticket_channel.send(
            content=f"{interaction.user.mention} {destek_rol.mention}",
            embed=embed,
            view=TicketControlView()
        )

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Kanalı Kapat", style=discord.ButtonStyle.danger, custom_id="nkop_close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Kanal 5 saniye icinde kapatiliyor")
        await discord.utils.sleep_until(discord.utils.utcnow() + datetime.timedelta(seconds=5))
        await interaction.channel.delete()

    @discord.ui.button(label="Kullanici Ekle", style=discord.ButtonStyle.secondary, custom_id="nkop_add_user", emoji="👤")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddUserModal())

    @discord.ui.button(label="Devret", style=discord.ButtonStyle.primary, custom_id="nkop_transfer_ticket", emoji="🔄")
    async def transfer_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TransferModal())

class AddUserModal(discord.ui.Modal, title="Kanala Kullanici Ekle"):
    user_id = discord.ui.TextInput(label="Kullanici ID", placeholder="Eklenecek kullanicinin ID nosunu girin")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = await interaction.guild.fetch_member(int(self.user_id.value))
            if member:
                await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)
                await interaction.response.send_message(f"{member.mention} bu tickete eklendi")
            else:
                await interaction.response.send_message("Kullanici bulunamadi", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Gecerli bir ID giriniz", ephemeral=True)

class TransferModal(discord.ui.Modal, title="Ticket Devret"):
    user_id = discord.ui.TextInput(label="Devredilecek Kullanici ID", placeholder="Yetki verilecek kullanicinin ID nosu")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = await interaction.guild.fetch_member(int(self.user_id.value))
            if member:
                await interaction.channel.set_permissions(member, read_messages=True, send_messages=True, manage_channels=True)
                await interaction.response.send_message(f"Ticket yetkisi {member.mention} kullanicisina devredildi")
            else:
                await interaction.response.send_message("Kullanici bulunamadi", ephemeral=True)
        except Exception:
            await interaction.response.send_message("Gecerli bir ID giriniz", ephemeral=True)

# Bot Hazır Olduğunda Çalışacak Kısım
@bot.event
async def on_ready():
    print(f"NykoPlus Aktif: {bot.user.name}")
    bot.add_view(TicketView())
    bot.add_view(TicketControlView())
    try:
        synced = await bot.tree.sync()
        print(f"Toplam {len(synced)} slash komutu senkronize edildi")
    except Exception as e:
        print(f"Komutlar senkronize edilirken hata olustu: {e}")

# Ticket Ayarlar Komutu
@bot.tree.command(name="ticket-ayarlar", description="Ticket sisteminin destek rolunu ve kategorisini ayarlar")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_ayarlar(interaction: discord.Interaction, destek_rol: discord.Role, kategori: discord.CategoryChannel = None):
    config = load_ticket_config()
    guild_id = str(interaction.guild_id)

    config[guild_id] = {
        "destek_rol": destek_rol.id,
        "kategori": kategori.id if kategori else None
    }
    save_ticket_config(config)

    await interaction.response.send_message(f"Ticket ayarlar kaydedildi Destek rolu: {destek_rol.name}", ephemeral=True)

@ticket_ayarlar.error
async def ticket_ayarlar_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin Yönetici yetkisine sahip olmalisiniz", ephemeral=True)

# Ticket Panel Komutu
@bot.tree.command(name="ticket-panel", description="Herkese acik ticket panelini kanala atar")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    config = load_ticket_config()

    if guild_id not in config or "destek_rol" not in config[guild_id]:
        await interaction.response.send_message("Sistem kurulmamis Lutfen once /ticket-ayarlar komutunu kullanin", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"Destek Sistemi - {interaction.guild.name}",
        description="Destek talebi olusturmak icin asagidaki tusa basiniz",
        color=discord.Color.blue()
    )
    embed.set_footer(text="NykoPlus Ticket Sistemi")

    await interaction.response.send_message("Panel olusturuldu", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketView())

# Genel Moderasyon Komutları (Yetkiye Göre Filtreli)

@bot.tree.command(name="sil", description="Belirtilen miktarda mesaji siler")
@app_commands.checks.has_permissions(manage_messages=True)
async def sil(interaction: discord.Interaction, sayi: int):
    if sayi < 1 or sayi > 100:
        await interaction.response.send_message("Lutfen 1 ile 100 arasinda bir sayi girin", ephemeral=True)
        return
    deleted = await interaction.channel.purge(limit=sayi)
    await interaction.response.send_message(f"{len(deleted)} adet mesaj silindi", ephemeral=True)

@sil.error
async def sil_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin Mesajlari Yonet yetkisine sahip olmalisiniz", ephemeral=True)

@bot.tree.command(name="ban", description="Kullaniciyi sunucudan yasaklar")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await kullanici.ban(reason=sebep)
    await interaction.response.send_message(f"{kullanici.mention} sunucudan yasaklandi Sebep: {sebep}")

@ban.error
async def ban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin Uyeleri Yasakla yetkisine sahip olmalisiniz", ephemeral=True)

@bot.tree.command(name="kick", description="Kullaniciyi sunucudan atar")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, kullanici: discord.Member, sebep: str = "Sebep belirtilmedi"):
    await kullanici.kick(reason=sebep)
    await interaction.response.send_message(f"{kullanici.mention} sunucudan atildi Sebep: {sebep}")

@kick.error
async def kick_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin Uyeleri At yetkisine sahip olmalisiniz", ephemeral=True)

@bot.tree.command(name="mute", description="Kullaniciyi zamansal olarak susturur")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, kullanici: discord.Member, dakika: int, sebep: str = "Sebep belirtilmedi"):
    import datetime
    duration = datetime.timedelta(minutes=dakika)
    await kullanici.timeout(duration, reason=sebep)
    await interaction.response.send_message(f"{kullanici.mention} {dakika} dakika boyunca susturuldu Sebep: {sebep}")

@mute.error
async def mute_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin Uyeleri Zamana Asimina Ugrat yetkisine sahip olmalisiniz", ephemeral=True)

@bot.tree.command(name="unmute", description="Kullanicinin susturmasini kaldirir")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, kullanici: discord.Member):
    await kullanici.timeout(None)
    await interaction.response.send_message(f"{kullanici.mention} susturmasi kaldirildi")

@unmute.error
async def unmute_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Bu komutu kullanmak icin Uyeleri Zamana Asimina Ugrat yetkisine sahip olmalisiniz", ephemeral=True)

# Railway Uyumlu Bot Baslatma Kodu
if __name__ == "__main__":
    import datetime
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("HATA: DISCORD_TOKEN degiskeni Railway Variables icinde bulunamadi!")
    else:
        bot.run(TOKEN)
