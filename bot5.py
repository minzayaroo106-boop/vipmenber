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

BOT_TOKEN_1 = os.environ.get("BOT_TOKEN")      # Bot 1 Token (@TranslateMovies2vip_bot)
BOT_TOKEN_2 = os.environ.get("BOT_TOKEN_2")    # Bot 2 Token (@Oursource2_bot)
ADMIN_ID = os.environ.get("ADMIN_ID")
DB_CHANNEL_ID = os.environ.get("DB_CHANNEL_ID")  # Private Database Channel ID (-100xxxxxxxxxx)

app = Flask(__name__)

# ====================================================
# အခြေခံ အချက်အလက်များ
# ====================================================
KPAY_NUMBER = "09764199664"
KPAY_NAME = "Min Zayar Oo"
CONTACT_1 = "@moon_translate25"
CONTACT_2 = "@beststoryken"

daily_members_log = {}
db_message_id = None
db_bot = None  # Database သိမ်းရန် အသုံးပြုမည့် Bot

# Database Data (Package တစ်ခုချင်းစီမှာ Link အများကြီး သိမ်းနိုင်သည်)
db_data = {
    "packages": {
        "1": {"label": "1 Movie", "price": "1,000 Ks", "links": [], "discount": False},
        "10": {"label": "10 Movies", "price": "5,000 Ks", "links": [], "discount": True},
        "20": {"label": "20 Movies", "price": "6,000 Ks", "links": [], "discount": True},
        "30": {"label": "30 Movies", "price": "8,000 Ks", "links": [], "discount": True}
    }
}

# ----------------------------------------------------
# ၁။ Web Server နှင့် ၂၄ နာရီ Auto-Ping
# ----------------------------------------------------
@app.route('/')
def home():
    return "Translate Movies Dual VIP Bots are running 24/7!"

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
def normalize_packages(pkgs):
    for k, v in pkgs.items():
        if "links" not in v:
            old_link = v.pop("link", "").strip()
            v["links"] = [{"name": "", "url": old_link}] if old_link else []
        else:
            fixed = []
            for item in v["links"]:
                if isinstance(item, str) and item.strip():
                    fixed.append({"name": "", "url": item.strip()})
                elif isinstance(item, dict) and item.get("url"):
                    fixed.append({"name": item.get("name", ""), "url": item["url"].strip()})
            v["links"] = fixed
    return pkgs

def load_db():
    global db_data, db_message_id
    if not DB_CHANNEL_ID or not db_bot:
        return
    try:
        chat = db_bot.get_chat(DB_CHANNEL_ID)
        if chat.pinned_message and chat.pinned_message.text:
            db_message_id = chat.pinned_message.message_id
            loaded = json.loads(chat.pinned_message.text)
            if isinstance(loaded, dict) and "packages" in loaded:
                db_data["packages"] = normalize_packages(loaded["packages"])
                print(f"DB ဖတ်ပြီး: Packages ({len(db_data['packages'])} ခု)")
    except Exception as e:
        print(f"DB Load error: {e}")

def save_db():
    global db_message_id
    if not DB_CHANNEL_ID or not db_bot:
        return False
    json_text = json.dumps(db_data, ensure_ascii=False)
    try:
        if db_message_id:
            db_bot.edit_message_text(json_text, chat_id=DB_CHANNEL_ID, message_id=db_message_id)
        else:
            msg = db_bot.send_message(DB_CHANNEL_ID, json_text)
            db_bot.pin_chat_message(DB_CHANNEL_ID, msg.message_id, disable_notification=True)
            db_message_id = msg.message_id
        return True
    except Exception as e:
        print(f"DB Save error: {e}")
        try:
            msg = db_bot.send_message(DB_CHANNEL_ID, json_text)
            db_bot.pin_chat_message(DB_CHANNEL_ID, msg.message_id, disable_notification=True)
            db_message_id = msg.message_id
            return True
        except Exception as e2:
            print(f"DB Fallback Save error: {e2}")
            return False

# ----------------------------------------------------
# ၃။ Helper Functions
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
    for k in get_sorted_pkg_keys():
        pkg = db_data["packages"][k]
        label = pkg.get("label", f"{k} Movies")
        price = pkg.get("price", "")
        markup.add(InlineKeyboardButton(f"🎥 {label} – {price}", callback_data=f"pkg_{k}"))
    return markup

def get_admin_action_buttons(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✅ Approve စာပို့မည်", callback_data=f"approve_{user_id}"),
        InlineKeyboardButton("⚠️ Slip ပြန်ပို့ခိုင်းမည်", callback_data=f"reject_{user_id}")
    )
    return markup

def build_price_list_message(user, bot_username):
    display_name = get_user_display(user)
    pkg_lines = []
    for k in get_sorted_pkg_keys():
        pkg = db_data["packages"][k]
        label = html.escape(pkg.get("label", f"{k} Movies"))
        price = html.escape(pkg.get("price", ""))
        pkg_lines.append(f"🎥 {label} – <b>{price}</b>")
    price_block = "\n".join(pkg_lines)
    bot_link = f"https://t.me/{bot_username}" if bot_username else ""

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
        f"• {bot_link}"
    )

def extract_target_user_id(reply_msg):
    if reply_msg.forward_from:
        return reply_msg.forward_from.id
    text_to_search = reply_msg.text or reply_msg.caption or ""
    match = re.search(r"User ID:\s*(\d+)", text_to_search)
    return int(match.group(1)) if match else None

# ----------------------------------------------------
# ၄။ Bot တစ်ခုချင်းစီအတွက် Handler များ ချိတ်ဆက်ခြင်း
# ----------------------------------------------------
def register_handlers(bot, bot_username):

    @bot.chat_join_request_handler()
    def handle_join_request(req):
        user = req.from_user
        chat = req.chat
        display_name = get_user_display(user)
        channel_title = html.escape(chat.title or "VIP Channel")

        today_str = str(date.today())
        daily_members_log.setdefault(today_str, set()).add(display_name)

        try:
            bot.send_message(
                user.id,
                f"မင်္ဂလာပါ <b>{display_name}</b> ခင်ဗျာ 🙏\n\n"
                f"📢 <b>{channel_title}</b> သို့ Join Request ပေးပို့ထားတာကို တွေ့ရှိရပါသည်။\n\n"
                f"VIP ဝင်ရောက်ရန် အောက်ပါ KPay သို့ ငွေလွှဲပြီး <b>ငွေလွှဲပြေစာ (Payment Slip)</b> ကို ဒီ Bot ဆီ ပေးပို့ပေးပါဗျ။ Admin မှ စစ်ဆေးပြီး ချက်ချင်း လက်ခံ (Accept) ပေးပါမည်။\n\n"
                f"💳 <b>KPay ငွေလွှဲရန်</b>\n"
                f"📱 KPay Number – <code>{KPAY_NUMBER}</code>\n"
                f"👤 Account Name – <b>{KPAY_NAME}</b>\n\n"
                f"📩 <b>ဆက်သွယ်ရန်:</b> {CONTACT_1} / {CONTACT_2}",
                parse_mode="HTML",
                reply_markup=get_main_buttons()
            )
        except Exception as e:
            print(f"[{bot_username}] Join request DM error: {e}")

        if ADMIN_ID:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Accept (လက်ခံမည်)", callback_data=f"jr_acc_{chat.id}_{user.id}"),
                InlineKeyboardButton("❌ Decline (ငြင်းမည်)", callback_data=f"jr_dec_{chat.id}_{user.id}")
            )
            try:
                bot.send_message(
                    ADMIN_ID,
                    f"🚪 <b>Channel Join Request အသစ်!</b> (@{bot_username})\n\n"
                    f"📢 Channel: <b>{channel_title}</b>\n"
                    f"👤 Customer: {display_name}\n"
                    f"🆔 User ID: <code>{user.id}</code>\n\n"
                    f"💡 <i>(ငွေလွှဲပြေစာ စစ်ပြီးမှ Accept / Decline နှိပ်ပါ)</i>",
                    parse_mode="HTML",
                    reply_markup=markup
                )
            except Exception as e:
                print(f"[{bot_username}] Admin notify error: {e}")

    @bot.message_handler(commands=['admin'])
    def set_admin(message):
        global ADMIN_ID
        ADMIN_ID = str(message.chat.id)
        db_status = "✅ ချိတ်ဆက်ပြီး" if DB_CHANNEL_ID else "⚠️ DB_CHANNEL_ID မထည့်ရသေးပါ"
        bot.reply_to(
            message,
            f"✅ <b>Admin အဖြစ် သတ်မှတ်ပြီးပါပြီ!</b> (@{bot_username})\n"
            f"🆔 Admin ID: <code>{ADMIN_ID}</code>\n"
            f"🗄 Database: {db_status}\n\n"
            f"⚙️ <b>Admin Command များ -</b>\n"
            f"1️⃣ <b>Channel Link ထပ်တိုးရန် (၂ ခု၊ ၃ ခု ထည့်နိုင်သည်):</b>\n"
            f"   <code>/addlink 1 https://t.me/+xxxxx</code>\n"
            f"   <code>/addlink 10 Channel 1 | https://t.me/+xxxxx</code>\n"
            f"   <code>/addlink 10 Channel 2 | https://t.me/+yyyyy</code>\n\n"
            f"2️⃣ <b>Link ဖျက်ရန်:</b>\n"
            f"   <code>/dellink 10 1</code> (10 Movies ရဲ့ Link နံပါတ် ၁ ကို ဖျက်ရန်)\n\n"
            f"3️⃣ <b>ဈေးနှုန်းပြင် / Package အသစ်တိုးရန်:</b>\n"
            f"   <code>/setprice 1 1,000 Ks</code>\n"
            f"   <code>/setprice 40 10,000 Ks</code>\n\n"
            f"4️⃣ <b>စစ်ဆေး/ဖျက်ရန်:</b>\n"
            f"   • /settings - လက်ရှိဈေးနှင့် Link အားလုံး ကြည့်ရန်\n"
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
            bot.reply_to(message, "⚠️ ဥပမာ - <code>/setprice 10 5,000 Ks</code>", parse_mode="HTML")
            return
        pkg_key = parts[1]
        new_price = parts[2].strip()
        if pkg_key not in db_data["packages"]:
            label = "1 Movie" if pkg_key == "1" else f"{pkg_key} Movies"
            db_data["packages"][pkg_key] = {
                "label": label,
                "price": new_price,
                "links": [],
                "discount": (pkg_key != "1")
            }
        else:
            db_data["packages"][pkg_key]["price"] = new_price
        saved = save_db()
        status = "✅ Database ထဲ သိမ်းပြီးပါပြီ!" if saved else "⚠️ ယာယီသိမ်းထားပါသည် (DB_CHANNEL_ID စစ်ပါ)"
        bot.reply_to(message, f"💰 <b>{pkg_key} Movie(s) ဈေးနှုန်း</b> ကို <b>{html.escape(new_price)}</b> သို့ ပြောင်းလဲပြီးပါပြီ!\n{status}", parse_mode="HTML")

    @bot.message_handler(commands=['addlink', 'setlink'])
    def add_package_link(message):
        if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
            return
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            bot.reply_to(
                message,
                "⚠️ ဥပမာ -\n<code>/addlink 10 https://t.me/+xxxxx</code>\nသို့မဟုတ် နာမည်ပါ ထည့်လိုပါက -\n<code>/addlink 10 Channel 1 | https://t.me/+xxxxx</code>",
                parse_mode="HTML"
            )
            return
        pkg_key = parts[1]
        rest = parts[2].strip()
        if "|" in rest:
            name_part, url_part = rest.split("|", 1)
            link_name = name_part.strip()
            link_url = url_part.strip()
        else:
            link_name = ""
            link_url = rest

        if pkg_key not in db_data["packages"]:
            label = "1 Movie" if pkg_key == "1" else f"{pkg_key} Movies"
            db_data["packages"][pkg_key] = {
                "label": label,
                "price": "မသတ်မှတ်ရသေးပါ",
                "links": [],
                "discount": (pkg_key != "1")
            }
        db_data["packages"][pkg_key]["links"].append({"name": link_name, "url": link_url})
        saved = save_db()
        status = "✅ Database ထဲ သိမ်းပြီးပါပြီ!" if saved else "⚠️ ယာယီသိမ်းထားပါသည် (DB_CHANNEL_ID စစ်ပါ)"
        label = db_data["packages"][pkg_key]["label"]
        count = len(db_data["packages"][pkg_key]["links"])
        bot.reply_to(
            message,
            f"🔗 <b>{label}</b> ထဲသို့ Link နံပါတ် ({count}) ထည့်သွင်းပြီးပါပြီ!\n"
            f"{html.escape(link_name) + ' - ' if link_name else ''}{link_url}\n{status}",
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    @bot.message_handler(commands=['dellink'])
    def delete_package_link(message):
        if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
            return
        parts = message.text.split()
        if len(parts) < 3 or parts[1] not in db_data["packages"] or not parts[2].isdigit():
            bot.reply_to(message, "⚠️ ဥပမာ - <code>/dellink 10 1</code> (10 Movies ရဲ့ Link နံပါတ် ၁ ကို ဖျက်ရန်)", parse_mode="HTML")
            return
        pkg_key = parts[1]
        idx = int(parts[2]) - 1
        links = db_data["packages"][pkg_key].get("links", [])
        if 0 <= idx < len(links):
            removed = links.pop(idx)
            save_db()
            bot.reply_to(message, f"🗑 <b>{db_data['packages'][pkg_key]['label']}</b> မှ Link ({idx+1}) ကို ဖျက်ပြီးပါပြီ။\n({removed['url']})", parse_mode="HTML", disable_web_page_preview=True)
        else:
            bot.reply_to(message, "❌ အဲဒီ Link နံပါတ် မရှိပါ။ /settings နဲ့ ပြန်စစ်ပါ။")

    @bot.message_handler(commands=['delpkg'])
    def delete_package(message):
        if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
            return
        parts = message.text.split()
        if len(parts) < 2 or parts[1] not in db_data["packages"]:
            bot.reply_to(message, "⚠️ ဥပမာ - <code>/delpkg 30</code>", parse_mode="HTML")
            return
        pkg_key = parts[1]
        label = db_data["packages"][pkg_key].get("label", f"{pkg_key} Movies")
        del db_data["packages"][pkg_key]
        save_db()
        bot.reply_to(message, f"🗑 <b>{label}</b> ကို ဖျက်ပြီးပါပြီ။", parse_mode="HTML")

    @bot.message_handler(commands=['settings', 'links'])
    def show_settings(message):
        if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
            return
        lines = []
        for k in get_sorted_pkg_keys():
            pkg = db_data["packages"][k]
            label = pkg.get("label", f"{k} Movies")
            p = pkg.get("price", "")
            links = pkg.get("links", [])
            if not links:
                lines.append(f"• <b>{label}:</b> {p}\n  🔗 Link မထည့်ရသေးပါ")
            else:
                link_strs = []
                for i, item in enumerate(links, 1):
                    nm = f" ({html.escape(item['name'])})" if item.get("name") else ""
                    link_strs.append(f"  {i}. 🔗{nm} {item['url']}")
                lines.append(f"• <b>{label}:</b> {p}\n" + "\n".join(link_strs))
        bot.reply_to(message, "⚙️ <b>လက်ရှိ ဈေးနှုန်းနှင့် Link များ -</b>\n\n" + "\n\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)

    @bot.message_handler(commands=['today'])
    def show_today_members(message):
        if not ADMIN_ID or str(message.chat.id) == str(ADMIN_ID):
            today_str = str(date.today())
            members = daily_members_log.get(today_str, set())
            if not members:
                bot.reply_to(message, f"📅 ယနေ့ ({today_str}) ဝင်ရောက်လာသူ မရှိသေးပါ။")
            else:
                member_list = "\n".join([f"• {name}" for name in members])
                bot.reply_to(message, f"📅 <b>ယနေ့ ({today_str}) ဝင်ရောက်လာသူများ ({len(members)} ဦး):</b>\n\n{member_list}", parse_mode="HTML")

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        data = call.data

        if data.startswith("pkg_"):
            pkg_key = data.split("_", 1)[1]
            bot.answer_callback_query(call.id)
            if pkg_key not in db_data["packages"]:
                return
            pkg = db_data["packages"][pkg_key]
            label = pkg.get("label", f"{pkg_key} Movies")
            price = pkg.get("price", "")
            links = pkg.get("links", [])
            has_discount = pkg.get("discount", pkg_key != "1")

            if not links:
                bot.send_message(
                    call.message.chat.id,
                    f"🎬 <b>{html.escape(label)}</b>\n"
                    f"💰 <b>ကျသင့်ငွေ:</b> {html.escape(price)}\n\n"
                    f"⏳ <b>{html.escape(label)} Channel Link</b> ကို မကြာမီ ထပ်မံထည့်သွင်းပေးပါမည်။\n"
                    f"📩 အသေးစိတ်မေးမြန်းလိုပါက {CONTACT_1} (သို့) {CONTACT_2} သို့ ဆက်သွယ်နိုင်ပါသည်ဗျ။",
                    parse_mode="HTML"
                )
                return

            markup = InlineKeyboardMarkup(row_width=1)
            link_lines = []
            for i, item in enumerate(links, 1):
                url = item["url"]
                nm = item.get("name") or (f"Channel {i}" if len(links) > 1 else label)
                link_lines.append(f"🔗 <b>{html.escape(nm)}:</b> {url}")
                if url.startswith("http"):
                    btn_text = f"🎬 {nm} ဝင်ကြည့်ရန်" if pkg_key == "1" else f"🔗 {nm} Join Request ရန်"
                    markup.add(InlineKeyboardButton(btn_text, url=url))

            links_block = "\n".join(link_lines)

            if pkg_key == "1":
                msg_text = (
                    f"🎬 <b>1 Movie ဇာတ်ကားစာရင်း (Catalog Channels)</b>\n"
                    f"💰 <b>ဈေးနှုန်း:</b> {html.escape(price)} (အထူးကား 2,000 Ks)\n\n"
                    f"📌 <b>ကြည့်ရှုပုံအဆင့်ဆင့် -</b>\n"
                    f"1️⃣ အောက်ပါ Link မှတစ်ဆင့် ဇာတ်ကားစာရင်း Channel ထဲ ဝင်ကြည့်ပါ။\n"
                    f"2️⃣ မိမိကြည့်လိုသော ဇာတ်ကား Link ကို နှိပ်ပြီး <b>Join Request</b> ပို့ထားပါ။\n"
                    f"3️⃣ KPay ငွေလွှဲပြီး <b>Payment Slip (SS)</b> ကို ဒီ Bot ဆီ ပို့ပေးပါဗျ။\n\n"
                    f"{links_block}\n\n"
                    f"💳 <b>KPay ငွေလွှဲရန် -</b>\n"
                    f"📱 KPay Number – <code>{KPAY_NUMBER}</code>\n"
                    f"👤 Account Name – <b>{KPAY_NAME}</b>"
                )
            else:
                discount_note = " (Old Member 50% Discount)" if has_discount else ""
                msg_text = (
                    f"🎬 <b>Package:</b> {html.escape(label)}\n"
                    f"💰 <b>ကျသင့်ငွေ:</b> {html.escape(price)}{discount_note}\n\n"
                    f"💳 <b>KPay ငွေလွှဲရန် -</b>\n"
                    f"📱 KPay Number – <code>{KPAY_NUMBER}</code>\n"
                    f"👤 Account Name – <b>{KPAY_NAME}</b>\n\n"
                    f"📢 <b>Channel Join Request ပို့ထားရန် Link များ -</b>\n"
                    f"{links_block}\n\n"
                    f"⚠️ ငွေလွှဲပြီးပါက <b>Payment Slip (SS)</b> ကို ဒီ Bot ဆီ ပို့ပေးပါဗျ။"
                )

            bot.send_message(
                call.message.chat.id,
                msg_text,
                parse_mode="HTML",
                reply_markup=markup if markup.keyboard else None,
                disable_web_page_preview=True
            )
            return

        if ADMIN_ID and str(call.message.chat.id) != str(ADMIN_ID):
            return

        if data.startswith("jr_acc_"):
            parts = data.split("_")
            chat_id, target_id = int(parts[2]), int(parts[3])
            try:
                bot.approve_chat_join_request(chat_id, target_id)
                try:
                    bot.send_message(
                        target_id,
                        "🎉 <b>ဂုဏ်ယူပါတယ်ခင်ဗျာ!</b>\n\n"
                        "✅ လူကြီးမင်း၏ VIP Channel Join Request ကို Admin မှ လက်ခံ (Accept) ပေးလိုက်ပါပြီ။ ဝင်ရောက်ကြည့်ရှုနိုင်ပါပြီဗျ 🙏",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "✅ Channel ထဲ လက်ခံပြီးပါပြီ!")
                bot.edit_message_text(call.message.text + "\n\n✅ [Admin မှ Channel ထဲ လက်ခံပြီးပါပြီ]", chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception as e:
                bot.answer_callback_query(call.id, f"Accept မရပါ: {e}", show_alert=True)
            return

        if data.startswith("jr_dec_"):
            parts = data.split("_")
            chat_id, target_id = int(parts[2]), int(parts[3])
            try:
                bot.decline_chat_join_request(chat_id, target_id)
                try:
                    bot.send_message(
                        target_id,
                        "⚠️ <b>Admin မှ အကြောင်းကြားစာ</b>\n\n"
                        "လူကြီးမင်း၏ Channel Join Request ကို ငြင်းပယ်ထားပါသည်။ ငွေလွှဲပြေစာ (Payment Slip) ပေးပို့ပြီးမှ ပြန်လည် Join Request နှိပ်ပေးပါခင်ဗျာ 🙏",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
                bot.answer_callback_query(call.id, "❌ ငြင်းပယ်ပြီးပါပြီ!")
                bot.edit_message_text(call.message.text + "\n\n❌ [Admin မှ ငြင်းပယ်ပြီးပါပြီ]", chat_id=call.message.chat.id, message_id=call.message.message_id)
            except Exception as e:
                bot.answer_callback_query(call.id, f"Decline မရပါ: {e}", show_alert=True)
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

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        user = message.from_user
        display_name = get_user_display(user)
        today_str = str(date.today())
        daily_members_log.setdefault(today_str, set()).add(display_name)

        if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
            bot.send_message(ADMIN_ID, f"🔔 <b>Customer အသစ် (@{bot_username})</b>\n👤 အမည်: {display_name}\n🆔 User ID: <code>{user.id}</code>", parse_mode="HTML")

        bot.reply_to(message, build_price_list_message(user, bot_username), parse_mode="HTML", reply_markup=get_main_buttons(), disable_web_page_preview=True)

    @bot.message_handler(content_types=['photo', 'document'])
    def handle_media(message):
        user = message.from_user
        display_name = get_user_display(user)
        raw_caption = message.caption or ""
        caption = html.escape(raw_caption) if raw_caption else "မှတ်ချက်စာသား မပါပါ"

        if ADMIN_ID and str(message.chat.id) != str(ADMIN_ID):
            info_text = (
                f"🧾 <b>Payment Slip အသစ်!</b> (@{bot_username})\n"
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
                f"💬 <b>Customer စာအသစ်</b> (@{bot_username})\n"
                f"👤 ပေးပို့သူ: {display_name}\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"✉️ စာသား: {html.escape(message.text)}"
            )
            bot.send_message(ADMIN_ID, info_text, parse_mode="HTML")

        bot.reply_to(message, build_price_list_message(user, bot_username), parse_mode="HTML", reply_markup=get_main_buttons(), disable_web_page_preview=True)

# ----------------------------------------------------
# ၅။ Bot (၂) ခုလုံးကို တစ်ပြိုင်တည်း Run ခြင်း
# ----------------------------------------------------
def run_bot_polling(bot, label):
    while True:
        try:
            bot.remove_webhook()
            time.sleep(2)
            print(f"@{label} စတင်အလုပ်လုပ်နေပါပြီ...")
            bot.polling(
                non_stop=True,
                interval=1,
                timeout=20,
                allowed_updates=["message", "callback_query", "chat_join_request"]
            )
        except Exception as e:
            print(f"[{label}] Polling error (restarting in 5s): {e}")
            time.sleep(5)

if __name__ == "__main__":
    bots_to_run = []
    for token in [BOT_TOKEN_1, BOT_TOKEN_2]:
        if token and token.strip():
            b = telebot.TeleBot(token.strip())
            try:
                uname = b.get_me().username
            except Exception:
                uname = "VIP_Bot"
            if db_bot is None:
                db_bot = b
            register_handlers(b, uname)
            bots_to_run.append((b, uname))

    load_db()

    threading.Thread(target=keep_alive_ping, daemon=True).start()
    for b, uname in bots_to_run:
        threading.Thread(target=run_bot_polling, args=(b, uname), daemon=True).start()

    run_web()
