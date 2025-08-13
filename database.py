import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import bcrypt
from datetime import datetime, timedelta
import secrets

load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME', 'superstar_db')
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci'
            )
            return True
        except Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def execute_query(self, query, params=None):
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                self.connection.commit()
                result = cursor.lastrowid if cursor.lastrowid else True
            
            cursor.close()
            return result
        except Error as e:
            print(f"Database error: {e}")
            return None

    def user_exists_by_phone(self, phone):
        """Check if user exists by phone number"""
        query = "SELECT id, telegram_id FROM users WHERE phone = %s"
        result = self.execute_query(query, (phone,))
        return result[0] if result else None

    def user_exists_by_telegram_id(self, telegram_id):
        """Check if user exists by Telegram ID"""
        query = "SELECT id, phone, full_name FROM users WHERE telegram_id = %s"
        result = self.execute_query(query, (telegram_id,))
        return result[0] if result else None

    def create_user(self, user_data):
        """Create new user account"""
        try:
            # Hash password
            password_hash = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            query = """
                INSERT INTO users (telegram_id, full_name, phone, email, business_name, 
                                 business_address, governorate, annual_revenue, business_type, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                user_data['telegram_id'],
                user_data['full_name'],
                user_data['phone'],
                user_data['email'],
                user_data['business_name'],
                user_data['business_address'],
                user_data['governorate'],
                user_data['annual_revenue'],
                user_data['business_type'],
                password_hash
            )
            
            result = self.execute_query(query, params)
            return result
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    def verify_password(self, phone, password):
        """Verify user password"""
        query = "SELECT id, password_hash, full_name, status FROM users WHERE phone = %s"
        result = self.execute_query(query, (phone,))
        
        if result and len(result) > 0:
            user = result[0]
            if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return user
        return None

    def update_telegram_id(self, phone, telegram_id):
        """Update user's Telegram ID after successful login"""
        query = "UPDATE users SET telegram_id = %s WHERE phone = %s"
        return self.execute_query(query, (telegram_id, phone))

    def get_user_orders(self, user_id, limit=5):
        """Get user's recent orders"""
        query = """
            SELECT o.order_number, o.status, o.total_amount, o.created_at
            FROM orders o
            WHERE o.user_id = %s
            ORDER BY o.created_at DESC
            LIMIT %s
        """
        return self.execute_query(query, (user_id, limit))

    def create_password_reset_token(self, user_id):
        """Create password reset token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        
        query = """
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, %s)
        """
        result = self.execute_query(query, (user_id, token, expires_at))
        return token if result else None

    def verify_reset_token(self, token):
        """Verify password reset token"""
        query = """
            SELECT user_id FROM password_reset_tokens
            WHERE token = %s AND expires_at > NOW() AND used = FALSE
        """
        result = self.execute_query(query, (token,))
        return result[0]['user_id'] if result else None

    def reset_password(self, user_id, new_password, token):
        """Reset user password"""
        try:
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update password
            query1 = "UPDATE users SET password_hash = %s WHERE id = %s"
            result1 = self.execute_query(query1, (password_hash, user_id))
            
            # Mark token as used
            query2 = "UPDATE password_reset_tokens SET used = TRUE WHERE token = %s"
            result2 = self.execute_query(query2, (token,))
            
            return result1 and result2
        except Exception as e:
            print(f"Error resetting password: {e}")
            return False
