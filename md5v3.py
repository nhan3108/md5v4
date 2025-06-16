import os
import telebot
from telebot import types
from datetime import datetime, timedelta
import json
import math
import numpy as np
import re
import hashlib
from collections import defaultdict
import time
import random

# ==============================================
# CẤU HÌNH HỆ THỐNG
# ==============================================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7780640154
SUPPORT_CONTACT = "@huydev"
REQUIRED_GROUPS = ["@techtitansteam", "@techtitansteamchat"]
PREMIUM_CODE = "VIP7DAYFREE"
BOT_USERNAME = "botmd5v2pro_bot"

bot = telebot.TeleBot(TOKEN)

# Danh sách emoji reaction ngẫu nhiên
REACTION_EMOJIS = ["👀"]

# Danh sách icon ngẫu nhiên cho tin nhắn phản hồi
RESPONSE_ICONS = ["🌟", "🚀", "🦠", "🔮", "🧬", "⚡️", "🌌", "🛡️", "💎", "🔥", "🎯", "🦾"]

# Icon hệ thống
ICONS = {
    "success": "✅", "error": "❌", "info": "ℹ️", "warning": "⚠️", "vip": "💎",
    "lock": "🔒", "unlock": "🔓", "clock": "⏰", "stats": "📊", "history": "📜",
    "user": "👤", "admin": "🛡️", "broadcast": "📢", "referral": "📨", "group": "👥",
    "tai": "🎰", "xiu": "🎲", "engine": "⚙️", "risk": "🚸", "time": "⏰",
    "correct": "✔️", "wrong": "❌", "analyze": "🔍", "invite": "📩", "help": "🆘"
}

# ==============================================
# CƠ SỞ DỮ LIỆU
# ==============================================
class Database:
    @staticmethod
    def load(filename):
        try:
            with open(f'{filename}.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save(data, filename):
        try:
            with open(f'{filename}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lỗi lưu {filename}: {e}")

# Khởi tạo cơ sở dữ liệu
users = Database.load('users')
history = Database.load('history')
activity = Database.load('activity')
codes_db = Database.load('codes')
referral_db = Database.load('referral')
config_db = Database.load('config')
reverse_mode = config_db.get('reverse_mode', False)

# ==============================================
# TIỆN ÍCH HỆ THỐNG
# ==============================================
def is_user_in_group(user_id, group_username):
    try:
        chat_member = bot.get_chat_member(group_username, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except:
        return False

def check_group_membership(user_id):
    return [group for group in REQUIRED_GROUPS if not is_user_in_group(user_id, group)]

def is_vip_active(uid):
    uid = str(uid)
    user = users.get(uid, {})
    if not user.get("vip_active", False):
        return False
    exp_str = user.get("vip_expire", "")
    try:
        return datetime.now() <= datetime.strptime(exp_str, "%Y-%m-%d %H:%M:%S")
    except:
        return False

def activate_vip(uid, days=7, extend=False):
    uid = str(uid)
    users[uid] = users.get(uid, {})
    if extend and users[uid].get("vip_expire"):
        try:
            current_expire = datetime.strptime(users[uid]["vip_expire"], "%Y-%m-%d %H:%M:%S")
            exp_date = (max(datetime.now(), current_expire) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        except:
            exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    users[uid]["vip_active"] = True
    users[uid]["vip_expire"] = exp_date
    users[uid]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    Database.save(users, 'users')
    return exp_date

def create_premium_code(code_name, days, max_uses=1):
    codes_db[code_name] = {
        "days": days,
        "max_uses": max_uses,
        "used_count": 0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "used_by": []
    }
    Database.save(codes_db, 'codes')
    return codes_db[code_name]

def use_premium_code(code_name, user_id):
    if code_name not in codes_db:
        return False, f"{ICONS['error']} Mã không hợp lệ!"
    code = codes_db[code_name]
    user_id = str(user_id)
    if user_id in code["used_by"]:
        return False, f"{ICONS['warning']} Bạn đã sử dụng mã này!"
    if code["used_count"] >= code["max_uses"]:
        return False, f"{ICONS['clock']} Mã đã hết lượt sử dụng!"
    
    extend = user_id in users and users[user_id].get("vip_active")
    exp_date = activate_vip(user_id, code["days"], extend)
    code["used_count"] += 1
    code["used_by"].append(user_id)
    Database.save(codes_db, 'codes')
    return True, f"{ICONS['success']} Kích hoạt VIP {code['days']} ngày thành công!\n⏰ Hết hạn: {exp_date}"

def track_activity(user_id, action):
    user_id = str(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    activity[user_id] = activity.get(user_id, {
        "first_seen": now,
        "last_seen": now,
        "request_count": 0,
        "actions": []
    })
    activity[user_id]["last_seen"] = now
    activity[user_id]["request_count"] += 1
    activity[user_id]["actions"].append(action)
    Database.save(activity, 'activity')

def create_referral_code(user_id):
    code = f"REF1DAY_{user_id}_{int(time.time())}"
    create_premium_code(code, 1, 1)
    return code

def track_referral(referrer_id, referred_id):
    referrer_id = str(referrer_id)
    referred_id = str(referred_id)
    
    if referrer_id not in referral_db:
        referral_db[referrer_id] = []
    
    if referred_id not in referral_db[referrer_id]:
        referral_db[referrer_id].append(referred_id)
        Database.save(referral_db, 'referral')
        
        reward_code = create_referral_code(referrer_id)
        try:
            bot.send_message(
                referrer_id,
                f"""
{ICONS['success']} Chúc mừng bạn đã mời thành công ID {referred_id}!
🔑 Mã thưởng: <code>{reward_code}</code>
📋 Sử dụng: /code {reward_code}
                """,
                parse_mode="HTML"
            )
        except:
            pass

# ==============================================
# HỆ THỐNG PHÂN TÍCH MD5
# ==============================================
class MD5Analyzer:
    @staticmethod
    def hyper_ai_engine(md5_hash):
        md5_hash = md5_hash.lower().strip()
        if len(md5_hash) != 32 or not re.match(r'^[a-f0-9]{32}$', md5_hash):
            raise ValueError("MD5 không hợp lệ")
        
        hex_bytes = [int(md5_hash[i:i+2], 16) for i in range(0, len(md5_hash), 2)]
        byte_array = np.array(hex_bytes)
        total_sum = sum(hex_bytes)

        # Thuật toán 1: Hyper-AI 7 Engines
        quantum_sum = sum(byte_array[i] * math.cos(i * math.pi/16) for i in range(16))
        neural_score = sum(byte_array[i] * (1.618 ** (i % 5)) for i in range(16))
        fractal_dim = sum(byte_array[i] * (1 + math.sqrt(5)) / 2 for i in range(16))
        score1 = (quantum_sum + neural_score + fractal_dim) % 20
        result1 = "TÀI" if score1 < 10 else "XỈU"
        prob1 = 95 - abs(score1 - 10) * 4.5 if score1 < 10 else 50 + (score1 - 10) * 4.5

        # Thuật toán 2: Diamond AI 7
        nums = [int(c, 16) for c in md5_hash]
        avg = sum(nums) / 32
        even_count = sum(1 for n in nums if n % 2 == 0)
        over8_count = sum(1 for n in nums if n > 8)
        score2 = (1 if avg > 7.5 else 0) + (1 if even_count > 16 else 0) + (1 if over8_count >= 10 else 0)
        result2 = "TÀI" if score2 >= 2 else "XỈU"
        prob2 = 90 if score2 == 3 else 75 if score2 == 2 else 60
        prob2 = prob2 if result2 == "TÀI" else 100 - prob2

        # Thuật toán 3: AI-Tech Titans
        x = int(md5_hash, 16)
        result3 = "TÀI" if x % 2 == 0 else "XỈU"
        prob3 = 75.0

        # Kết quả cuối cùng
        weights = [0.5, 0.3, 0.2]
        final_score = (score1 * weights[0] + score2 * 5 * weights[1] + (0 if result3 == "XỈU" else 10) * weights[2])
        final_result = "TÀI" if final_score < 10 else "XỈU"
        final_prob = (prob1 * weights[0] + prob2 * weights[1] + prob3 * weights[2])
        
        if reverse_mode:
            final_result = "XỈU" if final_result == "TÀI" else "TÀI"
            final_prob = 100 - final_prob

        risk_level = "THẤP" if final_prob > 80 else "TRUNG BÌNH" if final_prob > 60 else "CAO"
        
        return {
            "total_sum": total_sum,
            "algo1": {"result": result1, "prob": f"{prob1:.1f}%", "score": score1},
            "algo2": {"result": result2, "prob": f"{prob2:.1f}%", "score": score2},
            "algo3": {"result": result3, "prob": f"{prob3:.1f}%", "score": x % 2},
            "final": {"result": final_result, "prob": f"{final_prob:.1f}%"},
            "risk": risk_level,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reversed": reverse_mode
        }

# ==============================================
# GIAO DIỆN NGƯỜI DÙNG
# ==============================================
class UserInterface:
    @staticmethod
    def create_main_menu():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton(f"{ICONS['analyze']} Phân Tích MD5"),
            types.KeyboardButton(f"{ICONS['vip']} Thông Tin VIP")
        )
        markup.add(
            types.KeyboardButton(f"{ICONS['stats']} Thống Kê"),
            types.KeyboardButton(f"{ICONS['history']} Lịch Sử")
        )
        markup.add(
            types.KeyboardButton(f"{ICONS['invite']} Mời Bạn"),
            types.KeyboardButton(f"{ICONS['help']} Hỗ Trợ")
        )
        return markup

    @staticmethod
    def create_inline_menu():
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"{ICONS['help']} Hỗ Trợ", callback_data="menu_help")
        )
        return markup

    @staticmethod
    def create_result_message(md5_input, analysis):
        mode = "ĐẢO" if analysis["reversed"] else "BÌNH THƯỜNG"
        return (
            f"╭───{ICONS['engine']} <b>HYPER-AI 7 ENGINES PRO MAX</b> ───╮\n"
            f"│ {ICONS['info']} <b>Phiên bản:</b> HYPER-AI 7 ENGINES\n"
            f"│ {ICONS['lock']} <b>MD5:</b> <code>{md5_input[:8]}...{md5_input[-8:]}</code>\n"
            f"│ {ICONS['stats']} <b>Tổng HEX:</b> <code>{analysis['total_sum']}</code>\n"
            f"│ {ICONS['engine']} <b>Chế độ:</b> <code>{mode}</code>\n"
            f"├──────────────────────────────┤\n"
            f"│ <b>🌌 THUẬT TOÁN HYPER-AI</b>\n"
            f"│ {ICONS['tai' if analysis['algo1']['result'] == 'TÀI' else 'xiu']} Dự đoán: <b>{analysis['algo1']['result']}</b>\n"
            f"│ {ICONS['stats']} Xác suất: <code>{analysis['algo1']['prob']}</code>\n"
            f"│\n"
            f"│ <b>🧬 THUẬT TOÁN DIAMOND AI</b>\n"
            f"│ {ICONS['tai' if analysis['algo2']['result'] == 'TÀI' else 'xiu']} Dự đoán: <b>{analysis['algo2']['result']}</b>\n"
            f"│ {ICONS['stats']} Xác suất: <code>{analysis['algo2']['prob']}</code>\n"
            f"│\n"
            f"│ <b>🦠 THUẬT TOÁN AI-TECH TITANS</b>\n"
            f"│ {ICONS['tai' if analysis['algo3']['result'] == 'TÀI' else 'xiu']} Dự đoán: <b>{analysis['algo3']['result']}</b>\n"
            f"│ {ICONS['stats']} Xác suất: <code>{analysis['algo3']['prob']}</code>\n"
            f"├──────────────────────────────┤\n"
            f"│ <b>📊 THỐNG KÊ THUẬT TOÁN</b>\n"
            f"│ {ICONS['stats']} Hyper-AI: <code>{analysis['algo1']['score']:.2f}</code>\n"
            f"│ {ICONS['stats']} Diamond AI: <code>{analysis['algo2']['score']:.2f}</code>\n"
            f"│ {ICONS['stats']} AI-Tech: <code>{analysis['algo3']['score']:.2f}</code>\n"
            f"├──────────────────────────────┤\n"
            f"│ <b>🎯 KẾT LUẬN CUỐI CÙNG</b>\n"
            f"│ {ICONS['tai' if analysis['final']['result'] == 'TÀI' else 'xiu']} Dự đoán: <b>{analysis['final']['result']}</b>\n"
            f"│ {ICONS['stats']} Xác suất: <code>{analysis['final']['prob']}</code>\n"
            f"│ {ICONS['risk']} Rủi ro: <b>{analysis['risk']}</b>\n"
            f"│ {ICONS['time']} Thời gian: {analysis['timestamp']}\n"
            f"╰──────────────────────────────╯"
        )

# ==============================================
# QUẢN LÝ DỮ LIỆU
# ==============================================
def save_prediction(user_id, md5, analysis, is_correct=None):
    user_id = str(user_id)
    history[user_id] = history.get(user_id, [])
    history[user_id].append({
        "md5": md5,
        "prediction": analysis,
        "timestamp": analysis["timestamp"],
        "is_correct": is_correct,
        "awaiting_feedback": True if is_correct is None else False
    })
    if len(history[user_id]) > 100:
        history[user_id] = history[user_id][-100:]
    Database.save(history, 'history')

def check_feedback_status(user_id):
    user_id = str(user_id)
    if user_id in history:
        for entry in history[user_id]:
            if entry.get("awaiting_feedback", False):
                return True, entry["md5"]
    return False, None

def get_user_stats(user_id):
    user_id = str(user_id)
    if user_id not in history or not history[user_id]:
        return None
    user_history = history[user_id]
    total = len(user_history)
    correct = sum(1 for entry in user_history if entry.get("is_correct") is True)
    wrong = sum(1 for entry in user_history if entry.get("is_correct") is False)
    accuracy = correct / total * 100 if total > 0 else 0
    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy": accuracy
    }

# ==============================================
# HÀM PHẢN HỒI VỚI REACTION VÀ TYPING
# ==============================================
def send_response_with_reaction_and_typing(chat_id, message, response_text, reply_markup=None):
    # Gửi reaction (emoji) ngay sau tin nhắn người dùng
    reaction_emoji = random.choice(REACTION_EMOJIS)
    bot.send_message(chat_id, reaction_emoji, reply_to_message_id=message.message_id)
    
    # Hiển thị trạng thái "đang nhập"
    bot.send_chat_action(chat_id, 'typing')
    time.sleep(random.uniform(0.5, 1.5))  # Độ trễ ngẫu nhiên để giống người
    
    # Gửi phản hồi chính
    random_icon = random.choice(RESPONSE_ICONS)
    bot.send_message(
        chat_id,
        f"{random_icon} {response_text}",
        parse_mode="HTML",
        reply_markup=reply_markup,
        reply_to_message_id=message.message_id
    )

# ==============================================
# XỬ LÝ LỆNH
# ==============================================
@bot.message_handler(commands=['start'])
def handle_start(message):
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]
        if referrer_id != str(message.from_user.id):
            track_referral(referrer_id, message.from_user.id)
    
    name = message.from_user.first_name or "Người Dùng"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"{ICONS['success']} Xác Nhận Nhóm", callback_data="verify_groups"))
    response_text = (
        f"╭─── <b>Chào Mừng {name}!</b> ───╮\n"
        f"│ {ICONS['info']} Tham gia các nhóm để nhận <b>VIP 7 ngày miễn phí</b>!\n"
        f"│ 👥 @techtitansteam\n"
        f"│ 👥 @techtitansteamchat\n"
        f"│ {ICONS['help']} Nhấn nút để xác nhận và nhận mã!\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text, markup)
    track_activity(message.from_user.id, "start")

@bot.message_handler(commands=['code'])
def handle_code(message):
    parts = message.text.split()
    if len(parts) != 2:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /code [mã]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    success, msg = use_premium_code(parts[1].upper(), message.from_user.id)
    response_text = (
        f"╭─── {ICONS['vip']} <b>Kích Hoạt VIP</b> ───╮\n"
        f"│ {msg}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"use_code:{parts[1]}")

@bot.message_handler(commands=['ban'])
def handle_ban(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    parts = message.text.split()
    if len(parts) != 2:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /ban [user_id]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    uid = parts[1]
    users[uid] = users.get(uid, {})
    users[uid]["banned"] = True
    Database.save(users, 'users')
    try:
        bot.send_message(uid, f"{random.choice(RESPONSE_ICONS)} {ICONS['error']} Tài khoản của bạn đã bị cấm!", parse_mode="HTML")
    except:
        pass
    response_text = (
        f"╭─── {ICONS['admin']} <b>Quản Lý</b> ───╮\n"
        f"│ {ICONS['success']} Đã cấm người dùng <code>{uid}</code>\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"ban:{uid}")

@bot.message_handler(commands=['unban'])
def handle_unban(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    parts = message.text.split()
    if len(parts) != 2:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /unban [user_id]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    uid = parts[1]
    if uid in users:
        users[uid]["banned"] = False
        Database.save(users, 'users')
        try:
            bot.send_message(uid, f"{random.choice(RESPONSE_ICONS)} {ICONS['success']} Tài khoản của bạn đã được bỏ cấm!", parse_mode="HTML")
        except:
            pass
        response_text = (
            f"╭─── {ICONS['admin']} <b>Quản Lý</b> ───╮\n"
            f"│ {ICONS['success']} Đã bỏ cấm người dùng <code>{uid}</code>\n"
            f"╰────────────────────────────╯"
        )
    else:
        response_text = (
            f"╭─── {ICONS['admin']} <b>Quản Lý</b> ───╮\n"
            f"│ {ICONS['error']} Không tìm thấy người dùng <code>{uid}</code>\n"
            f"╰────────────────────────────╯"
        )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"unban:{uid}")

@bot.message_handler(commands=['userinfo'])
def handle_userinfo(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    parts = message.text.split()
    if len(parts) != 2:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /userinfo [user_id]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    uid = parts[1]
    if uid not in users:
        response_text = (
            f"╭─── {ICONS['user']} <b>Thông Tin Người Dùng</b> ───╮\n"
            f"│ {ICONS['error']} Không tìm thấy người dùng <code>{uid}</code>\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    user = users[uid]
    stats = get_user_stats(uid)
    stats_msg = f"""
│ {ICONS['stats']} Thống kê:\n
│ {ICONS['correct']} Đúng: <code>{stats['correct']}</code>\n
│ {ICONS['wrong']} Sai: <code>{stats['wrong']}</code>\n
│ {ICONS['stats']} Chính xác: <code>{stats['accuracy']:.2f}%</code>
    """ if stats else f"│ {ICONS['info']} Chưa có thống kê"
    response_text = (
        f"╭─── {ICONS['user']} <b>Thông Tin Người Dùng</b> ───╮\n"
        f"│ {ICONS['user']} ID: <code>{uid}</code>\n"
        f"│ {ICONS['vip']} VIP: <code>{'✅ Có' if user.get('vip_active') else '❌ Không'}</code>\n"
        f"│ {ICONS['clock']} Hết hạn: <code>{user.get('vip_expire', 'N/A')}</code>\n"
        f"│ {ICONS['warning']} Banned: <code>{'✅ Có' if user.get('banned') else '❌ Không'}</code>\n"
        f"{stats_msg}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"userinfo:{uid}")

@bot.message_handler(commands=['help'])
def handle_help(message):
    response_text = (
        f"╭─── {ICONS['help']} <b>Hướng Dẫn Sử Dụng</b> ───╮\n"
        f"│ {ICONS['analyze']} /start - Bắt đầu và nhận mã VIP\n"
        f"│ {ICONS['vip']} /code [mã] - Kích hoạt VIP\n"
        f"│ {ICONS['stats']} /stats - Xem thống kê cá nhân\n"
        f"│ {ICONS['history']} /history - Xem lịch sử dự đoán\n"
        f"│ {ICONS['invite']} /invite - Mời bạn bè\n"
        f"│ {ICONS['help']} /help - Hiển thị hướng dẫn\n"
        f"│ {ICONS['user']} /id - Xem thông tin tài khoản\n"
        f"│ {ICONS['info']} Gửi mã MD5 32 ký tự để phân tích\n"
        f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    track_activity(message.from_user.id, "help")

@bot.message_handler(commands=['id'])
def handle_id(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name or "Không có tên"
    status = "❌ Chưa kích hoạt"
    status_icon = ICONS["lock"]
    expire_str = "N/A"
    if uid in users and users[uid].get("vip_active", False):
        expire_str = users[uid].get("vip_expire", "N/A")
        if datetime.now() <= datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S"):
            status = "✅ Đã kích hoạt"
            status_icon = ICONS["vip"]
        else:
            status = "❌ Hết hạn"
            status_icon = ICONS["clock"]
    ref_count = len(referral_db.get(uid, []))
    stats = get_user_stats(uid)
    stats_msg = f"""
│ {ICONS['stats']} Thống kê:\n
│ {ICONS['correct']} Đúng: <code>{stats['correct']}</code>\n
│ {ICONS['wrong']} Sai: <code>{stats['wrong']}</code>\n
│ {ICONS['stats']} Chính xác: <code>{stats['accuracy']:.2f}%</code>
    """ if stats else f"│ {ICONS['info']} Chưa có thống kê"
    response_text = (
        f"╭─── {ICONS['user']} <b>Thông Tin Tài Khoản</b> ───╮\n"
        f"│ {ICONS['user']} Tên: <code>{name}</code>\n"
        f"│ {ICONS['user']} ID: <code>{uid}</code>\n"
        f"│ {status_icon} Trạng thái VIP: <code>{status}</code>\n"
        f"│ {ICONS['clock']} Hết hạn: <code>{expire_str}</code>\n"
        f"│ {ICONS['invite']} Lượt mời: <code>{ref_count}</code>\n"
        f"{stats_msg}\n"
        f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    track_activity(message.from_user.id, "id")

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    stats = get_user_stats(message.from_user.id)
    if not stats:
        response_text = (
            f"╭─── {ICONS['stats']} <b>Thống Kê Cá Nhân</b> ───╮\n"
            f"│ {ICONS['info']} Bạn chưa có thống kê!\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
        return
    response_text = (
        f"╭─── {ICONS['stats']} <b>Thống Kê Cá Nhân</b> ───╮\n"
        f"│ {ICONS['correct']} Dự đoán đúng: <code>{stats['correct']}</code>\n"
        f"│ {ICONS['wrong']} Dự đoán sai: <code>{stats['wrong']}</code>\n"
        f"│ {ICONS['stats']} Tổng dự đoán: <code>{stats['total']}</code>\n"
        f"│ {ICONS['stats']} Tỷ lệ chính xác: <code>{stats['accuracy']:.2f}%</code>\n"
        f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    track_activity(message.from_user.id, "stats")

@bot.message_handler(commands=['history'])
def handle_history(message):
    uid = str(message.from_user.id)
    if uid not in history or not history[uid]:
        response_text = (
            f"╭─── {ICONS['history']} <b>Lịch Sử Dự Đoán</b> ───╮\n"
            f"│ {ICONS['info']} Bạn chưa có lịch sử dự đoán!\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
        return
    user_history = history[uid][-10:]
    history_msg = [f"╭─── {ICONS['history']} <b>Lịch Sử Dự Đoán (Top 10)</b> ───╮"]
    for idx, entry in enumerate(reversed(user_history), 1):
        md5_short = f"{entry['md5'][:4]}...{entry['md5'][-4:]}"
        result = entry.get('prediction', {}).get('final', {}).get('result', 'N/A')
        time_str = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        feedback = ICONS['correct'] if entry.get('is_correct') is True else ICONS['wrong'] if entry.get('is_correct') is False else ""
        history_msg.append(f"│ {idx}. <code>{md5_short}</code> → <b>{result}</b> {feedback} | {time_str}")
    history_msg.append(f"╰────────────────────────────╯")
    response_text = "\n".join(history_msg)
    send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    track_activity(message.from_user.id, "history")

@bot.message_handler(commands=['invite'])
def handle_invite(message):
    user_id = message.from_user.id
    invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    response_text = (
        f"╭─── {ICONS['invite']} <b>Mời Bạn Bè</b> ───╮\n"
        f"│ {ICONS['invite']} Link mời: <code>{invite_link}</code>\n"
        f"│ {ICONS['info']} Mời 1 người để nhận mã VIP 1 ngày!\n"
        f"│ {ICONS['invite']} Tổng lượt mời: <code>{len(referral_db.get(str(user_id), []))}</code>\n"
        f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    track_activity(message.from_user.id, "invite")

@bot.message_handler(commands=['dao'])
def handle_dao(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    global reverse_mode
    reverse_mode = not reverse_mode
    Database.save({'reverse_mode': reverse_mode}, 'config')
    status = "BẬT" if reverse_mode else "TẮT"
    response_text = (
        f"╭─── {ICONS['admin']} <b>Chế Độ Đảo</b> ───╮\n"
        f"│ {ICONS['success']} Chế độ đảo: <code>{status}</code>\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"reverse_mode:{status}")

@bot.message_handler(commands=['taocode'])
def handle_create_code(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    parts = message.text.split()
    if len(parts) != 4:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /taocode [mã] [ngày] [lần]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    code_name = parts[1].upper()
    days = int(parts[2])
    max_uses = int(parts[3])
    create_premium_code(code_name, days, max_uses)
    response_text = (
        f"╭─── {ICONS['admin']} <b>Tạo Mã VIP</b> ───╮\n"
        f"│ {ICONS['success']} Tạo mã thành công!\n"
        f"│ {ICONS['vip']} Mã: <code>{code_name}</code>\n"
        f"│ {ICONS['clock']} Thời hạn: <code>{days} ngày</code>\n"
        f"│ {ICONS['info']} Lượt dùng: <code>{max_uses}</code>\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"create_code:{code_name}")

@bot.message_handler(commands=['listcode'])
def handle_list_codes(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    if not codes_db:
        response_text = (
            f"╭─── {ICONS['admin']} <b>Danh Sách Mã</b> ───╮\n"
            f"│ {ICONS['info']} Chưa có mã nào!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    codes_list = [f"╭─── {ICONS['admin']} <b>Danh Sách Mã</b> ───╮"]
    for code, details in codes_db.items():
        codes_list.append(
            f"""
│ {ICONS['vip']} <b><code>{code}</code></b>\n
│ {ICONS['clock']} {details['days']} ngày | {ICONS['info']} {details['used_count']}/{details['max_uses']}\n
│ {ICONS['time']} Tạo: {details['created_at']}\n
│ {ICONS['user']} {len(details['used_by'])} người dùng
            """
        )
    codes_list.append(f"╰────────────────────────────╯")
    response_text = "\n".join(codes_list)
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, "list_codes")

@bot.message_handler(commands=['kichhoat'])
def handle_kichhoat(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    parts = message.text.split()
    if len(parts) != 3:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /kichhoat [id] [ngày]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    uid = parts[1]
    days = int(parts[2])
    if days <= 0:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Số ngày phải lớn hơn 0!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    exp_date = activate_vip(uid, days)
    try:
        bot.send_message(
            uid,
            f"""
{random.choice(RESPONSE_ICONS)} ╭─── {ICONS['vip']} <b>Kích Hoạt VIP</b> ───╮
│ {ICONS['success']} VIP của bạn đã được kích hoạt!
│ {ICONS['clock']} Thời hạn: <code>{days} ngày</code>
│ {ICONS['time']} Hết hạn: <code>{exp_date}</code>
╰────────────────────────────╯
            """,
            parse_mode="HTML"
        )
    except:
        pass
    response_text = (
        f"╭─── {ICONS['admin']} <b>Kích Hoạt VIP</b> ───╮\n"
        f"│ {ICONS['success']} Kích hoạt VIP thành công!\n"
        f"│ {ICONS['user']} ID: <code>{uid}</code>\n"
        f"│ {ICONS['clock']} Thời hạn: <code>{days} ngày</code>\n"
        f"│ {ICONS['time']} Hết hạn: <code>{exp_date}</code>\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"activate:{uid}")

@bot.message_handler(commands=['huykichhoat'])
def handle_huykichhoat(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    parts = message.text.split()
    if len(parts) != 2:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Cú pháp: /huykichhoat [id]\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    uid = parts[1]
    if uid in users:
        users[uid]["vip_active"] = False
        users[uid].pop("vip_expire", None)
        Database.save(users, 'users')
        try:
            bot.send_message(
                uid,
                f"""
{random.choice(RESPONSE_ICONS)} ╭─── {ICONS['vip']} <b>Hủy VIP</b> ───╮
│ {ICONS['error']} VIP của bạn đã bị hủy!
╰────────────────────────────╯
                """,
                parse_mode="HTML"
            )
        except:
            pass
        response_text = (
            f"╭─── {ICONS['admin']} <b>Hủy VIP</b> ───╮\n"
            f"│ {ICONS['success']} Đã hủy VIP cho ID <code>{uid}</code>\n"
            f"╰────────────────────────────╯"
        )
    else:
        response_text = (
            f"╭─── {ICONS['admin']} <b>Hủy VIP</b> ───╮\n"
            f"│ {ICONS['error']} Không tìm thấy ID <code>{uid}</code>\n"
            f"╰────────────────────────────╯"
        )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, f"deactivate:{uid}")

@bot.message_handler(commands=['send'])
def handle_send(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    content = message.text[6:].strip()
    if not content:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Vui lòng nhập nội dung thông báo!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    total = len(users)
    success = 0
    failed = 0
    reaction_emoji = random.choice(REACTION_EMOJIS)
    bot.send_message(message.chat.id, reaction_emoji, reply_to_message_id=message.message_id)
    bot.send_chat_action(message.chat.id, 'typing')
    time.sleep(random.uniform(0.5, 1.5))
    processing_msg = bot.send_message(
        message.chat.id,
        f"""
{random.choice(RESPONSE_ICONS)} ╭─── {ICONS['broadcast']} <b>Thông Báo</b> ───╮
│ {ICONS['info']} Đang gửi đến <code>{total}</code> người dùng...
╰────────────────────────────╯
        """,
        parse_mode="HTML"
    )
    for uid in users:
        try:
            bot.send_message(
                uid,
                f"""
{random.choice(RESPONSE_ICONS)} ╭─── {ICONS['broadcast']} <b>Thông Báo Hệ Thống</b> ───╮
│ {content}
╰────────────────────────────╯
                """,
                parse_mode="HTML"
            )
            success += 1
        except:
            failed += 1
        time.sleep(0.1)
    bot.edit_message_text(
        f"""
{random.choice(RESPONSE_ICONS)} ╭─── {ICONS['broadcast']} <b>Thông Báo</b> ───╮
│ {ICONS['success']} Gửi thành công: <code>{success}</code>
│ {ICONS['error']} Gửi thất bại: <code>{failed}</code>
│ {ICONS['info']} Tổng người dùng: <code>{total}</code>
╰────────────────────────────╯
        """,
        message.chat.id,
        processing_msg.message_id,
        parse_mode="HTML"
    )
    track_activity(message.from_user.id, f"broadcast:{success}/{failed}")

@bot.message_handler(commands=['thongke'])
def handle_thongke(message):
    if message.from_user.id != ADMIN_ID:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Bạn không có quyền!\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    total_users = len(users)
    vip_users = sum(1 for uid in users if users[uid].get("vip_active", False))
    active_users = sum(1 for uid in activity if 
                       (datetime.now() - datetime.strptime(activity[uid]["last_seen"], "%Y-%m-%d %H:%M:%S")).days < 7)
    total_requests = sum(int(act.get("request_count", 0)) for act in activity.values())
    total_predictions = sum(len(h) for h in history.values())
    correct_predictions = sum(
        sum(1 for entry in history[uid] if entry.get("is_correct") is True)
        for uid in history
    )
    accuracy = correct_predictions / total_predictions * 100 if total_predictions > 0 else 0
    total_ref = sum(len(refs) for refs in referral_db.values())
    response_text = (
        f"╭─── {ICONS['stats']} <b>Thống Kê Hệ Thống</b> ───╮\n"
        f"│ {ICONS['user']} Người dùng:\n"
        f"│ ├ Tổng: <code>{total_users}</code>\n"
        f"│ ├ VIP: <code>{vip_users}</code>\n"
        f"│ └ Active (7 ngày): <code>{active_users}</code>\n"
        f"│ {ICONS['info']} Hoạt động:\n"
        f"│ ├ Tổng yêu cầu: <code>{total_requests}</code>\n"
        f"│ └ Trung bình: <code>{total_requests/max(1, len(activity)):.1f}</code>\n"
        f"│ {ICONS['stats']} Dự đoán:\n"
        f"│ ├ Tổng: <code>{total_predictions}</code>\n"
        f"│ ├ Đúng: <code>{correct_predictions}</code>\n"
        f"│ └ Chính xác: <code>{accuracy:.2f}%</code>\n"
        f"│ {ICONS['invite']} Lượt mời:\n"
        f"│ └ Tổng: <code>{total_ref}</code>\n"
        f"│ {ICONS['time']} Cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"╰────────────────────────────╯"
    )
    send_response_with_reaction_and_typing(message.chat.id, message, response_text)
    track_activity(message.from_user.id, "stats_system")

@bot.message_handler(func=lambda m: re.match(r'^[a-f0-9]{32}$', m.text.strip().lower()))
def handle_md5(message):
    user_id = str(message.from_user.id)
    
    if users.get(user_id, {}).get("banned", False):
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Tài khoản của bạn đã bị cấm!\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text)
        return
    
    if not is_vip_active(message.from_user.id):
        response_text = (
            f"╭─── {ICONS['lock']} <b>Yêu Cầu VIP</b> ───╮\n"
            f"│ {ICONS['info']} Chức năng này chỉ dành cho VIP!\n"
            f"│ {ICONS['vip']} Nhận VIP miễn phí:\n"
            f"│ ├ 1. Dùng /start\n"
            f"│ ├ 2. Tham gia nhóm\n"
            f"│ └ 3. Nhận mã VIP 7 ngày\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
        return
    
    needs_feedback, pending_md5 = check_feedback_status(user_id)
    if needs_feedback:
        response_text = (
            f"╭─── {ICONS['warning']} <b>Phản Hồi</b> ───╮\n"
            f"│ {ICONS['warning']} Vui lòng phản hồi dự đoán trước đó!\n"
            f"│ {ICONS['lock']} MD5: <code>{pending_md5[:8]}...{pending_md5[-8:]}</code>\n"
            f"│ {ICONS['info']} Nhấn nút để đánh giá:\n"
            f"╰────────────────────────────╯"
        )
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(f"{ICONS['correct']} Đúng", callback_data=f"correct_{pending_md5}"),
            types.InlineKeyboardButton(f"{ICONS['wrong']} Sai", callback_data=f"wrong_{pending_md5}")
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, markup)
        return
    
    try:
        md5_hash = message.text.strip().lower()
        analysis = MD5Analyzer.hyper_ai_engine(md5_hash)
        result_msg = UserInterface.create_result_message(md5_hash, analysis)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"{ICONS['correct']} Đúng", callback_data=f"correct_{md5_hash}"),
            types.InlineKeyboardButton(f"{ICONS['wrong']} Sai", callback_data=f"wrong_{md5_hash}")
        )
        reaction_emoji = random.choice(REACTION_EMOJIS)
        bot.send_message(message.chat.id, reaction_emoji, reply_to_message_id=message.message_id)
        bot.send_chat_action(message.chat.id, 'typing')
        time.sleep(random.uniform(0.5, 1.5))
        random_icon = random.choice(RESPONSE_ICONS)
        bot.send_message(
            message.chat.id,
            f"{random_icon} {result_msg}",
            parse_mode="HTML",
            reply_markup=markup,
            reply_to_message_id=message.message_id
        )
        save_prediction(message.from_user.id, md5_hash, analysis)
        track_activity(message.from_user.id, "analyze_md5")
    except Exception as e:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi Phân Tích</b> ───╮\n"
            f"│ {ICONS['error']} Mã MD5 không hợp lệ (yêu cầu 32 ký tự hex)!\n"
            f"│ {ICONS['info']} Ví dụ: <code>5d41402abc4b2a76b9719d911017c592</code>\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith(('correct_', 'wrong_')))
def handle_feedback(call):
    reaction_emoji = random.choice(REACTION_EMOJIS)
    bot.send_message(call.message.chat.id, reaction_emoji, reply_to_message_id=call.message.message_id)
    bot.send_chat_action(call.message.chat.id, 'typing')
    time.sleep(random.uniform(0.5, 1.5))
    
    action, md5_hash = call.data.split('_', 1)
    is_correct = action == "correct"
    user_id = str(call.from_user.id)
    for entry in history.get(user_id, []):
        if entry["md5"] == md5_hash and entry.get("awaiting_feedback"):
            entry["is_correct"] = is_correct
            entry["awaiting_feedback"] = False
            Database.save(history, 'history')
            break
    bot.answer_callback_query(call.id, "Phản hồi đã được ghi nhận!")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    random_icon = random.choice(RESPONSE_ICONS)
    response_text = (
        f"╭─── {ICONS['success']} <b>Phản Hồi</b> ───╮\n"
        f"│ {ICONS['success']} Phản hồi đã được ghi nhận!\n"
        f"│ {ICONS['lock']} MD5: <code>{md5_hash[:8]}...{md5_hash[-8:]}</code>\n"
        f"│ {ICONS['info']} Đánh giá: <b>{'Đúng' if is_correct else 'Sai'}</b>\n"
        f"╰────────────────────────────╯"
    )
    bot.send_message(
        call.message.chat.id,
        f"{random_icon} {response_text}",
        parse_mode="HTML",
        reply_markup=UserInterface.create_inline_menu()
    )
    track_activity(call.from_user.id, f"feedback:{'correct' if is_correct else 'wrong'}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
def handle_menu_callback(call):
    reaction_emoji = random.choice(REACTION_EMOJIS)
    bot.send_message(call.message.chat.id, reaction_emoji, reply_to_message_id=call.message.message_id)
    bot.send_chat_action(call.message.chat.id, 'typing')
    time.sleep(random.uniform(0.5, 1.5))
    
    action = call.data.split('_')[1]
    if action == "analyze":
        response_text = (
            f"╭─── {ICONS['analyze']} <b>Phân Tích MD5</b> ───╮\n"
            f"│ {ICONS['info']} Gửi mã MD5 32 ký tự để phân tích\n"
            f"│ {ICONS['info']} Ví dụ: <code>5d41402abc4b2a76b9719d911017c592</code>\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
    elif action == "vip":
        uid = str(call.from_user.id)
        status = "❌ Chưa kích hoạt"
        status_icon = ICONS["lock"]
        expire_str = "N/A"
        if uid in users and users[uid].get("vip_active", False):
            expire_str = users[uid].get("vip_expire", "N/A")
            if datetime.now() <= datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S"):
                status = "✅ Đã kích hoạt"
                status_icon = ICONS["vip"]
            else:
                status = "❌ Hết hạn"
                status_icon = ICONS["clock"]
        response_text = (
            f"╭─── {ICONS['vip']} <b>Thông Tin VIP</b> ───╮\n"
            f"│ {ICONS['user']} ID: <code>{uid}</code>\n"
            f"│ {status_icon} Trạng thái: <code>{status}</code>\n"
            f"│ {ICONS['clock']} Hết hạn: <code>{expire_str}</code>\n"
            f"│ {ICONS['invite']} Lượt mời: <code>{len(referral_db.get(uid, []))}</code>\n"
            f"│ {ICONS['info']} Kích hoạt VIP: /code [mã]\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
    elif action == "stats":
        stats = get_user_stats(call.from_user.id)
        if not stats:
            response_text = (
                f"╭─── {ICONS['stats']} <b>Thống Kê Cá Nhân</b> ───╮\n"
                f"│ {ICONS['info']} Bạn chưa có thống kê!\n"
                f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
                f"╰────────────────────────────╯"
            )
            send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
        else:
            response_text = (
                f"╭─── {ICONS['stats']} <b>Thống Kê Cá Nhân</b> ───╮\n"
                f"│ {ICONS['correct']} Dự đoán đúng: <code>{stats['correct']}</code>\n"
                f"│ {ICONS['wrong']} Dự đoán sai: <code>{stats['wrong']}</code>\n"
                f"│ {ICONS['stats']} Tổng dự đoán: <code>{stats['total']}</code>\n"
                f"│ {ICONS['stats']} Tỷ lệ chính xác: <code>{stats['accuracy']:.2f}%</code>\n"
                f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
                f"╰────────────────────────────╯"
            )
            send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
    elif action == "history":
        uid = str(call.from_user.id)
        if uid not in history or not history[uid]:
            response_text = (
                f"╭─── {ICONS['history']} <b>Lịch Sử Dự Đoán</b> ───╮\n"
                f"│ {ICONS['info']} Bạn chưa có lịch sử dự đoán!\n"
                f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
                f"╰────────────────────────────╯"
            )
            send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
        else:
            user_history = history[uid][-10:]
            history_msg = [f"╭─── {ICONS['history']} <b>Lịch Sử Dự Đoán (Top 10)</b> ───╮"]
            for idx, entry in enumerate(reversed(user_history), 1):
                md5_short = f"{entry['md5'][:4]}...{entry['md5'][-4:]}"
                result = entry.get('prediction', {}).get('final', {}).get('result', 'N/A')
                time_str = datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
                feedback = ICONS['correct'] if entry.get('is_correct') is True else ICONS['wrong'] if entry.get('is_correct') is False else ""
                history_msg.append(f"│ {idx}. <code>{md5_short}</code> → <b>{result}</b> {feedback} | {time_str}")
            history_msg.append(f"╰────────────────────────────╯")
            response_text = "\n".join(history_msg)
            send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
    elif action == "invite":
        user_id = call.from_user.id
        invite_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        response_text = (
            f"╭─── {ICONS['invite']} <b>Mời Bạn Bè</b> ───╮\n"
            f"│ {ICONS['invite']} Link mời: <code>{invite_link}</code>\n"
            f"│ {ICONS['info']} Mời 1 người để nhận mã VIP 1 ngày!\n"
            f"│ {ICONS['invite']} Tổng lượt mời: <code>{len(referral_db.get(str(user_id), []))}</code>\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
    elif action == "help":
        response_text = (
            f"╭─── {ICONS['help']} <b>Hướng Dẫn Sử Dụng</b> ───╮\n"
            f"│ {ICONS['analyze']} /start - Bắt đầu và nhận mã VIP\n"
            f"│ {ICONS['vip']} /code [mã] - Kích hoạt VIP\n"
            f"│ {ICONS['stats']} /stats - Xem thống kê cá nhân\n"
            f"│ {ICONS['history']} /history - Xem lịch sử dự đoán\n"
            f"│ {ICONS['invite']} /invite - Mời bạn bè\n"
            f"│ {ICONS['help']} /help - Hiển thị hướng dẫn\n"
            f"│ {ICONS['user']} /id - Xem thông tin tài khoản\n"
            f"│ {ICONS['info']} Gửi mã MD5 32 ký tự để phân tích\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(call.message.chat.id, call.message, response_text, UserInterface.create_inline_menu())
    bot.answer_callback_query(call.id)
    track_activity(call.from_user.id, f"menu:{action}")

@bot.callback_query_handler(func=lambda call: call.data == "verify_groups")
def handle_verify_groups(call):
    reaction_emoji = random.choice(REACTION_EMOJIS)
    bot.send_message(call.message.chat.id, reaction_emoji, reply_to_message_id=call.message.message_id)
    bot.send_chat_action(call.message.chat.id, 'typing')
    time.sleep(random.uniform(0.5, 1.5))
    
    missing_groups = check_group_membership(call.from_user.id)
    if missing_groups:
        bot.answer_callback_query(call.id, "Chưa tham gia đủ nhóm!")
        response_text = (
            f"╭─── {ICONS['warning']} <b>Xác Nhận Nhóm</b> ───╮\n"
            f"│ {ICONS['warning']} Vui lòng tham gia các nhóm sau:\n"
            f"│ {''.join(f"👥 {group}\n" for group in missing_groups)}"
            f"╰────────────────────────────╯"
        )
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(f"{ICONS['success']} Thử Lại", callback_data="verify_groups")
        )
        random_icon = random.choice(RESPONSE_ICONS)
        bot.send_message(
            call.message.chat.id,
            f"{random_icon} {response_text}",
            parse_mode="HTML",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "Xác nhận thành công!")
        response_text = (
            f"╭─── {ICONS['success']} <b>Xác Nhận Thành Công</b> ───╮\n"
            f"│ {ICONS['success']} Chúc mừng bạn đã nhận mã VIP!\n"
            f"│ {ICONS['vip']} Mã: <code>{PREMIUM_CODE}</code>\n"
            f"│ {ICONS['info']} Sử dụng: /code {PREMIUM_CODE}\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        random_icon = random.choice(RESPONSE_ICONS)
        bot.send_message(
            call.message.chat.id,
            f"{random_icon} {response_text}",
            parse_mode="HTML",
            reply_markup=UserInterface.create_main_menu()
        )
    track_activity(call.from_user.id, "verify_groups")

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    text = message.text.lower()
    if text == f"{ICONS['analyze']} phân tích md5":
        response_text = (
            f"╭─── {ICONS['analyze']} <b>Phân Tích MD5</b> ───╮\n"
            f"│ {ICONS['info']} Gửi mã MD5 32 ký tự để phân tích\n"
            f"│ {ICONS['info']} Ví dụ: <code>5d41402abc4b2a76b9719d911017c592</code>\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    elif text == f"{ICONS['vip']} thông tin vip":
        uid = str(message.from_user.id)
        status = "❌ Chưa kích hoạt"
        status_icon = ICONS["lock"]
        expire_str = "N/A"
        if uid in users and users[uid].get("vip_active", False):
            expire_str = users[uid].get("vip_expire", "N/A")
            if datetime.now() <= datetime.strptime(expire_str, "%Y-%m-%d %H:%M:%S"):
                status = "✅ Đã kích hoạt"
                status_icon = ICONS["vip"]
            else:
                status = "❌ Hết hạn"
                status_icon = ICONS["clock"]
        response_text = (
            f"╭─── {ICONS['vip']} <b>Thông Tin VIP</b> ───╮\n"
            f"│ {ICONS['user']} ID: <code>{uid}</code>\n"
            f"│ {status_icon} Trạng thái: <code>{status}</code>\n"
            f"│ {ICONS['clock']} Hết hạn: <code>{expire_str}</code>\n"
            f"│ {ICONS['invite']} Lượt mời: <code>{len(referral_db.get(uid, []))}</code>\n"
            f"│ {ICONS['info']} Kích hoạt VIP: /code [mã]\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_inline_menu())
    elif text == f"{ICONS['stats']} thống kê":
        handle_stats(message)
    elif text == f"{ICONS['history']} lịch sử":
        handle_history(message)
    elif text == f"{ICONS['invite']} mời bạn":
        handle_invite(message)
    elif text == f"{ICONS['help']} hỗ trợ":
        handle_help(message)
    else:
        response_text = (
            f"╭─── {ICONS['error']} <b>Lỗi</b> ───╮\n"
            f"│ {ICONS['error']} Lệnh không hợp lệ!\n"
            f"│ {ICONS['info']} Gửi mã MD5 32 ký tự hoặc dùng /help\n"
            f"│ {ICONS['help']} Liên hệ hỗ trợ: {SUPPORT_CONTACT}\n"
            f"╰────────────────────────────╯"
        )
        send_response_with_reaction_and_typing(message.chat.id, message, response_text, UserInterface.create_main_menu())
    track_activity(message.from_user.id, f"text:{message.text[:20]}")

# ==============================================
# KHỞI CHẠY HỆ THỐNG
# ==============================================
if __name__ == "__main__":
    if PREMIUM_CODE not in codes_db:
        create_premium_code(PREMIUM_CODE, 7, 999999)
    
    print("🟢 Hệ thống đang khởi động...")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"🔴 Lỗi hệ thống: {e}")
    finally:
        Database.save(users, 'users')
        Database.save(history, 'history')
        Database.save(activity, 'activity')
        Database.save(codes_db, 'codes')
        Database.save(referral_db, 'referral')
        Database.save({'reverse_mode': reverse_mode}, 'config')