from typing import List
import logging
import json
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import db_manager, Software
from sqlalchemy import select, func
from config import settings

logger = logging.getLogger(__name__)

class AdminHandlers:
    @staticmethod
    def is_admin(user_id: int) -> bool:
        return user_id in settings.admin_ids

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.is_admin(user_id):
            await update.message.reply_text("⛔ غير مصرح")
            return
        async for session in db_manager.get_session():
            total_sw = (await session.execute(select(func.count()).select_from(Software).where(Software.is_active == True))).scalar() or 0
        text = "📊 لوحة التحكم\n\n📦 البرامج: " + str(total_sw) + "\n\nالاوامر:\n/index - فهرسة ملف\n/stats - احصائيات"
        await update.message.reply_text(text)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.is_admin(user_id):
            return
        async for session in db_manager.get_session():
            total = (await session.execute(select(func.count()).select_from(Software).where(Software.is_active == True))).scalar()
            result = await session.execute(select(Software).where(Software.is_active == True).order_by(Software.id.desc()).limit(20))
            sw_list = result.scalars().all()
        text = "📊 البرامج: " + str(total) + "\n\n"
        for sw in sw_list:
            size_str = f"{sw.file_size:.1f} MB" if sw.file_size else "?"
            text += "📦 " + sw.name + " | " + size_str + " | msg:" + str(sw.message_id) + "\n"
        await update.message.reply_text(text)

    async def index_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text(
                "📝 الاستخدام:\n"
                "/index [message_id] [اسم_البرنامج]\n\n"
                "مثال: /index 1153 ibot\n\n"
                "للمساعدة: /testindex 1153"
            )
            return
        
        try:
            original_msg_id = int(context.args[0])
            name = " ".join(context.args[1:])
        except:
            await update.message.reply_text("⚠️ خطأ في الرقم")
            return
        
        if not name:
            await update.message.reply_text("⚠️ اكتب اسم البرنامج")
            return
        
        msg = await update.message.reply_text("🔍 جاري جلب الملف...")
        
        # نجرب forward بدل copy
        file_size = 0
        file_type = "unknown"
        description = name
        caption_text = ""
        
        try:
            # جرب forward_message أولاً
            fwd = await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id="@win_app_exe",
                message_id=original_msg_id
            )
            
            # اقرأ المعلومات
            if fwd.document:
                doc = fwd.document
                file_size = (doc.file_size or 0) / (1024 * 1024)
                if doc.file_name:
                    file_type = doc.file_name.rsplit('.', 1)[-1] if '.' in doc.file_name else "unknown"
            elif fwd.video:
                file_size = (fwd.video.file_size or 0) / (1024 * 1024)
                file_type = "mp4"
            elif fwd.audio:
                file_size = (fwd.audio.file_size or 0) / (1024 * 1024)
                file_type = "mp3"
            
            caption_text = fwd.caption or ""
            if caption_text:
                description = caption_text[:500]
            
            # احذف المعاد توجيهه
            await fwd.delete()
            
        except Exception as e:
            error_msg = str(e)
            logger.error("Forward failed: " + error_msg)
            await msg.edit_text(
                "❌ فشل جلب الملف\n\n"
                "الخطأ: " + error_msg[:200] + "\n\n"
                "تأكد:\n"
                "1. البوت مشرف في @win_app_exe\n"
                "2. الملف " + str(original_msg_id) + " موجود\n"
                "3. جرب: /testindex " + str(original_msg_id)
            )
            return
        
        # تخزين
        keywords = name.split()
        if caption_text:
            keywords.extend(caption_text.split()[:30])
        keywords = list(set([k.lower() for k in keywords if len(k) > 1]))
        
        async for session in db_manager.get_session():
            sw = Software(
                name=name[:200],
                description=description[:500],
                version="1.0",
                file_type=file_type,
                file_size=file_size,
                message_id=original_msg_id,
                channel_id="@win_app_exe",
                keywords=json.dumps(keywords, ensure_ascii=False),
                category="برامج",
                is_active=True
            )
            session.add(sw)
            await session.commit()
            new_id = sw.id
        
        size_str = f"{file_size:.2f} MB" if file_size > 0 else "غير معروف"
        
        await msg.edit_text(
            "✅ تمت فهرسة: " + name + "\n\n"
            "🆔 ID: " + str(new_id) + "\n"
            "💾 الحجم: " + size_str + "\n"
            "📝 الوصف: " + description[:100]
        )

    async def testindex_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اختبار الوصول للملف"""
        user_id = update.effective_user.id
        if not self.is_admin(user_id):
            return
        
        if not context.args:
            await update.message.reply_text("📝 استخدم: /testindex [message_id]")
            return
        
        try:
            msg_id = int(context.args[0])
        except:
            await update.message.reply_text("⚠️ رقم غير صالح")
            return
        
        status = await update.message.reply_text("🔍 جاري الاختبار...")
        results = []
        
        # اختبار 1: forward_message
        try:
            fwd = await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id="@win_app_exe",
                message_id=msg_id
            )
            results.append("✅ forward_message: ناجح")
            results.append("   document: " + str(fwd.document is not None))
            results.append("   video: " + str(fwd.video is not None))
            results.append("   audio: " + str(fwd.audio is not None))
            if fwd.document:
                results.append("   file_name: " + str(fwd.document.file_name))
                results.append("   file_size: " + str(fwd.document.file_size))
            await fwd.delete()
        except Exception as e:
            results.append("❌ forward_message: " + str(e)[:100])
        
        # اختبار 2: copy_message
        try:
            copy = await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id="@win_app_exe",
                message_id=msg_id
            )
            results.append("✅ copy_message: ناجح")
            await copy.delete()
        except Exception as e:
            results.append("❌ copy_message: " + str(e)[:100])
        
        # اختبار 3: get_chat
        try:
            chat = await context.bot.get_chat("@win_app_exe")
            results.append("✅ get_chat: ناجح - " + str(chat.type))
        except Exception as e:
            results.append("❌ get_chat: " + str(e)[:100])
        
        await status.edit_text("📊 نتائج الاختبار:\n\n" + "\n".join(results))

    def get_handlers(self) -> List:
        return [
            CommandHandler("admin", self.admin_command),
            CommandHandler("stats", self.stats_command),
            CommandHandler("index", self.index_command),
            CommandHandler("testindex", self.testindex_command),
        ]

admin_handlers = AdminHandlers()
