# ✂️ Sartarosh Navbat Boti

## Faylllar tarkibi

```
sartarosh_bot/
├── bot.py           — Asosiy fayl (ishga tushirish)
├── handlers.py      — Barcha amallar (handlers)
├── database.py      — Ma'lumotlar bazasi (JSON)
├── config.py        — Token va Owner ID
├── requirements.txt — Kutubxonalar
└── appointments.json — Navbatlar (avtomatik yaratiladi)
```

---

## O'rnatish va ishga tushirish

### 1. Python o'rnatilganligini tekshiring
```bash
python --version   # 3.9+ bo'lishi kerak
```

### 2. Kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

### 3. config.py ni to'ldiring
```python
BOT_TOKEN = "1234567890:ABC..."   # @BotFather dan olingan token
OWNER_ID  = 987654321             # Sizning Telegram ID
```

**Telegram ID ni bilish uchun:** @userinfobot ga /start yuboring

### 4. Botni ishga tushiring
```bash
python bot.py
```

---

## Imkoniyatlar

### Mijoz uchun:
| Amal | Tavsif |
|------|--------|
| ✂️ Navbat olish | Vaqt, ism, telefon kiritib navbat olish |
| ❌ Bekor qilish | O'z navbatini bekor qilish |

### Bot egasi uchun:
| Amal | Tavsif |
|------|--------|
| 📋 Ro'yxat | Barcha navbatlarni ko'rish |
| ❌ Bekor qilish | Istalgan navbatni bekor qilish |
| 📅 Kechiktirish | Barcha navbatlarni ertangi kunga o'tkazish + mijozlarga SMS |

---

## Vaqt formati
Mijozlar vaqtni quyidagi formatda kiritishi kerak:
```
YYYY-MM-DD HH:MM
Masalan: 2025-06-15 14:00
```

---

## Serverga joylash (bepul)

### Railway.app (tavsiya etiladi):
1. https://railway.app ga kiring
2. GitHub repoga kod yuklang
3. New Project → Deploy from GitHub
4. Environment Variables: `BOT_TOKEN` va `OWNER_ID`
5. Start command: `python bot.py`

### Render.com:
1. https://render.com ga kiring
2. Web Service → Connect GitHub
3. Build: `pip install -r requirements.txt`
4. Start: `python bot.py`
