import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from database import db_manager, Software
from sqlalchemy import select, func, or_
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

class UserHandlers:
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        await update.message.reply_text(
            "👋 مرحبا " + (user.first_name or "مستخدم") + "\n\n"
            "🔍 اكتب اسم البرنامج للبحث\n"
            "/search - بحث\n/admin - لوحة تحكم\n/help - مساعدة"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📖 اكتب اسم البرنامج مباشرة للبحث\n"
            "مثال: Chrome, Pc, Firefox, Python"
        )

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("📝 مثال: /search Chrome")
            return
        text = " ".join(context.args)
        await self.do_search(update, text)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text.startswith("/"):
            return
        if len(text) < 2:
            await update.message.reply_text("⚠️ اكتب كلمة بحث اطول")
            return
        await self.do_search(update, text)

    async def do_search(self, update: Update, text: str):
        logger.info("[SEARCH] Searching for: " + text)
        
        msg = await update.message.reply_text("🔍 جاري البحث...")
        
        try:
            search_pattern = "%" + text + "%"
            
            async for session in db_manager.get_session():
                # بحث موسع: name + description + keywords
                stmt = select(Software).where(
                    or_(
                        Software.name.like(search_pattern),
                        Software.description.like(search_pattern),
                        Software.keywords.like(search_pattern),
                        Software.category.like(search_pattern)
                    ),
                    Software.is_active == True
                ).limit(10)
                
                result = await session.execute(stmt)
                software_list = result.scalars().all()
                logger.info("[SEARCH] Found: " + str(len(software_list)))
                break
            
            await msg.delete()
            
            if not software_list:
                # جرب بحث أوسع - split words
                words = text.split()
                if len(words) > 1:
                    for word in words:
                        if len(word) >= 2:
                            search_pattern = "%" + word + "%"
                            async for session in db_manager.get_session():
                                stmt = select(Software).where(
                                    or_(
                                        Software.name.like(search_pattern),
                                        Software.description.like(search_pattern),
                                        Software.keywords.like(search_pattern)
                                    ),
                                    Software.is_active == True
                                ).limit(10)
                                result = await session.execute(stmt)
                                software_list = result.scalars().all()
                                break
                            if software_list:
                                break
                
                if not software_list:
                    await update.message.reply_text(
                        "❌ لا توجد نتائج لـ: " + text + "\n\n"
                        "💡 جرب:\n"
                        "- كلمة اخرى\n"
                        "- جزء من الاسم\n"
                        "- /stats لعرض كل البرامج"
                    )
                    return
            
            response = "🔍 نتائج البحث عن: " + text + "\n\n"
            keyboard = []
            
            for sw in software_list:
                size_mb = sw.file_size or 0
                if size_mb >= 1024:
                    size_str = f"{size_mb/1024:.2f} GB"
                else:
                    size_str = f"{size_mb:.2f} MB"
                
                response += "📦 " + sw.name + "\n"
                response += "   💾 " + size_str + " | 📂 " + (sw.category or "عام") + "\n"
                if sw.description:
                    response += "   📝 " + sw.description[:80] + "\n"
                response += "\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        "📥 تحميل",
                        callback_data="dl_" + str(sw.id)
                    ),
                    InlineKeyboardButton(
                        "ℹ️ معلومات",
                        callback_data="info_" + str(sw.id)
                    )
                ])
            
            await update.message.reply_text(
                response,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error("[SEARCH] Error: " + str(e), exc_info=True)
            await msg.delete()
            await update.message.reply_text("❌ خطأ في البحث: " + str(e)[:200])

    def get_handlers(self):
        return [
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("search", self.search_command),
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
        ]

user_handlers = UserHandlers()
