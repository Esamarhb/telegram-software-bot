import logging
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import Forbidden, BadRequest
from database import db_manager, Software
from sqlalchemy import select

logger = logging.getLogger(__name__)

class CallbackHandlers:
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id
        
        try:
            if data.startswith("dl_"):
                sw_id = int(data.split("_")[1])
                
                async for session in db_manager.get_session():
                    result = await session.execute(select(Software).where(Software.id == sw_id))
                    sw = result.scalar_one_or_none()
                    
                    if not sw:
                        await query.answer("❌ البرنامج غير موجود")
                        break
                    
                    channel_id = sw.channel_id
                    
                    # التحقق من اشتراك المستخدم في القناة
                    try:
                        member = await context.bot.get_chat_member(
                            chat_id=channel_id,
                            user_id=user_id
                        )
                        
                        if member.status in ['left', 'kicked']:
                            # غير مشترك - عرض زر الانضمام
                            await query.answer("⚠️ يجب الاشتراك في القناة أولاً")
                            await query.edit_message_text(
                                "⚠️ للتحميل يجب الاشتراك في القناة:\n\n"
                                "https://t.me/" + channel_id.replace("@", ""),
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton(
                                        "📢 انضم للقناة",
                                        url="https://t.me/" + channel_id.replace("@", "")
                                    )
                                ]])
                            )
                        else:
                            # مشترك - إرسال الملف
                            try:
                                await context.bot.copy_message(
                                    chat_id=user_id,
                                    from_chat_id=channel_id,
                                    message_id=sw.message_id
                                )
                                await query.answer("✅ تم إرسال الملف")
                                logger.info("[DL] Sent file " + sw.name + " to user " + str(user_id))
                            except Forbidden:
                                await query.answer("❌ البوت لا يملك صلاحية الوصول للملف")
                                logger.error("[DL] Forbidden: " + sw.name)
                            except BadRequest as e:
                                await query.answer("❌ خطأ في الطلب")
                                logger.error("[DL] BadRequest: " + str(e))
                            except Exception as e:
                                await query.answer("❌ فشل الإرسال")
                                logger.error("[DL] Error: " + str(e))
                    
                    except BadRequest:
                        # المستخدم لم يتفاعل مع القناة بعد
                        await query.answer("⚠️ الرجاء فتح القناة أولاً")
                        await query.edit_message_text(
                            "⚠️ للتحميل يجب فتح القناة أولاً:\n\n"
                            "https://t.me/" + channel_id.replace("@", ""),
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton(
                                    "📢 فتح القناة",
                                    url="https://t.me/" + channel_id.replace("@", "")
                                )
                            ]])
                        )
                    
                    break
            
            elif data.startswith("info_"):
                sw_id = int(data.split("_")[1])
                
                async for session in db_manager.get_session():
                    result = await session.execute(select(Software).where(Software.id == sw_id))
                    sw = result.scalar_one_or_none()
                    
                    if sw:
                        size_mb = sw.file_size or 0
                        if size_mb >= 1024:
                            size_str = f"{size_mb/1024:.2f} GB"
                        else:
                            size_str = f"{size_mb:.2f} MB"
                        
                        info = "📋 " + sw.name + "\n\n"
                        info += "📝 " + (sw.description or "لا يوجد وصف") + "\n"
                        info += "🔢 الاصدار: " + (sw.version or "غير محدد") + "\n"
                        info += "💾 الحجم: " + size_str + "\n"
                        info += "📂 الفئة: " + (sw.category or "عام") + "\n"
                        info += "📁 النوع: " + (sw.file_type or "غير معروف") + "\n\n"
                        info += "📥 للتحميل اضغط زر التحميل"
                        
                        await query.edit_message_text(info)
                    break
            
        except Exception as e:
            logger.error("[CALLBACK] General error: " + str(e), exc_info=True)
            await query.answer("❌ حدث خطأ غير متوقع")

    def get_handlers(self) -> List:
        return [CallbackQueryHandler(self.handle_callback)]

callback_handlers = CallbackHandlers()
