import os
import re
import json
import time
import html
import threading
import urllib.request
from datetime import date
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_ID")
DB_CHANNEL_ID = os.environ.get("DB_CHANNEL_ID")  # Private Channel ID (-100xxxxxxxxxx)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ====================================================
# အခြေခံ အချက်အလက်များ
# ====================================================
KPAY_NUMBER = "09764199664"
KPAY_NAME = "Min Zayar Oo"
BOT_LINK = "http://t.me/TranslateMovies2vip_bot"
CONTACT_1 = "@moon_translate25"
CONTACT_2 = "@beststoryken"

daily_members_log = {}
db_message_id = None

# Database Data (Bot ကနေ အချိန်မရွေး ပြင်/ထည့်နိုင်သည်)
db_data = {
    "price_1": "1,000 Ks",
    "movies": [],
    "packages": {
        "10": {"price": "5,000 Ks", "link": ""},
        "20": {"price": "6,000 Ks", "link": ""},
        "30": {"price": "8,000 Ks", "link": ""}
    }
}

# ----------------------------------------------------
# ၁။ Web Server နှင့် ၂၄ နာရီ Auto-Ping
# ----------------------------------------------------
@app.route('/')
def home():
    return "Translate Movies VIP Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive_ping():
    while True:
        time.sleep(600)
        url = os.environ.get("RENDER_EXTERNAL_URL")
        if url:
            try:
                urllib.request.urlopen(url, timeout=10)
            except Exception as e:
                print(f"Ping error: {e}")

# ----------------------------------------------------
# ၂။ Telegram Private Channel Database စနစ်
# ----------------------------------------------------
def load_db():
    global db_data, db_message_id
    if not DB_CHANNEL_ID:
        return
    try:
        chat = bot.get_chat(DB_CHANNEL_ID)
        if chat.pinned_message and chat.pinned_message.text:
            db_message_id = chat.pinned_message.message_id
            loaded = json.loads(chat.pinned_message.text)
            if isinstance(loaded, dict):
                if "price_1" in loaded:
                    db_data["price_1"] = loaded["price_1"]
                if "movies" in loaded:
                    db_data["movies"] = loaded["movies"]
                if "packages" in loaded and isinstance(loaded["packages"], dict):
                    db_data["packages"] = loaded["packages"]
            print(f"DB ဖတ်ပြီး: 1 Movie ({len(db_data['movies'])} ကား)")
    except Exception as e:
        print(f"DB Load error: {e}")

def save_db():
    global db_message_id
    if not DB_CHANNEL_ID:
        return False
    json_text = json.dumps(db_data, ensure_ascii=False)
    try:
        if db_message_id:
            bot.edit_message_text(json_text, chat_id=DB_CHANNEL_ID, message_id=db_message_id)
        else:
            msg = bot.send_message(DB_CHANNEL_ID, json_text)
            bot.pin_chat_message(DB_CHANNEL_ID, msg.message_id, disable_notification=True)
            db_message_id = msg.message_id
        return True
    except Exception as e:
        print(f"DB Save error: {e}")
        try:
            msg = bot.send_message(DB_CHANNEL_ID, json_text)
            bot.pin_chat_message(DB_CHANNEL_ID, msg.message_id, disable_notification=True)
            db_message_id = msg.message_id
            return True
        except Exception as e2:
            print(f"DB Fallback Save error: {e2}")
            return False

# ----------------------------------------------------
# ၃။ Customer Menu နှင့် Buttons
# ----------------------------------------------------
def get_user_display(user):
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    safe_name = html.escape(full_name) if full_name else "Customer"
    if user.username:
        return f"{safe_name} (@{html.escape(user.username)})"
    return safe_name

def get_sorted_pkg_keys():
    return sorted(db_data["packages"].keys(), key=lambda x: int(x) if x.isdigit() else 9999)

def get_main_buttons():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"🎥 1 Movie – {db_data['price_1']} (ဇာတ်ကားရွေးရန်)", callback_data="menu_1movie"))
    for k in get_sorted_pkg_keys():
        price = db_data["packages"][k].get("price", "")
        markup.add(InlineKeyboardButton(f"🎥 {k} Movies – {price}", callback_data=f"pkg_{k}"))
    return markup

def get_admin_action_buttons(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Approve လုပ်ပြီး", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("⚠️ Slip ပြန်ပို့ခိုင်းရန်", callback_data=f"reject_{user_id}")
    )
    return markup

def build_price_list_message(user):
    display_name = get_user_display(user)
    pkg_lines = [f"🎥 1 Movie – <b>{html.escape(db_data['price_1'])}</b>"]
    for k in get_sorted_pkg_keys():
        p = db_data["packages"][k].get("price", "")
        pkg_lines.append(f"🎥 {k} Movies – <b>{html.escape(p)}</b>")
    price_block = "\n".join(pkg_lines)

    return (
        f"မင်္ဂလာပါ <b>{display_name}</b> ခင်ဗျာ 🙏\n\n"
        f"🎬 <b>VIP MEMBER PRICE LIST</b> 🎬\n\n"
        f"📌 <b>VIP ဇာတ်ကားဈေးနှုန်းများ</b>\n"
        f"{price_block}\n\n"
        f"📍 <b>မှတ်ချက်</b>\n"
        f"အထူးဇာတ်ကားအချို့သည် <b>2,000 Ks</b> ကျသင့်နိုင်ပါသည်။\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"🎁 <b>OLD MEMBER SPECIAL DISCOUNT</b>\n"
        f"မန်ဘာအဟောင်းများအတွက် အထူးလျှော့ဈေးအစီအစဉ် ရှိပါသည်။ ❤️\n"
        f"✨ <b>10 Movies, 20 Movies နှင့် နောက်ပိုင်း Package များအားလုံး</b> ဝယ်ယူပါက <b>50% Discount</b> ရရှိပါမည်။\n\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"💳 <b>KPay ငွေလွှဲရန်</b>\n"
        f"📱 KPay Number – <code>{KPAY_NUMBER}</code>\n"
        f"👤 Account Name – <b>{KPAY_NAME}</b>\n\n"
        f"⚠️ <b>အရေးကြီးအသိပေးချက်</b>\n"
        f"ငွေလွှဲပြီးပါက <b>ငွေလွှဲပြေစာ (Payment Slip)</b> ကို မဖြစ်မနေ ပေးပို့ပေးရန် လိုအပ်ပါသည်။\n\n"
        f"📩 <b>ဆက်သွယ်ရန်</b>\n"
        f"• {CONTACT_1}\n"
        f"• {CONTACT_2}\n"
        f"• {BOT_LINK}"
    )

# ----------------------------------------------------
# ၄။ Admin Commands
# ----------------------------------------------------
@bot.message_handler(commands=['admin'])
def set_admin(message):
    global ADMIN_ID
    ADMIN_ID = str(message.chat.id)
    db_status = "✅ ချိတ်ဆက်ပြီး" if DB_CHANNEL_ID else "⚠️ DB_CHANNEL_ID မထည့်ရသေးပါ"
    bot.reply_to(
        message,
        f"✅ <b>Admin အဖြစ် သတ်မှတ်ပြီးပါပြီ!</b>\n"
        f"🆔 Admin ID: <code>{ADMIN_ID}</code>\n"
        f"🗄 Database: {db_status}\n\n"
        f"⚙️ <b>Admin Command များ -</b>\n"
        f"1️⃣ <b>ဈေးနှုန်းပြင်/အသစ်ထည့်ရန်:</b>\n"
        f"   <code>/setprice 1 1,000 Ks</code>\n"
        f"   <code>/setprice 10 5,000 Ks</code>\n"
        f"   <code>/setprice 40 10,000 Ks</code> (Package အသစ်ပါ တန်းတိုးနိုင်သည်)\n\n"
        f"2️⃣ <b>Package Link ထည့်/ပြင်ရန်:</b>\n"
        f"   <code>/setlink 10 https://t.me/+xxxxx</code>\n\n"
        f"3️⃣ <b>1 Movie (ပုံ + ဈေး + Link) ထည့်ရန်:</b>\n"
        f"   ပုံပို့ပြီး Caption မှာ <code>/add ဇာတ်ကားနာမည် | 1,000 Ks | https://t.me/...</code>\n"
        f"   <i>(Link မပါဘဲ <code>/add နာမည် | 1,000 Ks</code> လည်း ရသည်)</i>\n\n"
        f"4️⃣ <b>စစ်ဆေး/ဖျက်ရန်:</b>\n"
        f"   • /settings - လက်ရှိဈေးနှင့် Link အားလုံး ကြည့်ရန်\n"
        f"   • /movies - 1 Movie စာရင်းကြည့်ရန်\n"
        f"   • /del 1 - 1 Movie နံပါတ် (၁) ဖျက်ရန်\n"
        f"   • /delpkg 30 - 30 Movies Package ဖျက်ရန်\n"
        f"   • /today - ယနေ့ ဝင်ရောက်လာသူများ ကြည့်ရန်",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['setprice'])
def set_price(message):
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ ဥပမာ - <code>/setprice 10 5,000 Ks</code> (သို့) <code>/setprice 1 1,000 Ks</code>", parse_mode="HTML")
        return
    pkg_key = parts[1]
    new_price = parts[2].strip()
    if pkg_key == "1":
        db_data["price_1"] = new_price
    else:
        if pkg_key not in db_data["packages"]:
            db_data["packages"][pkg_key] = {"price": new_price, "link": ""}
        else:
            db_data["packages"][pkg_key]["price"] = new_price
    saved = save_db()
    status = "✅ Database ထဲ သိမ်းပြီးပါပြီ!" if saved else "⚠️ ယာယီသိမ်းထားပါသည် (DB_CHANNEL_ID စစ်ပါ)"
    bot.reply_to(message, f"💰 <b>{pkg_key} Movie(s) ဈေးနှုန်း</b> ကို <b>{html.escape(new_price)}</b> သို့ ပြောင်းလဲပြီးပါပြီ!\n{status}", parse_mode="HTML")

@bot.message_handler(commands=['setlink'])
def set_package_link(message):
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit() or parts[1] == "1":
        bot.reply_to(message, "⚠️ ဥပမာ - <code>/setlink 10 https://t.me/+xxxxx</code>", parse_mode="HTML")
        return
    pkg_key = parts[1]
    new_link = parts[2].strip()
    if pkg_key not in db_data["packages"]:
        db_data["packages"][pkg_key] = {"price": "မသတ်မှတ်ရသေးပါ", "link": new_link}
    else:
        db_data["packages"][pkg_key]["link"] = new_link
    saved = save_db()
    status = "✅ Database ထဲ သိမ်းပြီးပါပြီ!" if saved else "⚠️ ယာယီသိမ်းထားပါသည် (DB_CHANNEL_ID စစ်ပါ)"
    bot.reply_to(message, f"🔗 <b>{pkg_key} Movies Link</b> ကို ထည့်သွင်းပြီးပါပြီ!\n{new_link}\n{status}", parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['delpkg'])
def delete_package(message):
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        return
    parts = message.text.split()
    if len(parts) < 2 or parts[1] not in db_data["packages"]:
        bot.reply_to(message, "⚠️ ဥပမာ - <code>/delpkg 30</code> (ရှိပြီးသား Package နံပါတ် ရိုက်ပါ)", parse_mode="HTML")
        return
    pkg_key = parts[1]
    del db_data["packages"][pkg_key]
    save_db()
    bot.reply_to(message, f"🗑 <b>{pkg_key} Movies Package</b> ကို ဖျက်ပြီးပါပြီ။", parse_mode="HTML")

@bot.message_handler(commands=['settings', 'links'])
def show_settings(message):
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        return
    lines = [f"• <b>1 Movie:</b> {db_data['price_1']} ({len(db_data['movies'])} ကား)"]
    for k in get_sorted_pkg_keys():
        p = db_data["packages"][k].get("price", "")
        l = db_data["packages"][k].get("link") or "Link မထည့်ရသေးပါ"
        lines.append(f"• <b>{k} Movies:</b> {p}\n  🔗 {l}")
    bot.reply_to(message, "⚙️ <b>လက်ရှိ ဈေးနှုန်းနှင့် Link များ -</b>\n\n" + "\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['today'])
def show_today_members(message):
    if not ADMIN_ID or str(message.chat.id) == str(ADMIN_ID):
        today_str = str(date.today())
        members = daily_members_log.get(today_str, set())
        if not members:
            bot.reply_to(message, f"📅 ယနေ့ ({today_str}) Bot ထဲသို့ ဝင်ရောက်လာသူ မရှိသေးပါ။")
        else:
            member_list = "\n".join([f"• {name}" for name in members])
            bot.reply_to(message, f"📅 <b>ယနေ့ ({today_str}) ဝင်ရောက်လာသူများ ({len(members)} ဦး):</b>\n\n{member_list}", parse_mode="HTML")

@bot.message_handler(commands=['movies'])
def list_movies_admin(message):
    if not ADMIN_ID or str(message.chat.id) == str(ADMIN_ID):
        movies = db_data["movies"]
        if not movies:
            bot.reply_to(message, "🎬 1 Movie စာရင်း မရှိသေးပါ။", parse_mode="HTML")
            return
        lines = []
        for i, m in enumerate(movies):
            link_tag = " 🔗" if m.get("l") else ""
            lines.append(f"{i+1}. {m['t']} ({m['p']}){link_tag}")
        bot.reply_to(message, "🎬 <b>လက်ရှိ 1 Movie စာရင်းများ -</b>\n\n" + "\n".join(lines) + "\n\n🗑 ဖျက်လိုပါက <code>/del နံပါတ်</code> ရိုက်ပါ။", parse_mode="HTML")

@bot.message_handler(commands=['del'])
def delete_movie(message):
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ ဥပမာ - <code>/del 1</code>", parse_mode="HTML")
        return
    idx = int(parts[1]) - 1
    movies = db_data["movies"]
    if 0 <= idx < len(movies):
        removed = movies.pop(idx)
        save_db()
        bot.reply_to(message, f"🗑 <b>{html.escape(removed['t'])}</b> ကို ဖျက်ပြီးပါပြီ။", parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ အဲဒီနံပါတ် မရှိပါ။ /movies နဲ့ ပြန်စစ်ပါ။")

# ----------------------------------------------------
# ၅။ Callback ခလုတ်များ
# ----------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data

    if data == "menu_1movie":
        bot.answer_callback_query(call.id)
        movies = db_data["movies"]
        if not movies:
            bot.send_message(call.message.chat.id, "🎬 လက်ရှိ 1 Movie စာရင်း အသစ်တင်နေဆဲဖြစ်ပါသည်။ Admin ဆီ တိုက်ရိုက်မေးမြန်းနိုင်ပါသည်ဗျ။")
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for i, m in enumerate(movies):
            markup.add(InlineKeyboardButton(f"🎬 {m['t']} – {m['p']}", callback_data=f"mov_{i}"))
        bot.send_message(call.message.chat.id, "🎬 <b>ကြည့်ရှုလိုသော ဇာတ်ကားကို ရွေးချယ်ပါ -</b>", parse_mode="HTML", reply_markup=markup)
        return

    if data.startswith("mov_"):
        idx = int(data.split("_")[1])
        bot.answer_callback_query(call.id)
        movies = db_data["movies"]
        if 0 <= idx < len(movies):
            m = movies[idx]
            movie_link = m.get("l", "").strip()
            link_text = f"\n🔗 <b>ဇာတ်ကား Link:</b> {movie_link}\n" if movie_link else "\n"
            markup = InlineKeyboardMarkup()
            if movie_link.startswith("http"):
                markup.add(InlineKeyboardButton("🔗 ဇာတ်ကား Channel / Link ဝင်ရန်", url=movie_link))

            caption = (
                f"🎬 <b>{html.escape(m['t'])}</b>\n"
                f"💰 <b>ဈေးနှုန်း:</b> {html.escape(m['p'])}"
                f"{link_text}\n"
                f"💳 <b>KPay ငွေလွှဲရန် -</b>\n"
                f"📱 KPay: <code>{KPAY_NUMBER}</code>\n"
                f"👤 Name: <b>{KPAY_NAME}</b>\n\n"
                f"⚠️ ငွေလွှဲပြီးပါက <b>Payment Slip (SS)</b> ကို ဒီ Bot ဆီ ပို့ပေးပါဗျ။"
            )
            bot.send_photo(
                call.message.chat.id,
                m['f'],
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup if movie_link.startswith("http") else None
            )
        return

    if data.startswith("pkg_"):
        pkg_key = data.split("_", 1)[1]
        bot.answer_callback_query(call.id)
        if pkg_key not in db_data["packages"]:
            return
        pkg = db_data["packages"][pkg_key]
        price = pkg.get("price", "")
        link = pkg.get("link", "").strip()

        if not link:
            bot.send_message(
                call.message.chat.id,
                f"🎬 <b>{pkg_key} Movies Package</b>\n"
                f"💰 <b>ကျသင့်ငွေ:</b> {html.escape(price)} (Old Member 50% Discount)\n\n"
                f"⏳ <b>{pkg_key} Movies Link</b> ကို မကြာမီ ထပ်မံထည့်သွင်းပေးပါမည်။\n"
                f"📩 အသေးစိတ်မေးမြန်းလိုပါက {CONTACT_1} (သို့) {CONTACT_2} သို့ ဆက်သွယ်နိုင်ပါသည်ဗျ။",
                parse_mode="HTML"
            )
            return

        markup = InlineKeyboardMarkup()
        if link.startswith("http"):
            markup.add(InlineKeyboardButton(f"🔗 {pkg_key} Movies Channel Join Request ရန်", url=link))
        bot.send_message(
            call.message.chat.id,
            f"🎬 <b>Package:</b> {pkg_key} Movies\n"
            f"💰 <b>ကျသင့်ငွေ:</b> {html.escape(price)} (Old Member 50% Discount)\n\n"
            f"💳 <b>KPay ငွေလွှဲရန် -</b>\n"
            f"📱 KPay Number – <code>{KPAY_NUMBER}</code>\n"
            f"👤 Account Name – <b>{KPAY_NAME}</b>\n\n"
            f"📢 <b>Channel Join Request ပို့ထားရန် Link -</b>\n"
            f"🔗 {link}\n\n"
            f"⚠️ ငွေလွှဲပြီးပါက <b>Payment Slip (SS)</b> ကို ဒီ Bot ဆီ ပို့ပေးပါဗျ။",
            parse_mode="HTML",
            reply_markup=markup if link.startswith("http") else None,
            disable_web_page_preview=True
        )
        return

    if ADMIN_ID and str(call.message.chat.id) != str(ADMIN_ID):
        return

    if data.startswith("approve_"):
        target_id = int(data.split("_")[1])
        try:
            bot.send_message(
                target_id,
                "🎉 <b>ဂုဏ်ယူပါတယ်ခင်ဗျာ!</b>\n\n"
                "✅ လူကြီးမင်း၏ Payment Slip ကို Admin မှ စစ်ဆေးအတည်ပြုပြီးပါပြီ။\n"
                "📢 မိမိရွေးချယ်ထားသော Package / ဇာတ်ကား Link တွင် Join Request နှိပ်ထားပေးပါဗျ 🙏",
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "✅ Approve စာပို့ပြီးပါပြီ!")
            bot.edit_message_text(call.message.text + "\n\n✅ [Admin မှ Approve စာပို့ပြီးပါပြီ]", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"ပို့မရပါ: {e}", show_alert=True)

    elif data.startswith("reject_"):
        target_id = int(data.split("_")[1])
        try:
            bot.send_message(
                target_id,
                "⚠️ <b>Admin မှ အကြောင်းကြားစာ</b>\n\nလူကြီးမင်း ပေးပို့ထားသော Payment Slip ပုံမရှင်းလင်းပါသဖြင့် <b>ငွေလွှဲပြေစာ (Payment Slip)</b> ကို ပြန်လည်ပေးပို့ပေးပါခင်ဗျာ 🙏",
                parse_mode="HTML"
            )
            bot.answer_callback_query(call.id, "⚠️ ပြေစာပြန်ပို့ခိုင်းသည့်စာ ပို့ပြီးပါပြီ!")
            bot.edit_message_text(call.message.text + "\n\n⚠️ [Slip ပြန်ပို့ရန် အကြောင်းကြားပြီးပါပြီ]", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"ပို့မရပါ: {e}", show_alert=True)

# ----------------------------------------------------
# ၆။ /start နှင့် /help
# ----------------------------------------------------
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = message.from_user
    display_name = get_user_display(user)
    today_str = str(date.today())
    daily_members_log.setdefault(today_str, set()).add(display_name)

    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        bot.send_message(ADMIN_ID, f"🔔 <b>Customer အသစ် Bot ကို စတင်နှိပ်လိုက်ပါသည်</b>\n👤 အမည်: {display_name}\n🆔 User ID: <code>{user.id}</code>", parse_mode="HTML")

    bot.reply_to(message, build_price_list_message(user), parse_mode="HTML", reply_markup=get_main_buttons(), disable_web_page_preview=True)

# ----------------------------------------------------
# ၇။ Photo / Document (Admin /add + Customer Slip)
# ----------------------------------------------------
@bot.message_handler(content_types=['photo', 'document'])
def handle_media(message):
    user = message.from_user
    display_name = get_user_display(user)
    raw_caption = message.caption or ""

    if ADMIN_ID and str(message.chat.id) == str(ADMIN_ID) and raw_caption.startswith("/add"):
        if not message.photo:
            bot.reply_to(message, "⚠️ ဇာတ်ကားထည့်ရန် <b>Photo (ဓာတ်ပုံ)</b> အဖြစ် ပို့ပေးပါ။", parse_mode="HTML")
            return
        content = raw_caption[4:].strip()
        parts = [x.strip() for x in content.split("|")]
        title = parts[0] if len(parts) >= 1 else ""
        price = parts[1] if len(parts) >= 2 and parts[1] else db_data["price_1"]
        link = parts[2] if len(parts) >= 3 else ""

        if not title:
            bot.reply_to(message, "⚠️ ဥပမာ - <code>/add ဇာတ်ကားနာမည် | 1,000 Ks | https://t.me/...</code>", parse_mode="HTML")
            return

        file_id = message.photo[-1].file_id
        db_data["movies"].append({"t": title, "p": price, "f": file_id, "l": link})
        saved = save_db()
        status = "✅ Database ထဲ သိမ်းပြီးပါပြီ!" if saved else "⚠️ ယာယီသိမ်းထားပါသည် (DB_CHANNEL_ID စစ်ပေးပါ)"
        link_info = f"\n🔗 Link: {link}" if link else ""
        bot.reply_to(message, f"🎬 <b>{html.escape(title)}</b> ({html.escape(price)}){link_info}\nထည့်သွင်းပြီးပါပြီ!\n{status}", parse_mode="HTML", disable_web_page_preview=True)
        return

    caption = html.escape(raw_caption) if raw_caption else "မှတ်ချက်စာသား မပါပါ"
    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        info_text = (
            f"🧾 <b>Payment Slip အသစ်ရောက်ရှိလာပါသည်!</b>\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: <code>{user.id}</code>\n"
            f"📝 မှတ်ချက်: {caption}\n\n"
            f"💡 <i>(ဤစာကို Reply ထောက်ပြီး Customer ဆီ စာပြန်နိုင်ပါသည်)</i>"
        )
        bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        bot.send_message(ADMIN_ID, info_text, parse_mode="HTML", reply_markup=get_admin_action_buttons(user.id))

    bot.reply_to(
        message,
        f"ကျေးဇူးတင်ပါတယ် <b>{display_name}</b> ခင်ဗျာ 🙏\n\n"
        f"✅ လူကြီးမင်း ပေးပို့သော <b>ငွေလွှဲပြေစာ (Payment Slip)</b> ကို Admin ထံ ပေးပို့ထားပြီး ဖြစ်ပါသည်။\n"
        f"စစ်ဆေးပြီး မကြာမီ အကြောင်းပြန်ပေးပါမည်ဗျ။",
        parse_mode="HTML",
        reply_markup=get_main_buttons(),
        disable_web_page_preview=True
    )

# ----------------------------------------------------
# ၈။ Customer စာပို့ခြင်းနှင့် Admin Reply
# ----------------------------------------------------
def extract_target_user_id(reply_msg):
    if reply_msg.forward_from:
        return reply_msg.forward_from.id
    text_to_search = reply_msg.text or reply_msg.caption or ""
    match = re.search(r"User ID:\s*(\d+)", text_to_search)
    return int(match.group(1)) if match else None

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = message.from_user
    display_name = get_user_display(user)

    if ADMIN_ID and str(message.chat.id) == str(ADMIN_ID):
        if message.reply_to_message:
            target_id = extract_target_user_id(message.reply_to_message)
            if target_id:
                try:
                    bot.send_message(target_id, f"📩 <b>Admin မှ အကြောင်းကြားစာ -</b>\n\n{html.escape(message.text)}", parse_mode="HTML")
                    bot.reply_to(message, "✅ Customer ဆီသို့ စာပို့ပြီးပါပြီ။")
                    return
                except Exception as e:
                    bot.reply_to(message, f"❌ ပို့မရပါ: {e}")
                    return

    if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
        info_text = (
            f"💬 <b>Customer ဆီမှ စာအသစ် ရောက်ရှိလာပါသည်</b>\n"
            f"👤 ပေးပို့သူ: {display_name}\n"
            f"🆔 User ID: <code>{user.id}</code>\n"
            f"✉️ စာသား: {html.escape(message.text)}"
        )
        bot.send_message(ADMIN_ID, info_text, parse_mode="HTML")

    bot.reply_to(message, build_price_list_message(user), parse_mode="HTML", reply_markup=get_main_buttons(), disable_web_page_preview=True)

# ----------------------------------------------------
# ၉။ Bot စတင်ခြင်း
# ----------------------------------------------------
def start_bot_polling():
    load_db()
    while True:
        try:
            bot.remove_webhook()
            time.sleep(2)
            bot.polling(non_stop=True, interval=1, timeout=20)
        except Exception as e:
            print(f"Polling error (restarting in 5s): {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    print("Translate Movies VIP Bot စတင်အလုပ်လုပ်နေပါပြီ...")
    start_bot_polling()
