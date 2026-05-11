import os, re, asyncio
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# الإعدادات
TOKEN = os.getenv('BOT_TOKEN')
TARGET_GROUP_ID = -1003809059141 
MY_USER_ID = 7878629406 

# حالات البوت
WAITING_FOR_SOURCE = 1

# 1. وظيفة مراقبة الطرد وسحب الرتب (Anti-Demote/Kick)
async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return

    # لو حد اطرد أو اتحظر (Banned or Kicked)
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id # الشخص اللي قام بالطرد
        
        # لو اللي طرد مش أنت ومش البوت نفسه
        if actor_id != MY_USER_ID and actor_id != context.bot.id:
            try:
                # فوراً سحب الرتبة وتنزيله لعضو عادي
                await context.bot.promote_chat_member(
                    chat_id=update.effective_chat.id,
                    user_id=actor_id,
                    can_change_info=False,
                    can_post_messages=False,
                    can_edit_messages=False,
                    can_delete_messages=False,
                    can_invite_users=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False
                )
                await update.effective_chat.send_message(
                    f"🚫 المشرف {result.from_user.first_name} حاول يطرد حد.. تم سحب رتبته فوراً!"
                )
            except Exception as e:
                print(f"Error demoting admin: {e}")

# 2. وظيفة الحماية من البوتات الغريبة
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.is_bot and member.id != context.bot.id:
                if update.message.from_user.id != MY_USER_ID:
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                        await update.message.reply_text("🚫 المالك فقط هو من يضيف بوتات!")
                    except: pass

# 3. أمر سحب الميديا (تحديد المصدر)
async def start_getmedia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MY_USER_ID: return
    await update.message.reply_text("🔗 ابعتلي دلوقتي رابط الجروب المصدر (أو أي رسالة منه):")
    context.user_data['state'] = WAITING_FOR_SOURCE

# 4. المعالج الشامل (نقل الميديا + منع الروابط)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    # أ - لو البوت مستني منك تحديد الجروب المصدر
    if context.user_data.get('state') == WAITING_FOR_SOURCE:
        context.chat_data['source_chat_id'] = update.message.chat_id
        context.user_data['state'] = None
        await update.message.reply_text("✅ تم ربط المصدر بنجاح! أي ميديا هتنزل هنا هتروح للمستودع.")
        return

    # ب - منع الروابط لغير الأدمن
    u_id = update.effective_user.id
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, u_id)
        if res.status not in ['administrator', 'creator']:
            try: await update.message.delete()
            except: pass
            return

    # ج - نقل الميديا (لو الرسالة جاية من المصدر المحدد)
    if update.message.chat_id == context.chat_data.get('source_chat_id'):
        if update.message.photo or update.message.video:
            try:
                await context.bot.copy_message(
                    chat_id=TARGET_GROUP_ID,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
            except: pass

def main():
    if not TOKEN: 
        print("Error: BOT_TOKEN is missing!")
        return
    app = Application.builder().token(TOKEN).build()
    
    # الأوامر
    app.add_handler(CommandHandler("getmedia", start_getmedia))
    
    # محرك مراقبة المشرفين (سحب الرتب)
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    
    # حماية الجروب من البوتات
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    
    # معالج الرسائل العام (نقل ميديا ومنع روابط)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال.. تم حذف أمر التاك بنجاح.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
