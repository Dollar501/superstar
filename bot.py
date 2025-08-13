import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv
from database import Database
import re

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(REGISTRATION_START, FULL_NAME, PHONE, EMAIL, BUSINESS_NAME, 
 BUSINESS_ADDRESS, GOVERNORATE, ANNUAL_REVENUE, BUSINESS_TYPE, 
 PASSWORD, CONFIRM_DATA, LOGIN_PHONE, LOGIN_PASSWORD, 
 RESET_PASSWORD, NEW_PASSWORD) = range(15)

# Initialize database
db = Database()

class SuperStarBot:
    def __init__(self):
        self.web_app_url = os.getenv('WEB_APP_URL', 'http://localhost/superstar')
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        telegram_id = user.id
        
        # Check if user already exists
        existing_user = db.user_exists_by_telegram_id(telegram_id)
        
        if existing_user:
            # User exists, show main menu
            keyboard = [
                [KeyboardButton("🌟 افتح تطبيق SuperStar", web_app=WebAppInfo(url=self.web_app_url))],
                [KeyboardButton("📦 تتبع طلبي"), KeyboardButton("🚪 تسجيل الخروج")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"مرحباً بك مرة أخرى {existing_user['full_name']}! 👋\n\n"
                "اختر ما تريد فعله:",
                reply_markup=reply_markup
            )
        else:
            # New user, show registration options
            keyboard = [
                [KeyboardButton("📝 تسجيل حساب جديد")],
                [KeyboardButton("🔑 لدي حساب بالفعل")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "🌟 مرحباً بك في SuperStar! 🌟\n\n"
                "نظام إدارة المخازن والبيع بالجملة المتطور\n"
                "المتخصص في تجارة الأحذية\n\n"
                "اختر أحد الخيارات التالية:",
                reply_markup=reply_markup
            )
        
        return REGISTRATION_START

    async def registration_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle registration choice"""
        text = update.message.text
        
        if text == "📝 تسجيل حساب جديد":
            await update.message.reply_text(
                "ممتاز! سنقوم بإنشاء حساب جديد لك.\n\n"
                "الرجاء إدخال الاسم الثلاثي:",
                reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True)
            )
            return FULL_NAME
            
        elif text == "🔑 لدي حساب بالفعل":
            await update.message.reply_text(
                "الرجاء إدخال رقم الهاتف المسجل:",
                reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True)
            )
            return LOGIN_PHONE
        
        return REGISTRATION_START

    async def get_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's full name"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        full_name = update.message.text.strip()
        if len(full_name) < 6:
            await update.message.reply_text("الرجاء إدخال الاسم الثلاثي كاملاً (على الأقل 6 أحرف):")
            return FULL_NAME
        
        context.user_data['full_name'] = full_name
        await update.message.reply_text(
            "ممتاز! 👍\n\n"
            "الرجاء إدخال رقم الهاتف:\n"
            "(مثال: 07901234567)"
        )
        return PHONE

    async def get_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's phone number"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        phone = update.message.text.strip()
        
        # Validate phone number (Iraqi format)
        if not re.match(r'^07[3-9]\d{8}$', phone):
            await update.message.reply_text(
                "رقم الهاتف غير صحيح. الرجاء إدخال رقم عراقي صحيح:\n"
                "(مثال: 07901234567)"
            )
            return PHONE
        
        # Check if phone already exists
        existing_user = db.user_exists_by_phone(phone)
        if existing_user:
            await update.message.reply_text(
                "هذا الرقم مسجل بالفعل في النظام.\n"
                "يمكنك تسجيل الدخول باستخدام خيار 'لدي حساب بالفعل'"
            )
            return PHONE
        
        context.user_data['phone'] = phone
        
        # Email input with helper buttons
        keyboard = [
            [KeyboardButton("@gmail.com"), KeyboardButton("@yahoo.com")],
            [KeyboardButton("@hotmail.com"), KeyboardButton("❌ إلغاء")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "الرجاء إدخال البريد الإلكتروني:\n"
            "(يمكنك استخدام الأزرار أدناه للمساعدة)",
            reply_markup=reply_markup
        )
        return EMAIL

    async def get_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get user's email"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        text = update.message.text.strip()
        
        # Handle helper buttons
        if text in ["@gmail.com", "@yahoo.com", "@hotmail.com"]:
            await update.message.reply_text(f"اكتب اسم المستخدم قبل {text}")
            return EMAIL
        
        # Validate email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
            await update.message.reply_text("البريد الإلكتروني غير صحيح. الرجاء المحاولة مرة أخرى:")
            return EMAIL
        
        context.user_data['email'] = text
        await update.message.reply_text(
            "ما هو اسم نشاطك التجاري أو المنشأة؟",
            reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True)
        )
        return BUSINESS_NAME

    async def get_business_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get business name"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        context.user_data['business_name'] = update.message.text.strip()
        await update.message.reply_text("أين يقع عنوان المنشأة؟")
        return BUSINESS_ADDRESS

    async def get_business_address(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get business address"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        context.user_data['business_address'] = update.message.text.strip()
        
        # Iraqi governorates
        governorates = [
            ["بغداد", "البصرة"], ["نينوى", "أربيل"],
            ["النجف", "كربلاء"], ["الأنبار", "صلاح الدين"],
            ["كركوك", "ديالى"], ["واسط", "بابل"],
            ["المثنى", "القادسية"], ["ذي قار", "ميسان"],
            ["دهوك", "السليمانية"], ["❌ إلغاء"]
        ]
        reply_markup = ReplyKeyboardMarkup(governorates, resize_keyboard=True)
        
        await update.message.reply_text(
            "الرجاء تحديد محافظة الإقامة:",
            reply_markup=reply_markup
        )
        return GOVERNORATE

    async def get_governorate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get governorate"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        context.user_data['governorate'] = update.message.text.strip()
        
        # Annual revenue options
        revenue_options = [
            ["أقل من 50 ألف"], ["50-100 ألف"],
            ["100-200 ألف"], ["200-500 ألف"],
            ["أكثر من 500 ألف"], ["❌ إلغاء"]
        ]
        reply_markup = ReplyKeyboardMarkup(revenue_options, resize_keyboard=True)
        
        await update.message.reply_text(
            "كم تقدر أرباحك السنوية؟",
            reply_markup=reply_markup
        )
        return ANNUAL_REVENUE

    async def get_annual_revenue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get annual revenue"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        revenue_map = {
            "أقل من 50 ألف": "less_than_50k",
            "50-100 ألف": "50k_100k",
            "100-200 ألف": "100k_200k",
            "200-500 ألف": "200k_500k",
            "أكثر من 500 ألف": "more_than_500k"
        }
        
        context.user_data['annual_revenue'] = revenue_map.get(update.message.text.strip(), "less_than_50k")
        
        # Business type options
        business_types = [
            ["جملة", "قطاعي"],
            ["❌ إلغاء"]
        ]
        reply_markup = ReplyKeyboardMarkup(business_types, resize_keyboard=True)
        
        await update.message.reply_text(
            "ما هو نوع نشاطك؟",
            reply_markup=reply_markup
        )
        return BUSINESS_TYPE

    async def get_business_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get business type"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        business_type_map = {
            "جملة": "wholesale",
            "قطاعي": "retail"
        }
        
        context.user_data['business_type'] = business_type_map.get(update.message.text.strip(), "retail")
        
        await update.message.reply_text(
            "الرجاء إدخال كلمة مرور قوية لتأمين حسابك:\n"
            "(على الأقل 8 أحرف، تحتوي على أرقام وحروف)",
            reply_markup=ReplyKeyboardMarkup([["❌ إلغاء"]], resize_keyboard=True)
        )
        return PASSWORD

    async def get_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get password"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        password = update.message.text.strip()
        
        # Validate password
        if len(password) < 8:
            await update.message.reply_text("كلمة المرور يجب أن تكون 8 أحرف على الأقل:")
            return PASSWORD
        
        if not re.search(r'[0-9]', password) or not re.search(r'[a-zA-Z]', password):
            await update.message.reply_text("كلمة المرور يجب أن تحتوي على أرقام وحروف:")
            return PASSWORD
        
        context.user_data['password'] = password
        
        # Delete the password message for security
        try:
            await update.message.delete()
        except:
            pass
        
        # Show confirmation
        user_data = context.user_data
        confirmation_text = f"""
📋 تأكيد البيانات:

👤 الاسم: {user_data['full_name']}
📱 الهاتف: {user_data['phone']}
📧 البريد: {user_data['email']}
🏢 النشاط: {user_data['business_name']}
📍 العنوان: {user_data['business_address']}
🏛️ المحافظة: {user_data['governorate']}
💰 الأرباح السنوية: {[k for k, v in {"أقل من 50 ألف": "less_than_50k", "50-100 ألف": "50k_100k", "100-200 ألف": "100k_200k", "200-500 ألف": "200k_500k", "أكثر من 500 ألف": "more_than_500k"}.items() if v == user_data['annual_revenue']][0]}
🏪 نوع النشاط: {"جملة" if user_data['business_type'] == "wholesale" else "قطاعي"}

هل البيانات صحيحة؟
        """
        
        keyboard = [
            ["✅ تأكيد التسجيل", "❌ إلغاء"],
            ["✏️ تعديل البيانات"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
        return CONFIRM_DATA

    async def confirm_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirm registration data"""
        text = update.message.text
        
        if text == "✅ تأكيد التسجيل":
            # Save user to database
            user_data = context.user_data.copy()
            user_data['telegram_id'] = update.effective_user.id
            
            user_id = db.create_user(user_data)
            
            if user_id:
                # Success message with web app button
                keyboard = [[KeyboardButton("🌟 افتح تطبيق SuperStar", web_app=WebAppInfo(url=self.web_app_url))]]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    "🎉 تم إنشاء حسابك بنجاح!\n\n"
                    "مرحباً بك في عائلة SuperStar 🌟\n"
                    "يمكنك الآن الوصول إلى جميع خدماتنا",
                    reply_markup=reply_markup
                )
                
                # Clear user data
                context.user_data.clear()
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ حدث خطأ أثناء إنشاء الحساب.\n"
                    "الرجاء المحاولة مرة أخرى أو التواصل مع الدعم الفني."
                )
                return CONFIRM_DATA
        
        elif text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        elif text == "✏️ تعديل البيانات":
            await update.message.reply_text("سيتم إضافة خاصية التعديل قريباً. الرجاء إلغاء التسجيل والبدء من جديد.")
            return CONFIRM_DATA
        
        return CONFIRM_DATA

    async def login_phone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle login phone input"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        phone = update.message.text.strip()
        
        # Check if user exists
        user = db.user_exists_by_phone(phone)
        if not user:
            await update.message.reply_text(
                "❌ هذا الرقم غير مسجل لدينا.\n"
                "يمكنك التسجيل من جديد باختيار 'تسجيل حساب جديد'"
            )
            return LOGIN_PHONE
        
        context.user_data['login_phone'] = phone
        await update.message.reply_text(
            "الرجاء إدخال كلمة المرور:\n"
            "(سيتم حذف رسالتك تلقائياً لحماية خصوصيتك)"
        )
        return LOGIN_PASSWORD

    async def login_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle login password"""
        if update.message.text == "❌ إلغاء":
            return await self.cancel(update, context)
        
        password = update.message.text.strip()
        phone = context.user_data['login_phone']
        
        # Delete password message immediately
        try:
            await update.message.delete()
        except:
            pass
        
        # Verify password
        user = db.verify_password(phone, password)
        
        if user:
            if user['status'] != 'active':
                await update.message.reply_text("❌ حسابك معطل. الرجاء التواصل مع الدعم الفني.")
                return ConversationHandler.END
            
            # Update telegram ID
            db.update_telegram_id(phone, update.effective_user.id)
            
            # Success - show main menu
            keyboard = [
                [KeyboardButton("🌟 افتح تطبيق SuperStar", web_app=WebAppInfo(url=self.web_app_url))],
                [KeyboardButton("📦 تتبع طلبي"), KeyboardButton("🚪 تسجيل الخروج")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"مرحباً بك {user['full_name']}! 👋\n\n"
                "تم تسجيل الدخول بنجاح ✅",
                reply_markup=reply_markup
            )
            
            context.user_data.clear()
            return ConversationHandler.END
        else:
            keyboard = [
                [KeyboardButton("🔄 المحاولة مرة أخرى")],
                [KeyboardButton("🔑 نسيت كلمة المرور؟")],
                [KeyboardButton("❌ إلغاء")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "❌ كلمة المرور غير صحيحة.\n"
                "اختر أحد الخيارات:",
                reply_markup=reply_markup
            )
            return LOGIN_PASSWORD

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle main menu options"""
        text = update.message.text
        user = update.effective_user
        
        if text == "📦 تتبع طلبي":
            # Get user's recent orders
            db_user = db.user_exists_by_telegram_id(user.id)
            if db_user:
                orders = db.get_user_orders(db_user['id'])
                if orders:
                    orders_text = "📦 آخر طلباتك:\n\n"
                    for order in orders:
                        status_emoji = {
                            'pending': '⏳',
                            'confirmed': '✅',
                            'shipped': '🚚',
                            'delivered': '📦',
                            'cancelled': '❌'
                        }.get(order['status'], '❓')
                        
                        orders_text += f"{status_emoji} {order['order_number']}\n"
                        orders_text += f"المبلغ: {order['total_amount']} د.ع\n"
                        orders_text += f"التاريخ: {order['created_at'].strftime('%Y-%m-%d')}\n\n"
                    
                    await update.message.reply_text(orders_text)
                else:
                    await update.message.reply_text("لا توجد طلبات حالياً 📭")
            else:
                await update.message.reply_text("❌ خطأ في الوصول للبيانات")
        
        elif text == "🚪 تسجيل الخروج":
            # Clear telegram_id from database
            db_user = db.user_exists_by_telegram_id(user.id)
            if db_user:
                db.update_telegram_id(db_user['phone'], None)
            
            keyboard = [
                [KeyboardButton("📝 تسجيل حساب جديد")],
                [KeyboardButton("🔑 لدي حساب بالفعل")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "تم تسجيل الخروج بنجاح 👋\n"
                "يمكنك تسجيل الدخول مرة أخرى في أي وقت",
                reply_markup=reply_markup
            )

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel conversation"""
        context.user_data.clear()
        
        keyboard = [
            [KeyboardButton("📝 تسجيل حساب جديد")],
            [KeyboardButton("🔑 لدي حساب بالفعل")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "تم إلغاء العملية ❌\n"
            "يمكنك البدء من جديد في أي وقت",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(os.getenv('BOT_TOKEN')).build()
    
    bot = SuperStarBot()
    
    # Conversation handler for registration and login
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', bot.start)],
        states={
            REGISTRATION_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.registration_start)],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_full_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_phone)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_email)],
            BUSINESS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_business_name)],
            BUSINESS_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_business_address)],
            GOVERNORATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_governorate)],
            ANNUAL_REVENUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_annual_revenue)],
            BUSINESS_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_business_type)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.get_password)],
            CONFIRM_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.confirm_data)],
            LOGIN_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.login_phone)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.login_password)],
        },
        fallbacks=[CommandHandler('cancel', bot.cancel)]
    )
    
    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_main_menu))
    
    # Start the bot
    print("🌟 SuperStar Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
