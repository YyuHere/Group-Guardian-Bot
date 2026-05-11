import os, re, asyncio
from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

# ================= الإعدادات الأساسية =================
TOKEN = os.getenv('BOT_TOKEN')
MY_USER_ID = 7878629406 

# 1. الجروب اللي الميديا "هتنزل فيه" (المستودع)
TARGET_GROUP_ID = -1003809059141  

# 2. الجروب اللي البوت "هيسحب منه" الميديا (المصدر)
# حط هنا أيدي الجروب اللي عاوز تسحب منه الميديا
SOURCE_GROUP_ID = -1003999923575  # <--- غير ده وحط أيدي الجروب المصدر
# =================================================

# وظيفة مراقبة المشرفين (سحب الرتب)
async def on_chat_member_updated(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    if result.new_chat_member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        actor_id = result.from_user.id
        if actor_id != MY_USER_ID and actor_id != context.bot.id:
            try:
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
                await update.effective_chat.send_message(f"🚫 تم سحب رتبة {result.from_user.first_name}!")
            except: pass

# وظيفة حماية البوتات
async def protect_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.is_bot and member.id != context.bot.id:
                if update.message.from_user.id != MY_USER_ID:
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, member.id)
                    except: pass

# المعالج الشامل (المنع والنقل)
async def handle_everything(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    # 1. منع الروابط لغير الأدمن
    if update.message.text and re.search(r'http[s]?://|www\.', update.message.text):
        res = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if res.status not in ['administrator', 'creator']:
            try: await update.message.delete()
            except: pass
            return

    # 2. نقل الميديا (من المصدر إلى المستودع)
    # لو الرسالة جاية من الجروب اللي حددناه كـ SOURCE_GROUP_ID
    if update.message.chat_id == SOURCE_GROUP_ID:
        if update.message.photo or update.message.video:
            try:
                # نسخ الميديا للمستودع
                await context.bot.copy_message(
                    chat_id=TARGET_GROUP_ID,
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id
                )
            except Exception as e:
                print(f"نقل فاشل: {e}")

def main():
    if not TOKEN: return
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(ChatMemberHandler(on_chat_member_updated, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, protect_group))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_everything))
    
    print("البوت شغال بنظام الربط الثابت يا يوسف..")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
