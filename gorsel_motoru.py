import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from io import BytesIO

def hosgeldin_kart_olustur(avatar_url):
    try:
        base_img = Image.open("welcome.png").convert("RGBA")
    except FileNotFoundError:
        base_img = Image.new("RGBA", (1000, 563), (40, 40, 40, 255))

    response = requests.get(avatar_url)
    avatar_img = Image.open(BytesIO(response.content)).convert("RGBA")
    
    yeni_boyut = 300
    avatar_img = avatar_img.resize((yeni_boyut, yeni_boyut))

    mask = Image.new("L", (yeni_boyut, yeni_boyut), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, yeni_boyut, yeni_boyut), fill=255)
    
    yuvarlak_avatar = ImageOps.fit(avatar_img, (yeni_boyut, yeni_boyut), centering=(0.5, 0.5))
    yuvarlak_avatar.putalpha(mask)

    base_img.paste(yuvarlak_avatar, (25, 235), yuvarlak_avatar)

    b = BytesIO()
    base_img.save(b, format="PNG")
    b.seek(0)
    return b

def seviye_kart_olustur(avatar_url, kullanici_adi, yeni_seviye):
    response = requests.get(avatar_url)
    raw_avatar = Image.open(BytesIO(response.content)).convert("RGBA")
    
    kart_w, kart_h = 800, 450
    
    bg_img = raw_avatar.resize((kart_w, kart_w))
    bg_img = bg_img.crop((0, (kart_w - kart_h)//2, kart_w, (kart_w + kart_h)//2))
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=15))
    
    overlay = Image.new("RGBA", (kart_w, kart_h), (0, 0, 0, 120))
    bg_img = Image.alpha_composite(bg_img, overlay)

    mask_kart = Image.new("L", (kart_w, kart_h), 0)
    draw_mask_kart = ImageDraw.Draw(mask_kart)
    draw_mask_kart.rounded_rectangle([0, 0, kart_w, kart_h], radius=35, fill=255)
    
    son_kart = Image.new("RGBA", (kart_w, kart_h))
    son_kart.paste(bg_img, (0, 0), mask_kart)
    draw = ImageDraw.Draw(son_kart)

    av_size = 190
    avatar_img = raw_avatar.resize((av_size, av_size))
    
    av_x = (kart_w - av_size) // 2
    av_y = 65

    mask_av = Image.new("L", (av_size, av_size), 0)
    draw_mask_av = ImageDraw.Draw(mask_av)
    draw_mask_av.rounded_rectangle([0, 0, av_size, av_size], radius=25, fill=255)
    
    yuvarlak_pp = Image.new("RGBA", (av_size, av_size))
    yuvarlak_pp.paste(avatar_img, (0, 0), mask_av)
    
    son_kart.paste(yuvarlak_pp, (av_x, av_y), yuvarlak_pp)
    draw.rounded_rectangle([av_x - 3, av_y - 3, av_x + av_size + 3, av_y + av_size + 3], radius=25, outline=(147, 112, 219, 255), width=3)

    try:
        font_ana = ImageFont.truetype("arial.ttf", 36)
        font_alt = ImageFont.truetype("arial.ttf", 32)
    except:
        font_ana = ImageFont.load_default()
        font_alt = ImageFont.load_default()

    metin1 = f"{kullanici_adi.upper()} SEVİYE ATLADI!"
    metin2 = f"YENİ SEVIYESİ : {yeni_seviye}"
    
    draw.text((kart_w // 2, 295), metin1, fill=(255, 255, 255), font=font_ana, anchor="mm")
    draw.text((kart_w // 2, 365), metin2, fill=(255, 20, 147), font=font_alt, anchor="mm")

    b = BytesIO()
    son_kart.save(b, format="PNG")
    b.seek(0)
    return b

# 🆔 YENİ: KİMLİK KARTINI OLUŞTURMA FONKSİYONU
def kimlik_kart_olustur(avatar_url, kullanici_adi, seviye, mevcut_xp, gerekli_xp, olusturma_tarihi):
    response = requests.get(avatar_url)
    raw_avatar = Image.open(BytesIO(response.content)).convert("RGBA")
    
    # Kimlik kartı boyutları (Dikdörtgen)
    kart_w, kart_h = 750, 400
    
    # Arka plan için PP'den bulanık şablon üretiyoruz
    bg_img = raw_avatar.resize((kart_w, kart_w))
    bg_img = bg_img.crop((0, (kart_w - kart_h)//2, kart_w, (kart_w + kart_h)//2))
    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=18))
    
    # Kartı koyulaştırma katmanı
    overlay = Image.new("RGBA", (kart_w, kart_h), (15, 15, 15, 160))
    bg_img = Image.alpha_composite(bg_img, overlay)

    # 🎴 Kartın Dış Kenarlarını Yumuşatma
    mask_kart = Image.new("L", (kart_w, kart_h), 0)
    draw_mask_kart = ImageDraw.Draw(mask_kart)
    draw_mask_kart.rounded_rectangle([0, 0, kart_w, kart_h], radius=30, fill=255)
    
    son_kart = Image.new("RGBA", (kart_w, kart_h))
    son_kart.paste(bg_img, (0, 0), mask_kart)
    draw = ImageDraw.Draw(son_kart)

    # 🖼️ Sol Üst Profil Resmi (Yumuşak Kenarlı)
    av_size = 140
    avatar_img = raw_avatar.resize((av_size, av_size))
    av_x, av_y = 40, 40

    mask_av = Image.new("L", (av_size, av_size), 0)
    draw_mask_av = ImageDraw.Draw(mask_av)
    draw_mask_av.rounded_rectangle([0, 0, av_size, av_size], radius=20, fill=255)
    
    yuvarlak_pp = Image.new("RGBA", (av_size, av_size))
    yuvarlak_pp.paste(avatar_img, (0, 0), mask_av)
    
    son_kart.paste(yuvarlak_pp, (av_x, av_y), yuvarlak_pp)
    # PP etrafına mor şık bir çerçeve çiziyoruz
    draw.rounded_rectangle([av_x - 2, av_y - 2, av_x + av_size + 2, av_y + av_size + 2], radius=20, outline=(147, 112, 219, 255), width=2)

    try:
        font_isim = ImageFont.truetype("arial.ttf", 34)
        font_bilgi = ImageFont.truetype("arial.ttf", 24)
        font_alt = ImageFont.truetype("arial.ttf", 22)
    except:
        font_isim = font_bilgi = font_alt = ImageFont.load_default()

    # 📝 Yazı Yerleşimleri
    # PP'nin Sağındaki Alan (İsim ve Seviye)
    draw.text((200, 55), kullanici_adi, fill=(255, 255, 255), font=font_isim)
    draw.text((200, 110), f"Seviye: {seviye}", fill=(255, 20, 147), font=font_bilgi)

    # PP'nin Altındaki Alan (Hesap Oluşturma Tarihi)
    draw.text((40, 210), f"Kuruluş Tarihi:\n{olusturma_tarihi}", fill=(180, 180, 180), font=font_bilgi)

    # Tarihin Sağındaki Alan (XP Durumu)
    draw.text((420, 210), f"Deneyim Puanı (XP):\n{mevcut_xp} / {gerekli_xp}", fill=(0, 220, 255), font=font_bilgi)

    # En Alt Ortadaki Metin
    draw.text((kart_w // 2, 355), "Frututunix Kimliği", fill=(147, 112, 219, 200), font=font_alt, anchor="mm")

    b = BytesIO()
    son_kart.save(b, format="PNG")
    b.seek(0)
    return b