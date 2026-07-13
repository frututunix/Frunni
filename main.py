import os
import json
import random
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Görsel motor fonksiyonları
from gorsel_motoru import hosgeldin_kart_olustur, seviye_kart_olustur, kimlik_kart_olustur

load_dotenv()
TOKEN = os.getenv("TOKEN")
PREFIX = os.getenv("PREFIX", "f!")

# --- YETKİLİ ROLÜ AYARI (BURAYI KENDİ SUNUCUNA GÖRE DÜZENLE) ---
YETKILI_ROL_ID = 123456789012345678  # Ticketları görecek yetkili rolünün ID'sini buraya yapıştır!

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

xp_cooldowns = {}
aktif_cekilisler = {}

ICECEKLER = [
    {"id": "su", "isim": "💧 Su", "fiyat": 10, "sans": 90},
    {"id": "kola", "isim": "🥤 Kola", "fiyat": 50, "sans": 85},
    {"id": "süt", "isim": "🥛 Süt", "fiyat": 20, "sans": 80},
    {"id": "enerji", "isim": "⚡ Enerji İçeceği", "fiyat": 75, "sans": 70},
    {"id": "bira", "isim": "🍺 Bira", "fiyat": 100, "sans": 50},
    {"id": "ziplama", "isim": "🦘 Zıplama İksiri", "fiyat": 1250, "sans": 40},
    {"id": "gorunmezlik", "isim": "👤 Görünmezlik İksiri", "fiyat": 1500, "sans": 35},
    {"id": "can", "isim": "❤️ Can İksiri", "fiyat": 2000, "sans": 20},
    {"id": "olumsuzluk", "isim": "🛡️ Ölümsüzlük İksiri", "fiyat": 5000, "sans": 10},
    {"id": "gizemli", "isim": "🔮 ??? İksiri", "fiyat": 10000, "sans": 1}
]

YEMEKLER = [
    {"id": "ekmek", "isim": "🍞 Ekmek", "fiyat": 10, "sans": 99},
    {"id": "yumurta", "isim": "🥚 Yumurta", "fiyat": 10, "sans": 95},
    {"id": "tost", "isim": "🥪 Tost", "fiyat": 50, "sans": 80},
    {"id": "salata", "isim": "🥗 Salata", "fiyat": 45, "sans": 76},
    {"id": "patates", "isim": "🍟 Patates Kızartması", "fiyat": 65, "sans": 70},
    {"id": "patso", "isim": "🥖 Patso", "fiyat": 75, "sans": 60},
    {"id": "hamburger", "isim": "🍔 Hamburger", "fiyat": 100, "sans": 45},
    {"id": "sonsuzluk", "isim": "🌌 Sonsuzluk Meyvesi", "fiyat": 99999, "sans": 1}
]

# --- VERİ TABANI VE YETKİ FONKSİYONLARI ---
def verileri_yukle():
    try:
        with open("ekonomi.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def verileri_kaydet(veri):
    with open("ekonomi.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def hesap_kontrol(user_id, veri):
    uid = str(user_id)
    if "oyuncular" not in veri: veri["oyuncular"] = {}
    if "market" not in veri: veri["market"] = {"tarih": "", "icecekler": [], "yemekler": []}
    if "ayarlar" not in veri: 
        veri["ayarlar"] = {
            "hosgeldin_kanal": None, 
            "gorusuruz_kanal": None, 
            "seviye_kanal": None, 
            "yetkili_uyeler": [], 
            "yetkili_roller": [],
            "seviye_rolleri": {}
        }
    if "seviye_rolleri" not in veri["ayarlar"]:
        veri["ayarlar"]["seviye_rolleri"] = {}

    if uid not in veri["oyuncular"]:
        veri["oyuncular"][uid] = {
            "cuzdan": 0,
            "banka": 0,
            "seviye": 1,
            "xp": 0,
            "envanter": {},
            "son_yemek_tarihi": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "olum_bitis_tarihi": None
        }
    return veri

def yetkili_mi(ctx, veri):
    if ctx.author.id == ctx.guild.owner_id: return True
    ayarlar = veri.get("ayarlar", {})
    if ctx.author.id in ayarlar.get("yetkili_uyeler", []): return True
    for rol in ctx.author.roles:
        if rol.id in ayarlar.get("yetkili_roller", []): return True
    return False

def marketi_yenile_eger_gerekliyse(veri):
    bugun = datetime.now().strftime("%Y-%m-%d")
    if "market" not in veri or not isinstance(veri["market"], dict):
        veri["market"] = {"tarih": "", "icecekler": [], "yemekler": []}
    if veri["market"].get("tarih") == bugun: return veri

    def reyon_sec(havuz, adet):
        secilenler = []
        for urun in havuz:
            if random.randint(1, 100) <= urun["sans"]:
                yeni_urun = urun.copy()
                secilenler.append(yeni_urun)
        while len(secilenler) < adet and len(secilenler) < len(havuz):
            kalanlar = [u for u in havuz if u["id"] not in [s["id"] for s in secilenler]]
            if not kalanlar: break
            secilenler.append(random.choice(kalanlar).copy())
        return random.sample(secilenler, min(adet, len(secilenler)))

    veri["market"] = {"tarih": bugun, "icecekler": reyon_sec(ICECEKLER, 5), "yemekler": reyon_sec(YEMEKLER, 5)}
    return veri

async def saglik_kontrol_et(ctx):
    veri = verileri_yukle()
    veri = hesap_kontrol(ctx.author.id, veri)
    oyuncu = veri["oyuncular"][str(ctx.author.id)]
    simdi = datetime.now()

    if oyuncu["olum_bitis_tarihi"]:
        olum_bitis = datetime.strptime(oyuncu["olum_bitis_tarihi"], "%Y-%m-%d %H:%M:%S")
        if simdi < olum_bitis:
            kalan = olum_bitis - simdi
            embed = discord.Embed(title="💀 ÖLÜSÜN!", description=f"Mezarından kalkmana **{kalan.days} gün {kalan.seconds//3600} saat** var.", color=discord.Color.dark_red())
            await ctx.send(embed=embed)
            return False
        else:
            oyuncu["olum_bitis_tarihi"] = None
            oyuncu["son_yemek_tarihi"] = simdi.strftime("%Y-%m-%d %H:%M:%S")
            verileri_kaydet(veri)

    son_yemek = datetime.strptime(oyuncu["son_yemek_tarihi"], "%Y-%m-%d %H:%M:%S")
    gecen_gun = (simdi - son_yemek).days

    if gecen_gun >= 15:
        oyuncu["olum_bitis_tarihi"] = (simdi + timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")
        verileri_kaydet(veri)
        await ctx.send("💀 **AÇLIKTAN ÖLDÜN!** 20 gün botu kullanamazsın.")
        return False
    elif gecen_gun >= 10:
        await ctx.send(f"🤒 **UYARI:** {ctx.author.mention} 10 gündür yemek yemedin, acele et!")
    return True

# --- 🎫 TICKET SİSTEMİ (Destek Talebi) ---

class TicketKapatView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Talebi Kapat 🔒", style=discord.ButtonStyle.danger, custom_id="ticket_kapat_buton")
    async def kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Bu kanal 5 saniye içinde silinecek...", ephemeral=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Destek Talebi Aç 🎫", style=discord.ButtonStyle.primary, custom_id="ticket_ac_buton")
    async def ticket_ac(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        yetkili_rol = guild.get_role(YETKILI_ROL_ID)
        category = discord.utils.get(guild.categories, name="Destek Talepleri")
        
        if not category:
            category = await guild.create_category("Destek Talepleri")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        if yetkili_rol:
            overwrites[yetkili_rol] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        channel_name = f"destek-{interaction.user.name.lower()}"
        
        for ch in category.channels:
            if ch.name == channel_name:
                return await interaction.response.send_message("❌ Zaten açık bir talebin var kanka!", ephemeral=True)

        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        
        embed = discord.Embed(
            title="🎫 Destek Talebi",
            description=f"{interaction.user.mention} hoş geldin! Yetkililerimiz kısa sürede sana yardımcı olacak.\n\nİşin bittiğinde aşağıdaki butondan talebi kapatabilirsin.",
            color=discord.Color.blue()
        )
        etiket_mesaji = f"{interaction.user.mention} " + (yetkili_rol.mention if yetkili_rol else "")
        await channel.send(content=etiket_mesaji, embed=embed, view=TicketKapatView())
        await interaction.response.send_message(f"✅ Destek kanalı açıldı: {channel.mention}", ephemeral=True)

@bot.command(name="ticket-panel")
async def ticket_panel_komutu(ctx):
    veri = verileri_yukle()
    if not yetkili_mi(ctx, veri):
        return await ctx.send("❌ Sadece yetkililer ticket paneli kurabilir kanka!")
    
    embed = discord.Embed(
        title="📩 Frunni Destek Sistemi",
        description="Yardıma mı ihtiyacın var? Aşağıdaki butona basarak yetkililerimizle özel olarak görüşmek için bir destek talebi oluşturabilirsin!",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed, view=TicketView())


# --- 🎉 ÇEKİLİŞ COMPONENTLERİ ---

class CekilisSüreSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Dakika", value="60", description="Hızlı test süresi", default=True),
            discord.SelectOption(label="5 Dakika", value="300"),
            discord.SelectOption(label="30 Dakika", value="1800"),
            discord.SelectOption(label="1 Saat", value="3600"),
            discord.SelectOption(label="1 Gün", value="86400")
        ]
        super().__init__(placeholder="⏱️ Süreyi Seçin...", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id: return await interaction.response.defer()
        self.view.süre = int(self.values[0])
        self.view.süre_etiket = [o.label for o in self.options if o.value == self.values[0]][0]
        await self.view.paneli_guncelle(interaction)

class CekilisKazananSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Kazanan", value="1", default=True),
            discord.SelectOption(label="2 Kazanan", value="2"),
            discord.SelectOption(label="3 Kazanan", value="3"),
            discord.SelectOption(label="5 Kazanan", value="5")
        ]
        super().__init__(placeholder="👑 Kazanan Sayısını Seçin...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id: return await interaction.response.defer()
        self.view.kazanan_sayisi = int(self.values[0])
        await self.view.paneli_guncelle(interaction)

class OdulGirisModal(discord.ui.Modal, title="Çekiliş Ödülünü Belirle"):
    odul_input = discord.ui.TextInput(label="Hediye/Ödül Ne Olacak?", placeholder="Örn: 5000 Frunni Parası, VIP Rolü vb.", min_length=1, max_length=100)
    def __init__(self, view_nesnesi):
        super().__init__()
        self.view_nesnesi = view_nesnesi
    async def on_submit(self, interaction: discord.Interaction):
        self.view_nesnesi.odul = self.odul_input.value
        await self.view_nesnesi.paneli_guncelle(interaction)

class BiletFiyatiModal(discord.ui.Modal, title="Bilet Ücretini Belirle"):
    fiyat_input = discord.ui.TextInput(label="Bir Bilet Kaç Frunni Parası?", placeholder="Örn: 250", min_length=1, max_length=10)
    def __init__(self, view_nesnesi):
        super().__init__()
        self.view_nesnesi = view_nesnesi
    async def on_submit(self, interaction: discord.Interaction):
        try:
            fiyat = int(self.fiyat_input.value)
            if fiyat <= 0: raise ValueError()
            self.view_nesnesi.bilet_fiyati = fiyat
            await self.view_nesnesi.paneli_guncelle(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Lütfen sadece pozitif bir tam sayı gir kanka!", ephemeral=True)

class CekilisSetupView(discord.ui.View):
    def __init__(self, ctx, tip="normal"):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.tip = tip
        self.süre = 60
        self.süre_etiket = "1 Dakika"
        self.kazanan_sayisi = 1
        self.odul = None
        self.bilet_fiyati = 100

        self.add_item(CekilisSüreSelect())
        self.add_item(CekilisKazananSelect())

    async def paneli_guncelle(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎉 Frunni Çekiliş Sihirbazı",
            description=f"Aşağıdaki menülerden çekiliş ayarlarını `f!setup` mantığıyla seç kanka, ardından **Başlat** butonuna bas!",
            color=discord.Color.brand_green() if self.tip == "normal" else discord.Color.orange()
        )
        embed.add_field(name="📋 Çekiliş Türü", value=f"`{self.tip.upper()}`", inline=True)
        embed.add_field(name="⏱️ Süre", value=f"`{self.süre_etiket}`", inline=True)
        embed.add_field(name="👑 Kazanan Sayısı", value=f"`{self.kazanan_sayisi} Kişi`", inline=True)
        
        if self.tip == "biletli":
            embed.add_field(name="🎟️ Bilet Ücreti", value=f"`{self.bilet_fiyati}` Frunni Parası", inline=True)
            
        odul_durum = f"**{self.odul}**" if self.odul else "❌ *Henüz Yazılmadı*"
        embed.add_field(name="🎁 Verilecek Ödül", value=odul_durum, inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎁 Ödülü Yaz", style=discord.ButtonStyle.primary, emoji="✍️", row=2)
    async def odul_yaz_buton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        await interaction.response.send_modal(OdulGirisModal(self))

    @discord.ui.button(label="🎟️ Bilet Ücreti Belirle", style=discord.ButtonStyle.secondary, emoji="🪙", row=2)
    async def bilet_ucret_buton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        if self.tip != "biletli":
            return await interaction.response.send_message("❌ Bu ayar sadece biletli çekilişlerde geçerlidir kanka!", ephemeral=True)
        await interaction.response.send_modal(BiletFiyatiModal(self))

    @discord.ui.button(label="🚀 Çekilişi Başlat!", style=discord.ButtonStyle.success, emoji="🎉", row=3)
    async def baslat_buton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        if not self.odul:
            return await interaction.response.send_message("❌ Ödülü belirlemeden çekilişi başlatamam kanka!", ephemeral=True)
        
        await interaction.response.defer()
        await interaction.message.delete()
        asyncio.create_task(self.cekilis_dongusu_calistir())

    async def cekilis_dongusu_calistir(self):
        bitis_zamani = datetime.utcnow() + timedelta(seconds=self.süre)
        timestamp = int(bitis_zamani.timestamp())
        katilimcilar = set()

        katil_view = discord.ui.View(timeout=None)
        buton_label = "Çekilişe Katıl! 🎉" if self.tip == "normal" else f"Bilet Al ({self.bilet_fiyati} 🪙)"
        buton_style = discord.ButtonStyle.success if self.tip == "normal" else discord.ButtonStyle.primary
        
        katil_buton = discord.ui.Button(label=buton_label, style=buton_style, custom_id=f"katil_btn_{random.randint(1000,9999)}")
        
        async def katil_callback(inter: discord.Interaction):
            if self.tip == "normal":
                if inter.user.id in katilimcilar:
                    katilimcilar.remove(inter.user.id)
                    await inter.response.send_message("❌ Çekilişten ayrıldın kanka.", ephemeral=True)
                else:
                    katilimcilar.add(inter.user.id)
                    await inter.response.send_message("✅ Çekilişe başarıyla katıldın! Bol şans.", ephemeral=True)
            else:
                if inter.user.id in katilimcilar:
                    return await inter.response.send_message("👀 Zaten bir bilet almışsın kanka!", ephemeral=True)
                
                veri = verileri_yukle()
                veri = hesap_kontrol(inter.user.id, veri)
                cuzdan = veri["oyuncular"][str(inter.user.id)]["cuzdan"]
                
                if cuzdan < self.bilet_fiyati:
                    return await inter.response.send_message(f"❌ Bakiyen yetersiz! `{self.bilet_fiyati}` Frunni parası gerekiyor.", ephemeral=True)
                
                veri["oyuncular"][str(inter.user.id)]["cuzdan"] -= self.bilet_fiyati
                verileri_kaydet(veri)
                katilimcilar.add(inter.user.id)
                await inter.response.send_message(f"🎟️ `{self.bilet_fiyati}` Frunni parası karşılığında biletini aldın kanka!", ephemeral=True)

            y_embed = inter.message.embeds[0]
            y_embed.set_footer(text=f"Katılımcı Sayısı: {len(katilimcilar)}")
            await inter.message.edit(embed=y_embed)

        katil_buton.callback = katil_callback
        katil_view.add_item(katil_buton)

        if self.tip == "normal":
            embed = discord.Embed(
                title="🎉 BÜYÜK ÇEKİLİŞ BAŞLADI 🎉",
                description=f"**Ödül:** 🎁 {self.odul}\n**Kazanan Sayısı:** `{self.kazanan_sayisi}`\n**Bitiş Süresi:** <t:{timestamp}:R> (<t:{timestamp}:f>)\n\nKatılmak için aşağıdaki butona basın kanka!",
                color=discord.Color.brand_green()
            )
        else:
            embed = discord.Embed(
                title="🎟️ BİLETLİ EKONOMİ ÇEKİLİŞİ 🎟️",
                description=f"**Büyük Ödül:** 🎁 {self.odul}\n**Bilet Ücreti:** `{self.bilet_fiyati}` Frunni Parası\n**Bitiş Süresi:** <t:{timestamp}:R>\n\nŞansını denemek için bilet satın al kanka!",
                color=discord.Color.orange()
            )
        
        embed.set_footer(text="Katılımcı Sayısı: 0")
        mesaj = await self.ctx.send(embed=embed, view=katil_view)

        await asyncio.sleep(self.süre)
        
        katil_buton.disabled = True
        katil_view.clear_items()
        katil_view.add_item(katil_buton)

        if not katilimcilar:
            bitti_embed = discord.Embed(title="🎉 Çekiliş Sona Erdi", description=f"**Ödül:** {self.odul}\n\n❌ Çekilişe katılım olmadığı için kazanan seçilemedi kanka.", color=discord.Color.red())
            await mesaj.edit(embed=bitti_embed, view=katil_view)
            return

        kazananlar = random.sample(list(katilimcilar), min(self.kazanan_sayisi, len(katilimcilar)))
        kazananlar_mentions = ", ".join([f"<@{kid}>" for kid in kazananlar])

        bitti_embed = discord.Embed(
            title="🎉 Çekiliş Sonuçlandı! 🎉",
            description=f"**Ödül:** 🎁 {self.odul}\n\n👑 **Kazananlar:** {kazananlar_mentions}\n✨ Toplam Katılımcı: `{len(katilimcilar)}`",
            color=discord.Color.gold()
        )
        await mesaj.edit(embed=bitti_embed, view=katil_view)
        await self.ctx.send(f"🎊 Tebrikler {kazananlar_mentions}! **{self.odul}** kazandınız, hayırlı olsun!")

@bot.command(name="çekiliş", aliases=["cekilis", "giveaway"])
async def cekilis_komutu(ctx):
    veri = verileri_yukle()
    if not yetkili_mi(ctx, veri):
        return await ctx.send("❌ Çekiliş paneline erişmek için yetkili olmalısın kanka!")
    
    view = CekilisSetupView(ctx, tip="normal")
    embed = discord.Embed(
        title="🎉 Frunni Çekiliş Sihirbazı",
        description=f"Aşağıdaki menülerden çekiliş ayarlarını `f!setup` mantığıyla seç kanka, ardından **Başlat** butonuna bas!",
        color=discord.Color.brand_green()
    )
    embed.add_field(name="📋 Çekiliş Türü", value="`NORMAL`", inline=True)
    embed.add_field(name="⏱️ Süre", value="`1 Dakika`", inline=True)
    embed.add_field(name="👑 Kazanan Sayısı", value="`1 Kişi`", inline=True)
    embed.add_field(name="🎁 Verilecek Ödül", value="❌ *Henüz Yazılmadı*", inline=False)
    
    await ctx.send(embed=embed, view=view)

@bot.command(name="biletli-çekiliş", aliases=["biletlicekilis"])
async def biletli_cekilis_komutu(ctx):
    veri = verileri_yukle()
    if not yetkili_mi(ctx, veri):
        return await ctx.send("❌ Biletli çekiliş paneline erişmek için yetkili olmalısın kanka!")
    
    view = CekilisSetupView(ctx, tip="biletli")
    embed = discord.Embed(
        title="🎉 Frunni Çekiliş Sihirbazı",
        description=f"Aşağıdaki menülerden çekiliş ayarlarını `f!setup` mantığıyla seç kanka, ardından **Başlat** butonuna bas!",
        color=discord.Color.orange()
    )
    embed.add_field(name="📋 Çekiliş Türü", value="`BİLETLİ`", inline=True)
    embed.add_field(name="⏱️ Süre", value="`1 Dakika`", inline=True)
    embed.add_field(name="👑 Kazanan Sayısı", value="`1 Kişi`", inline=True)
    embed.add_field(name="🎟️ Bilet Ücreti", value="`100 Frunni Parası`", inline=True)
    embed.add_field(name="🎁 Verilecek Ödül", value="❌ *Henüz Yazılmadı*", inline=False)
    
    await ctx.send(embed=embed, view=view)


# --- 🛠️ SUNUCU KURULUM PANELİ (SETUP) ---
class SetupView(discord.ui.View):
    def __init__(self, ctx, gecici_ayarlar):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.gecici = gecici_ayarlar

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
        placeholder="👋 Hoş Geldin Kanalı Seç...", custom_id="setup_welcome", row=0
    )
    async def welcome_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        self.gecici["hosgeldin_kanal"] = select.values[0].id
        await interaction.response.send_message(f" Welcomelist güncellendi: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
        placeholder="🏃 Görüşürüz Kanalı Seç...", custom_id="setup_leave", row=1
    )
    async def leave_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        self.gecici["gorusuruz_kanal"] = select.values[0].id
        await interaction.response.send_message(f" Leavelist güncellendi: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(
        cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text],
        placeholder="⭐ Seviye Tebrik Kanalı Seç...", custom_id="setup_level_ch", row=2
    )
    async def level_ch_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        self.gecici["seviye_kanal"] = select.values[0].id
        await interaction.response.send_message(f" Seviye bildirim kanalı güncellendi: {select.values[0].mention}", ephemeral=True)

    @discord.ui.select(
        cls=discord.ui.RoleSelect, placeholder="🎖️ Seviye Rolleri Seçimi (1'den 12'ye sırayla)",
        max_values=12, custom_id="setup_level_roles", row=3
    )
    async def level_roles_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        self.gecici["seviye_rolleri"] = {}
        for index, rol in enumerate(select.values):
            self.gecici["seviye_rolleri"][str(index + 1)] = rol.id
        await interaction.response.send_message(f"✅ Toplam {len(select.values)} adet seviye rolü kuyruğa eklendi kanka!", ephemeral=True)

    @discord.ui.button(label="💾 Ayarları Kaydet", style=discord.ButtonStyle.success, emoji="📥", row=4)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        veri = verileri_yukle()
        veri["ayarlar"]["hosgeldin_kanal"] = self.gecici["hosgeldin_kanal"]
        veri["ayarlar"]["gorusuruz_kanal"] = self.gecici["gorusuruz_kanal"]
        veri["ayarlar"]["seviye_kanal"] = self.gecici["seviye_kanal"]
        veri["ayarlar"]["seviye_rolleri"] = self.gecici["seviye_rolleri"]
        verileri_kaydet(veri)
        self.stop()
        await interaction.response.send_message("🎉 **Mükemmel! Bütün ayarlar başarıyla veri tabanına kaydedildi ve aktif edildi kanka!**", ephemeral=False)

@bot.command(name="setup", aliases=["kurulum", "ayarla"])
async def setup_komutu(ctx):
    veri = verileri_yukle()
    veri = hesap_kontrol(ctx.author.id, veri)
    if not yetkili_mi(ctx, veri):
        await ctx.send("❌ Bu komutu kullanmak için yetkin olmalı kanka!")
        return
    ayarlar = veri["ayarlar"]
    gecici_ayarlar = {
        "hosgeldin_kanal": ayarlar.get("hosgeldin_kanal"),
        "gorusuruz_kanal": ayarlar.get("gorusuruz_kanal"),
        "seviye_kanal": ayarlar.get("seviye_kanal"),
        "seviye_rolleri": ayarlar.get("seviye_rolleri", {})
    }
    embed = discord.Embed(title="⚙️ Frunni Gelişmiş Kurulum Paneli", description="Aşağıdaki menülerden doldurmak istediğin yerleri seçip, en alttaki **Kaydet** butonuna bas kanka!", color=discord.Color.purple())
    hk = f"<#{ayarlar['hosgeldin_kanal']}>" if ayarlar.get("hosgeldin_kanal") else "`Seçilmedi`"
    gk = f"<#{ayarlar['gorusuruz_kanal']}>" if ayarlar.get("gorusuruz_kanal") else "`Seçilmedi`"
    sk = f"<#{ayarlar['seviye_kanal']}>" if ayarlar.get("seviye_kanal") else "`Seçilmedi`"
    embed.add_field(name="👋 Hoş Geldin Kanalı", value=hk, inline=True)
    embed.add_field(name="🏃 Görüşürüz Kanalı", value=gk, inline=True)
    embed.add_field(name="⭐ Seviye Bildirim", value=sk, inline=True)
    rol_yazisi = ""
    eski_roller = ayarlar.get("seviye_rolleri", {})
    for i in range(1, 13):
        r_id = eski_roller.get(str(i))
        rol_yazisi += f"**{i}. Seviye Rolü:** " + (f"<@&{r_id}>\n" if r_id else "`Seçilmedi`\n")
    embed.add_field(name="🎖️ Güncel Seviye Rolleri Sınırı (Max 12)", value=rol_yazisi, inline=False)
    await ctx.send(embed=embed, view=SetupView(ctx, gecici_ayarlar))

@bot.command(name="yetkili")
async def yetkili_komutu(ctx, islem: str = None, tip: str = None, hedef: str = None):
    veri = verileri_yukle()
    veri = hesap_kontrol(ctx.author.id, veri)
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ Bu komutu sadece **Sunucu Sahibi** kullanabilir kanka!")
        return
    if islem is None or tip is None or hedef is None:
        embed = discord.Embed(title="🛡️ Frunni Yetkili Yönetim Sistemi", color=discord.Color.blue())
        embed.description = (
            "**Kullanım Formatları:**\n"
            f"`{PREFIX}yetkili ekle üye @Kullanıcı`\n"
            f"`{PREFIX}yetkili sil üye @Kullanıcı`\n"
            f"`{PREFIX}yetkili ekle rol @Rol`\n"
            f"`{PREFIX}yetkili sil rol @Rol`"
        )
        await ctx.send(embed=embed)
        return
    ayarlar = veri["ayarlar"]
    islem = islem.lower()
    tip = tip.lower()
    if tip in ["üye", "uye"]:
        try:
            member = await commands.MemberConverter().convert(ctx, hedef)
            if islem == "ekle":
                if member.id not in ayarlar["yetkili_uyeler"]:
                    ayarlar["yetkili_uyeler"].append(member.id)
                    await ctx.send(f"✅ {member.mention} artık yetkili!")
            elif islem == "sil":
                if member.id in ayarlar["yetkili_uyeler"]:
                    ayarlar["yetkili_uyeler"].remove(member.id)
                    await ctx.send(f"❌ {member.mention} yetkisi kaldırıldı.")
        except: await ctx.send("❌ Geçerli bir üye etiketle kanka!")
    elif tip == "rol":
        try:
            role = await commands.RoleConverter().convert(ctx, hedef)
            if islem == "ekle":
                if role.id not in ayarlar["yetkili_roller"]:
                    ayarlar["yetkili_roller"].append(role.id)
                    await ctx.send(f"✅ **{role.name}** rolü artık yetkili!")
            elif islem == "sil":
                if role.id in ayarlar["yetkili_roller"]:
                    ayarlar["yetkili_roller"].remove(role.id)
                    await ctx.send(f"❌ **{role.name}** rolünün yetkisi kaldırıldı.")
        except: await ctx.send("❌ Geçerli bir rol etiketle!")
    verileri_kaydet(veri)


# --- EVENTLER (Giriş, Çıkış, Mesaj) ---
@bot.event
async def on_ready():
    print(f"--- {bot.user} başarıyla giriş yaptı ve göreve hazır! ---")
    bot.add_view(TicketView()) # Ticket butonunun bot kapandığında bile çalışması için
    bot.add_view(TicketKapatView())

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    
    await bot.process_commands(message)

    user_id = message.author.id
    simdi = datetime.now()
    if user_id in xp_cooldowns:
        if simdi - xp_cooldowns[user_id] < timedelta(seconds=60): return
    xp_cooldowns[user_id] = simdi

    veri = verileri_yukle()
    veri = hesap_kontrol(user_id, veri)
    oyuncu = veri["oyuncular"][str(user_id)]

    eski_seviye = oyuncu["seviye"]
    if eski_seviye >= 50: return

    oyuncu["xp"] += random.randint(15, 25)
    gerekli_xp = eski_seviye * 100

    if oyuncu["xp"] >= gerekli_xp:
        oyuncu["xp"] -= gerekli_xp
        oyuncu["seviye"] += 1
        yeni_seviye = oyuncu["seviye"]
        
        if yeni_seviye > 50:
            yeni_seviye = 50
            oyuncu["seviye"] = 50
            oyuncu["xp"] = 0

        verileri_kaydet(veri)

        kanal_id = veri.get("ayarlar", {}).get("seviye_kanal")
        target_channel = bot.get_channel(int(kanal_id)) if kanal_id else message.channel
        
        if target_channel:
            kart_bytes = seviye_kart_olustur(message.author.display_avatar.url, message.author.name, yeni_seviye)
            dosya = discord.File(fp=kart_bytes, filename="seviye.png")
            try: await target_channel.send(content=f"🎉 {message.author.mention} Seviye Atladı!", file=dosya)
            except: pass

        seviye_rolleri = veri.get("ayarlar", {}).get("seviye_rolleri", {})
        if str(yeni_seviye) in seviye_rolleri:
            rol_id = seviye_rolleri[str(yeni_seviye)]
            rol = message.guild.get_role(int(rol_id))
            if rol:
                try: 
                    await message.author.add_roles(role)
                    if target_channel:
                        await target_channel.send(f"🎖️ {message.author.mention} tebrikler, **{rol.name}** rolü verildi!")
                except: pass
    else:
        verileri_kaydet(veri)

@bot.event
async def on_member_join(member):
    veri = verileri_yukle()
    kanal_id = veri.get("ayarlar", {}).get("hosgeldin_kanal")
    if kanal_id:
        kanal = bot.get_channel(int(kanal_id))
        if kanal:
            kart_bytes = hosgeldin_kart_olustur(member.display_avatar.url)
            dosya = discord.File(fp=kart_bytes, filename="hosgeldin.png")
            try: await kanal.send(content=f"👋 Selam {member.mention}, aramıza hoş geldin! 🔥", file=dosya)
            except: pass

@bot.event
async def on_member_remove(member):
    veri = verileri_yukle()
    kanal_id = veri.get("ayarlar", {}).get("gorusuruz_kanal")
    if kanal_id:
        kanal = bot.get_channel(int(kanal_id))
        if kanal:
            try: await kanal.send(content=f"😢 **{member.name}** sunucudan ayrıldı. Bir yaprak daha düştü...")
            except: pass


# --- KİMLİK & SIRALAMA SİSTEMİ ---
@bot.command(name="kimlik", aliases=["id", "profil"])
async def kimlik(ctx, uye: discord.Member = None):
    if not await saglik_kontrol_et(ctx): return
    if uye is None: uye = ctx.author

    veri = verileri_yukle()
    veri = hesap_kontrol(uye.id, veri)
    oyuncu = veri["oyuncular"][str(uye.id)]

    seviye = oyuncu["seviye"]
    mevcut_xp = oyuncu["xp"]
    gerekli_xp = seviye * 100
    olusturma_tarihi = uye.created_at.strftime("%d.%m.%Y")

    kart_bytes = kimlik_kart_olustur(
        avatar_url=uye.display_avatar.url, kullanici_adi=uye.name, seviye=seviye,
        mevcut_xp=mevcut_xp, gerekli_xp=gerekli_xp, olusturma_tarihi=olusturma_tarihi
    )
    dosya = discord.File(fp=kart_bytes, filename="kimlik.png")
    await ctx.send(file=dosya)

class SıralamaFiltreView(discord.ui.View):
    def __init__(self, ctx, kapsam):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.kapsam = kapsam

    @discord.ui.button(label="⭐ Seviye Sıralaması", style=discord.ButtonStyle.primary, emoji="📊")
    async def seviye_sirala(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        await interaction.response.defer()
        veri = verileri_yukle()
        oyuncular = veri.get("oyuncular", {})
        sirali_liste = []
        for uid, data in oyuncular.items():
            if self.kapsam == "server":
                member = self.ctx.guild.get_member(int(uid))
                if not member: continue
                isim = member.name
            else:
                user = bot.get_user(int(uid))
                isim = user.name if user else f"Kullanıcı ({uid})"
            sirali_liste.append({"isim": isim, "seviye": data.get("seviye", 1), "xp": data.get("xp", 0)})
        sirali_liste = sorted(sirali_liste, key=lambda x: (x["seviye"], x["xp"]), reverse=True)[:10]
        embed = discord.Embed(title="📊 Seviye Sıralaması", description="👑 **[SUNUCU]**\n\n" if self.kapsam == "server" else "🌍 **[GLOBAL]**\n\n", color=discord.Color.purple())
        for sira, u in enumerate(sirali_liste, 1):
            madalya = "🥇" if sira == 1 else "🥈" if sira == 2 else "🥉" if sira == 3 else f"`#{sira}`"
            embed.description += f"{madalya} **{u['isim']}** - Seviye: `{u['seviye']}` *(XP: {u['xp']})*\n"
        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(label="🪙 Para Sıralaması", style=discord.ButtonStyle.success, emoji="💰")
    async def para_sirala(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        await interaction.response.defer()
        veri = verileri_yukle()
        oyuncular = veri.get("oyuncular", {})
        sirali_liste = []
        for uid, data in oyuncular.items():
            if self.kapsam == "server":
                member = self.ctx.guild.get_member(int(uid))
                if not member: continue
                isim = member.name
            else:
                user = bot.get_user(int(uid))
                isim = user.name if user else f"Kullanıcı ({uid})"
            sirali_liste.append({"isim": isim, "para": data.get("cuzdan", 0)})
        sirali_liste = sorted(sirali_liste, key=lambda x: x["para"], reverse=True)[:10]
        embed = discord.Embed(title="💰 En Zenginler Sıralaması", description="👑 **[SUNUCU]**\n\n" if self.kapsam == "server" else "🌍 **[GLOBAL]**\n\n", color=discord.Color.gold())
        for sira, u in enumerate(sirali_liste, 1):
            madalya = "🥇" if sira == 1 else "🥈" if sira == 2 else "🥉" if sira == 3 else f"`#{sira}`"
            embed.description += f"{madalya} **{u['isim']}** - Bakiye: `{u['para']}`\n"
        await interaction.edit_original_response(embed=embed, view=None)

class SıralamaAnaView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

    @discord.ui.button(label="👑 Sunucu Sıralaması", style=discord.ButtonStyle.primary, emoji="🏠")
    async def server_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        embed = discord.Embed(title="🏠 Sunucu Sıralaması", description="Hangi kritere göre sıralamak istersin kanka?", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=SıralamaFiltreView(self.ctx, "server"))

    @discord.ui.button(label="🌍 Global Sıralama", style=discord.ButtonStyle.secondary, emoji="🚀")
    async def global_click(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id: return await interaction.response.defer()
        embed = discord.Embed(title="🌍 Küresel Sıralama", description="Tüm bot genelinde liderlik tablosu:", color=discord.Color.orange())
        await interaction.response.edit_message(embed=embed, view=SıralamaFiltreView(self.ctx, "global"))

@bot.command(name="sıralama", aliases=["top", "leaderboard", "lb"])
async def sıralama_komutu(ctx):
    if not await saglik_kontrol_et(ctx): return
    embed = discord.Embed(title="🏆 Frututunix Sıralama Merkezi", description="Lütfen görmek istediğin liderlik panosu kapsamını seç kanka!", color=discord.Color.magenta())
    await ctx.send(embed=embed, view=SıralamaAnaView(ctx))


# --- 🎮 EKONOMİ VE EĞLENCE KOMUTLARI ---
@bot.command(name="ship")
async def ship(ctx, uye: discord.Member = None):
    if not await saglik_kontrol_et(ctx): return
    if uye is None:
        aktif_uyeler = [m for m in ctx.guild.members if not m.bot and m.id != ctx.author.id]
        if not aktif_uyeler: return await ctx.send("❌ Shipleyebileceğim kimse yok!")
        uye = random.choice(aktif_uyeler)
    oran = random.randint(0, 100)
    embed = discord.Embed(title="💘 Frunni Aşk Ölçer", description=f"**{ctx.author.mention}** ile **{uye.mention}** arasındaki aşk uyumu: %{oran}", color=discord.Color.red())
    await ctx.send(embed=embed)

@bot.command(name="yardım", aliases=["help", "y"])
async def yardim(ctx):
    if not await saglik_kontrol_et(ctx): return
    embed = discord.Embed(title="🌟 Frunni Bot - Komut Listesi", color=discord.Color.gold())
    embed.add_field(name="💰 Ekonomi & Kumar", value="`f!para` - Cüzdanını gösterir.\n`f!cf <miktar>` - Yazı-tura oyunu.\n`f!slot <miktar>` - Slot makinesi.\n`f!günlük` - Günlük paranı alır.\n`f!send @üye <miktar>` - Para gönderir.", inline=False)
    embed.add_field(name="💼 Gelişim", value="`f!work` / `f!calis` - Çalışarak para kazanır.", inline=False)
    embed.add_field(name="🎉 Gelişmiş Çekiliş Sistemleri", value="`f!çekiliş` - İnteraktif normal çekiliş sihirbazını açar.\n`f!biletli-çekiliş` - Parayla bilet alınan çekiliş sihirbazını açar.", inline=False)
    embed.add_field(name="🛠️ Sunucu Yönetimi", value="`f!yetkili ekle/sil üye/rol` - Bot yetkililerini belirler.\n`f!setup` - Giriş, çıkış, seviye kanallarını ve rollerini ayarlar.\n`f!ticket-panel` - Destek (Ticket) oluşturma butonunu kanala kurar.", inline=False)
    embed.add_field(name="🛒 Market & Yaşam", value="`f!market` - Günlük marketi açar.\n`f!satınal <id>` - Eşya satın alır.\n`f!envanter` - Çantanızı gösterir.\n`f!ye <id>` - Yemek yer, açlığı giderir.\n`f!sağlık` - Açlık durumunu gösterir.\n`f!kimlik` - Görsel profil kartınızı basar.\n`f!sıralama` - Gelişmiş sıralama menüsü.", inline=False)
    embed.add_field(name="❤️ Eğlence", value="`f!ship @üye` - Aşk uyumunuzu test eder.", inline=False)
    embed.set_footer(text=f"Prefix: {PREFIX}")
    await ctx.send(embed=embed)

@bot.command(name="work", aliases=["calis", "çalış"])
@commands.cooldown(1, 30, commands.BucketType.user)
async def work(ctx):
    if not await saglik_kontrol_et(ctx): return
    veri = verileri_yukle(); uid = str(ctx.author.id); veri = hesap_kontrol(uid, veri)
    kazanc = random.randint(50, 250); veri["oyuncular"][uid]["cuzdan"] += kazanc; verileri_kaydet(veri)
    await ctx.send(f"💼 **{ctx.author.name}**, çalıştın ve `{kazanc}` Frunni parası kazandın!")

@bot.command(name="market", aliases=["dükkan"])
async def market(ctx):
    if not await saglik_kontrol_et(ctx): return
    veri = verileri_yukle(); veri = marketi_yenile_eger_gerekliyse(veri); verileri_kaydet(veri)
    embed = discord.Embed(title="🛒 Frunni Günlük Marketi", color=discord.Color.green())
    icecek_text = "".join([f"🔹 `{u['id']}` - **{u['isim']}** | Fiyat: `{u['fiyat']}`\n" for u in veri["market"]["icecekler"]])
    embed.add_field(name="🥤 İçecek", value=icecek_text, inline=False)
    yemek_text = "".join([f"🔸 `{u['id']}` - **{u['isim']}** | Fiyat: `{u['fiyat']}`\n" for u in veri["market"]["yemekler"]])
    embed.add_field(name="🍔 Yemek", value=yemek_text, inline=False)
    await ctx.send(embed=embed)

@bot.command(name="satınal", aliases=["buy"])
async def satınal(ctx, urun_id: str = None):
    if not await saglik_kontrol_et(ctx): return
    if urun_id is None: return
    veri = verileri_yukle(); veri = marketi_yenile_eger_gerekliyse(veri); uid = str(ctx.author.id); veri = hesap_kontrol(uid, veri)
    urun = next((u for u in veri["market"]["icecekler"]+veri["market"]["yemekler"] if u["id"] == urun_id.lower()), None)
    if not urun or veri["oyuncular"][uid]["cuzdan"] < urun["fiyat"]: return
    veri["oyuncular"][uid]["cuzdan"] -= urun["fiyat"]
    veri["oyuncular"][uid]["envanter"][urun["id"]] = veri["oyuncular"][uid]["envanter"].get(urun["id"], 0) + 1
    verileri_kaydet(veri); await ctx.send(f"🛒 **{ctx.author.name}**, 1 adet **{urun['isim']}** aldın!")

@bot.command(name="envanter", aliases=["inv"])
async def envanter(ctx):
    if not await saglik_kontrol_et(ctx): return
    veri = verileri_yukle(); veri = hesap_kontrol(ctx.author.id, veri)
    env = veri["oyuncular"][str(ctx.author.id)]["envanter"]
    text = "".join([f"📦 **{u['isim']}** - `{adet} adet` (Kodu: `{eid}`)\n" for eid, adet in env.items() if adet > 0 for u in ICECEKLER+YEMEKLER if u["id"] == eid])
    await ctx.send(embed=discord.Embed(title=f"🎒 Envanter", description=text or "Çantan bomboş!", color=discord.Color.blue()))

@bot.command(name="ye", aliases=["iç"])
async def ye(ctx, urun_id: str = None):
    if not await saglik_kontrol_et(ctx): return
    if urun_id is None: return
    veri = verileri_yukle(); uid = str(ctx.author.id); veri = hesap_kontrol(uid, veri)
    if urun_id.lower() not in veri["oyuncular"][uid]["envanter"] or veri["oyuncular"][uid]["envanter"][urun_id.lower()] <= 0: return
    veri["oyuncular"][uid]["envanter"][urun_id.lower()] -= 1
    veri["oyuncular"][uid]["son_yemek_tarihi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    verileri_kaydet(veri); await ctx.send(f"🍔 Ürünü tükettin kanka! Açlığın sıfırlandı.")

@bot.command(name="sağlık", aliases=["durum"])
async def saglik(ctx):
    veri = verileri_yukle(); veri = hesap_kontrol(ctx.author.id, veri); oyuncu = veri["oyuncular"][str(ctx.author.id)]
    son_yemek = datetime.strptime(oyuncu["son_yemek_tarihi"], "%Y-%m-%d %H:%M:%S")
    gecen_gun = (datetime.now() - son_yemek).days
    await ctx.send(f"🩺 Seviye: `{oyuncu['seviye']}` | `{gecen_gun}` gündür yemek yemedin.")

@bot.command(name="send")
async def send_money(ctx, uye: discord.Member = None, miktar: str = None):
    if not await saglik_kontrol_et(ctx): return
    if uye is None or miktar is None: return
    veri = verileri_yukle(); uid, aid = str(ctx.author.id), str(uye.id); veri = hesap_kontrol(uid, veri); veri = hesap_kontrol(aid, veri)
    m = veri["oyuncular"][uid]["cuzdan"] if miktar.lower() == "all" else int(miktar)
    if veri["oyuncular"][uid]["cuzdan"] >= m and m > 0:
        veri["oyuncular"][uid]["cuzdan"] -= m; veri["oyuncular"][aid]["cuzdan"] += m
        verileri_kaydet(veri); await ctx.send(f"💸 `{m}` Frunni parası gönderildi!")

@bot.command(name="günlük")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def gunluk(ctx):
    if not await saglik_kontrol_et(ctx): return
    veri = verileri_yukle(); veri = hesap_kontrol(ctx.author.id, veri)
    odul = random.randint(100, 1000); veri["oyuncular"][str(ctx.author.id)]["cuzdan"] += odul
    verileri_kaydet(veri); await ctx.send(f"🎁 Bugünün şansına `{odul}` Frunni parası kaptın!")

@bot.command(name="para", aliases=["cash"])
async def para(ctx):
    if not await saglik_kontrol_et(ctx): return
    veri = verileri_yukle(); veri = hesap_kontrol(ctx.author.id, veri)
    await ctx.send(f"🪙 Cüzdanın: `{veri['oyuncular'][str(ctx.author.id)]['cuzdan']}` Frunni parası.")

@bot.command(name="cf")
async def coinflip(ctx, miktar: str = None):
    if not await saglik_kontrol_et(ctx): return
    if miktar is None: return
    veri = verileri_yukle(); uid = str(ctx.author.id); veri = hesap_kontrol(ctx.author.id, veri)
    mevcut = veri["oyuncular"][uid]["cuzdan"]
    m = mevcut if miktar.lower() == "all" else int(miktar)
    if mevcut >= m and m > 0:
        if random.randint(1, 2) == 1: veri["oyuncular"][uid]["cuzdan"] += m; await ctx.send(f"🎉 Kazandın! `+{m}`")
        else: veri["oyuncular"][uid]["cuzdan"] -= m; await ctx.send(f"😭 Kaybettin! `-{m}`")
        verileri_kaydet(veri)

@bot.command(name="slot")
async def slot(ctx, miktar: int = None):
    if not await saglik_kontrol_et(ctx): return
    if miktar is None or miktar <= 0: return
    veri = verileri_yukle(); uid = str(ctx.author.id); veri = hesap_kontrol(ctx.author.id, veri)
    if veri["oyuncular"][uid]["cuzdan"] < miktar: return
    emojiler = ["🍒", "🍇", "🍋", "💎"]
    s1, s2, s3 = random.choice(emojiler), random.choice(emojiler), random.choice(emojiler)
    await ctx.send(f"🎰 **[ {s1} | {s2} | {s3} ]**")
    if s1 == s2 == s3: veri["oyuncular"][uid]["cuzdan"] += miktar * 3
    elif s1 == s2 or s2 == s3 or s1 == s3: veri["oyuncular"][uid]["cuzdan"] += int(miktar * 1.5)
    else: veri["oyuncular"][uid]["cuzdan"] -= miktar
    verileri_kaydet(veri)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound): return
    elif isinstance(error, commands.CommandOnCooldown): await ctx.send(f"⏱️ Sakin kanka: `{error.retry_after:.1f}` saniye.")

if TOKEN:
    bot.run(TOKEN)