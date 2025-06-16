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
import asyncio

# ==============================================
# CẤU HÌNH HỆ THỐNG
# ==============================================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ BOT_TOKEN chưa được thiết lập!")
ADMIN_ID = 7780640154
LIEN_HE_HO_TRO = "@huydev"
NHOM_YEU_CAU = ["@techtitansteam"]
MA_VIP = "VIP7NGAYMIENPHI"
TEN_BOT = "botmd5v2pro_bot"
SERVER_TRANG_THAI = True  # True: Bật, False: Tắt

bot = telebot.TeleBot(TOKEN)

# Biểu tượng phản hồi động
PHAN_HOI_EMOJI = ["🌌", "🚀", "🪐", "⭐", "💫"]

# Biểu tượng giao diện hiện đại
BIỂU_TƯỢNG = {
    "thanh_cong": "✅", "loi": "❌", "thong_tin": "ℹ️", "canh_bao": "⚠️", "vip": "💎",
    "khoa": "🔒", "mo_khoa": "🔓", "dong_ho": "⏳", "thong_ke": "📊", "lich_su": "📜",
    "nguoi_dung": "👤", "quan_tri": "🛡️", "phat_tin": "📡", "moi_ban": "📩", "nhom": "👥",
    "tai": "🎰", "xiu": "🎲", "dong_co": "⚙️", "rủi_ro": "🚨", "thoi_gian": "⏰",
    "dung": "✔️", "sai": "❌", "phan_tich": "🔍", "moi": "📬", "tro_giup": "🆘"
}

# ==============================================
# QUẢN LÝ CƠ SỞ DỮ LIỆU
# ==============================================
class CoSoDuLieu:
    @staticmethod
    def tai(filename):
        try:
            with open(f'{filename}.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def luu(data, filename):
        try:
            with open(f'{filename}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Lỗi lưu {filename}: {e}")

# Khởi tạo cơ sở dữ liệu
nguoi_dung = CoSoDuLieu.tai('nguoi_dung')
lich_su = CoSoDuLieu.tai('lich_su')
hoat_dong = CoSoDuLieu.tai('hoat_dong')
ma_vip_db = CoSoDuLieu.tai('ma_vip')
moi_ban_db = CoSoDuLieu.tai('moi_ban')
cau_hinh_db = CoSoDuLieu.tai('cau_hinh')
che_do_dao = cau_hinh_db.get('che_do_dao', False)

# ==============================================
# TIỆN ÍCH HỆ THỐNG
# ==============================================
async def kiem_tra_tham_gia_nhom(user_id):
    nhom_thieu = []
    cache_key = f"nhom_{user_id}"
    cache = CoSoDuLieu.tai('cache_nhom').get(cache_key, {})
    thoi_gian_cache = cache.get('thoi_gian', 0)
    
    if time.time() - thoi_gian_cache < 120:  # Cache 120 giây
        return cache.get('nhom_thieu', NHOM_YEU_CAU)
    
    for nhom in NHOM_YEU_CAU:
        for attempt in range(3):  # Thử lại 3 lần
            try:
                thanh_vien = await bot.get_chat_member(nhom, user_id)
                if thanh_vien.status not in ['member', 'administrator', 'creator']:
                    nhom_thieu.append(nhom)
                break
            except telebot.apihelper.ApiTelegramException as e:
                if "rate limit" in str(e).lower():
                    await asyncio.sleep(1)
                    continue
                nhom_thieu.append(nhom)
                break
    
    cache_nhom = CoSoDuLieu.tai('cache_nhom')
    cache_nhom[cache_key] = {
        'nhom_thieu': nhom_thieu,
        'thoi_gian': time.time()
    }
    CoSoDuLieu.luu(cache_nhom, 'cache_nhom')
    
    return nhom_thieu

def kich_hoat_vip(uid, days=7, mo_rong=False):
    uid = str(uid)
    nguoi_dung[uid] = nguoi_dung.get(uid, {})
    if mo_rong and nguoi_dung[uid].get("vip_het_han"):
        try:
            het_han_hien_tai = datetime.strptime(nguoi_dung[uid]["vip_het_han"], "%Y-%m-%d %H:%M:%S")
            ngay_het_han = (max(datetime.now(), het_han_hien_tai) + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        except:
            ngay_het_han = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        ngay_het_han = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    nguoi_dung[uid]["vip_kich_hoat"] = True
    nguoi_dung[uid]["vip_het_han"] = ngay_het_han
    nguoi_dung[uid]["lan_hoat_dong_cuoi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    CoSoDuLieu.luu(nguoi_dung, 'nguoi_dung')
    return ngay_het_han

def tao_ma_vip(ma_ten, days, so_lan_su_dung_toi_da=1):
    ma_vip_db[ma_ten] = {
        "days": days,
        "so_lan_su_dung_toi_da": so_lan_su_dung_toi_da,
        "so_lan_su_dung": 0,
        "ngay_tao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nguoi_su_dung": []
    }
    CoSoDuLieu.luu(ma_vip_db, 'ma_vip')
    return ma_vip_db[ma_ten]

def su_dung_ma_vip(ma_ten, user_id):
    if ma_ten not in ma_vip_db:
        return False, f"{BIỂU_TƯỢNG['loi']} Mã không hợp lệ!"
    ma = ma_vip_db[ma_ten]
    user_id = str(user_id)
    if user_id in ma["nguoi_su_dung"]:
        return False, f"{BIỂU_TƯỢNG['canh_bao']} Bạn đã dùng mã này rồi!"
    if ma["so_lan_su_dung"] >= ma["so_lan_su_dung_toi_da"]:
        return False, f"{BIỂU_TƯỢNG['dong_ho']} Mã đã hết lượt sử dụng!"
    
    mo_rong = user_id in nguoi_dung and nguoi_dung[user_id].get("vip_kich_hoat")
    ngay_het_han = kich_hoat_vip(user_id, ma["days"], mo_rong)
    ma["so_lan_su_dung"] += 1
    ma["nguoi_su_dung"].append(user_id)
    CoSoDuLieu.luu(ma_vip_db, 'ma_vip')
    return True, f"{BIỂU_TƯỢNG['thanh_cong']} Kích hoạt VIP {ma['days']} ngày!\n{BIỂU_TƯỢNG['dong_ho']} Hết hạn: {ngay_het_han}"

def theo_doi_hoat_dong(user_id, hanh_dong):
    user_id = str(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hoat_dong[user_id] = hoat_dong.get(user_id, {
        "lan_dau_xem": now,
        "lan_cuoi_xem": now,
        "so_lan_yeu_cau": 0,
        "hanh_dong": []
    })
    hoat_dong[user_id]["lan_cuoi_xem"] = now
    hoat_dong[user_id]["so_lan_yeu_cau"] += 1
    hoat_dong[user_id]["hanh_dong"].append(hanh_dong)
    CoSoDuLieu.luu(hoat_dong, 'hoat_dong')

def tao_ma_moi_ban(user_id):
    ma = f"MOI1NGAY_{user_id}_{int(time.time())}"
    tao_ma_vip(ma, 1, 1)
    return ma

def theo_doi_moi_ban(nguoi_moi_id, nguoi_duoc_moi_id):
    nguoi_moi_id = str(nguoi_moi_id)
    nguoi_duoc_moi_id = str(nguoi_duoc_moi_id)
    
    if nguoi_moi_id not in moi_ban_db:
        moi_ban_db[nguoi_moi_id] = []
    
    if nguoi_duoc_moi_id not in moi_ban_db[nguoi_moi_id]:
        moi_ban_db[nguoi_moi_id].append(nguoi_duoc_moi_id)
        CoSoDuLieu.luu(moi_ban_db, 'moi_ban')
        
        ma_thuong = tao_ma_moi_ban(nguoi_moi_id)
        try:
            bot.send_message(
                nguoi_moi_id,
                f"""
{BIỂU_TƯỢNG['thanh_cong']} <b>Mời Bạn Thành Công!</b>
{BIỂU_TƯỢNG['nguoi_dung']} Bạn đã mời ID {nguoi_duoc_moi_id}!
{BIỂU_TƯỢNG['moi']} Mã thưởng: <code>{ma_thuong}</code>
{BIỂU_TƯỢNG['thong_tin']} Dùng: /ma {ma_thuong}
                """,
                parse_mode="HTML"
            )
        except:
            pass

def kiem_tra_vip_kich_hoat(user_id):
    user_id = str(user_id)
    if user_id in nguoi_dung and nguoi_dung[user_id].get("vip_kich_hoat", False):
        het_han = nguoi_dung[user_id].get("vip_het_han", "N/A")
        try:
            if datetime.now() <= datetime.strptime(het_han, "%Y-%m-%d %H:%M:%S"):
                return True
        except:
            return False
    return False

# ==============================================
# ĐỘNG CƠ PHÂN TÍCH MD5
# ==============================================
class PhanTichMD5:
    @staticmethod
    def dong_co_sieu_tri_tue(md5_hash):
        md5_hash = md5_hash.lower().strip()
        if len(md5_hash) != 32 or not re.match(r'^[a-f0-9]{32}$', md5_hash):
            raise ValueError("Mã MD5 không hợp lệ!")
        
        hex_bytes = [int(md5_hash[i:i+2], 16) for i in range(0, len(md5_hash), 2)]
        byte_array = np.array(hex_bytes)
        tong = sum(hex_bytes)

        # Thuật toán 1: Hyper-AI Engine
        tong_luong_tu = sum(byte_array[i] * math.cos(i * math.pi/16) for i in range(16))
        diem_neural = sum(byte_array[i] * (1.618 ** (i % 5)) for i in range(16))
        chieu_phân_hình = sum(byte_array[i] * (1 + math.sqrt(5)) / 2 for i in range(16))
        diem1 = (tong_luong_tu + diem_neural + chieu_phân_hình) % 20
        ket_qua1 = "TÀI" if diem1 < 10 else "XỈU"
        xac_suat1 = 95 - abs(diem1 - 10) * 4.5 if diem1 < 10 else 50 + (diem1 - 10) * 4.5

        # Thuật toán 2: Diamond Engine
        nums = [int(c, 16) for c in md5_hash]
        trung_binh = sum(nums) / 32
        so_chan = sum(1 for n in nums if n % 2 == 0)
        tren_8 = sum(1 for n in nums if n > 8)
        diem2 = (1 if trung_binh > 7.5 else 0) + (1 if so_chan > 16 else 0) + (1 if tren_8 >= 10 else 0)
        ket_qua2 = "TÀI" if diem2 >= 2 else "XỈU"
        xac_suat2 = 90 if diem2 == 3 else 75 if diem2 == 2 else 60
        xac_suat2 = xac_suat2 if ket_qua2 == "TÀI" else 100 - xac_suat2

        # Thuật toán 3: Titans Tech
        x = int(md5_hash, 16)
        ket_qua3 = "TÀI" if x % 2 == 0 else "XỈU"
        xac_suat3 = 75.0

        # Kết quả cuối
        trong_so = [0.5, 0.3, 0.2]
        diem_cuoi = (diem1 * trong_so[0] + diem2 * 5 * trong_so[1] + (0 if ket_qua3 == "XỈU" else 10) * trong_so[2])
        ket_qua_cuoi = "TÀI" if diem_cuoi < 10 else "XỈU"
        xac_suat_cuoi = (xac_suat1 * trong_so[0] + xac_suat2 * trong_so[1] + xac_suat3 * trong_so[2])
        
        if che_do_dao:
            ket_qua_cuoi = "XỈU" if ket_qua_cuoi == "TÀI" else "TÀI"
            xac_suat_cuoi = 100 - xac_suat_cuoi

        muc_do_rui_ro = "THẤP" if xac_suat_cuoi > 80 else "TRUNG BÌNH" if xac_suat_cuoi > 60 else "CAO"
        
        return {
            "tong": tong,
            "thuattoan1": {"ket_qua": ket_qua1, "xac_suat": f"{xac_suat1:.1f}%", "diem": diem1},
            "thuattoan2": {"ket_qua": ket_qua2, "xac_suat": f"{xac_suat2:.1f}%", "diem": diem2},
            "thuattoan3": {"ket_qua": ket_qua3, "xac_suat": f"{xac_suat3:.1f}%", "diem": x % 2},
            "cuoi": {"ket_qua": ket_qua_cuoi, "xac_suat": f"{xac_suat_cuoi:.1f}%"},
            "rui_ro": muc_do_rui_ro,
            "thoi_gian": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "da_dao": che_do_dao
        }

# ==============================================
# GIAO DIỆN NGƯỜI DÙNG (THIẾT KẾ VŨ TRỤ)
# ==============================================
class GiaoDienNguoiDung:
    @staticmethod
    def tao_menu_chinh():
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton(f"{BIỂU_TƯỢNG['phan_tich']} Phân Tích MD5"),
            types.KeyboardButton(f"{BIỂU_TƯỢNG['vip']} Trạng Thái VIP")
        )
        markup.add(
            types.KeyboardButton(f"{BIỂU_TƯỢNG['thong_ke']} Thống Kê"),
            types.KeyboardButton(f"{BIỂU_TƯỢNG['lich_su']} Lịch Sử")
        )
        markup.add(
            types.KeyboardButton(f"{BIỂU_TƯỢNG['moi_ban']} Mời Bạn"),
            types.KeyboardButton(f"{BIỂU_TƯỢNG['tro_giup']} Trợ Giúp")
        )
        return markup

    @staticmethod
    def tao_menu_tuong_tac():
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['tro_giup']} Trợ Giúp", callback_data="menu_tro_giup"),
            types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['phan_tich']} Phân Tích", callback_data="menu_phan_tich")
        )
        return markup

    @staticmethod
    def tao_bao_cao_phan_tich(md5_input, phan_tich):
        che_do = "ĐẢO" if phan_tich["da_dao"] else "BÌNH THƯỜNG"
        return (
            f"🌌 <b>Hyper-AI Analysis</b> 🌌\n"
            f"═══ Thông Tin Phân Tích ═══\n"
            f"🪐 Version: Siêu Trí Tuệ 7 Pro\n"
            f"🔒 MD5: <code>{md5_input[:8]}...{md5_input[-8:]}</code>\n"
            f"📊 Tổng HEX: <code>{phan_tich['tong']}</code>\n"
            f"⚙️ Chế độ: <code>{che_do}</code>\n"
            f"═══ Kết Quả Thuật Toán ═══\n"
            f"🌟 <b>Hyper-AI Engine</b>\n"
            f"   {BIỂU_TƯỢNG['tai' if phan_tich['thuattoan1']['ket_qua'] == 'TÀI' else 'xiu']} Dự đoán: <b>{phan_tich['thuattoan1']['ket_qua']}</b>\n"
            f"   📈 Xác suất: <code>{phan_tich['thuattoan1']['xac_suat']}</code>\n"
            f"💎 <b>Diamond Engine</b>\n"
            f"   {BIỂU_TƯỢNG['tai' if phan_tich['thuattoan2']['ket_qua'] == 'TÀI' else 'xiu']} Dự đoán: <b>{phan_tich['thuattoan2']['ket_qua']}</b>\n"
            f"   📈 Xác suất: <code>{phan_tich['thuattoan2']['xac_suat']}</code>\n"
            f"🛸 <b>Titans Tech</b>\n"
            f"   {BIỂU_TƯỢNG['tai' if phan_tich['thuattoan3']['ket_qua'] == 'TÀI' else 'xiu']} Dự đoán: <b>{phan_tich['thuattoan3']['ket_qua']}</b>\n"
            f"   📈 Xác suất: <code>{phan_tich['thuattoan3']['xac_suat']}</code>\n"
            f"═══ Điểm Thuật Toán ═══\n"
            f"🌟 Hyper-AI: <code>{phan_tich['thuattoan1']['diem']:.2f}</code>\n"
            f"💎 Diamond: <code>{phan_tich['thuattoan2']['diem']:.2f}</code>\n"
            f"🛸 Titans: <code>{phan_tich['thuattoan3']['diem']:.2f}</code>\n"
            f"═══ Kết Quả Cuối ═══\n"
            f"🎯 Dự đoán: <b>{phan_tich['cuoi']['ket_qua']}</b>\n"
            f"📈 Độ tin cậy: <code>{phan_tich['cuoi']['xac_suat']}</code>\n"
            f"🚨 Rủi ro: <b>{phan_tich['rui_ro']}</b>\n"
            f"⏰ Thời gian: {phan_tich['thoi_gian']}"
        )

# ==============================================
# QUẢN LÝ DỮ LIỆU
# ==============================================
def luu_du_doan(user_id, md5, phan_tich, la_dung=None):
    user_id = str(user_id)
    lich_su[user_id] = lich_su.get(user_id, [])
    lich_su[user_id].append({
        "md5": md5,
        "du_doan": phan_tich,
        "thoi_gian": phan_tich["thoi_gian"],
        "la_dung": la_dung,
        "cho_phan_hoi": True if la_dung is None else False
    })
    if len(lich_su[user_id]) > 100:
        lich_su[user_id] = lich_su[user_id][-100:]
    CoSoDuLieu.luu(lich_su, 'lich_su')

def kiem_tra_trang_thai_phan_hoi(user_id):
    user_id = str(user_id)
    if user_id in lich_su:
        for muc in lich_su[user_id]:
            if muc.get("cho_phan_hoi", False):
                return True, muc["md5"]
    return False, None

def lay_thong_ke_nguoi_dung(user_id):
    user_id = str(user_id)
    if user_id not in lich_su or not lich_su[user_id]:
        return None
    lich_su_nguoi_dung = lich_su[user_id]
    tong = len(lich_su_nguoi_dung)
    dung = sum(1 for muc in lich_su_nguoi_dung if muc.get("la_dung") is True)
    sai = sum(1 for muc in lich_su_nguoi_dung if muc.get("la_dung") is False)
    do_chinh_xac = dung / tong * 100 if tong > 0 else 0
    return {
        "tong": tong,
        "dung": dung,
        "sai": sai,
        "do_chinh_xac": do_chinh_xac
    }

# ==============================================
# PHẢN HỒI ĐỘNG
# ==============================================
async def gui_phan_hoi_voi_emoji(chat_id, tin_nhan, noi_dung, reply_markup=None):
    tin_nhan_bieu_tuong = await bot.send_message(chat_id, random.choice(PHAN_HOI_EMOJI), reply_to_message_id=tin_nhan.message_id)
    await bot.send_chat_action(chat_id, 'typing')
    await asyncio.sleep(random.uniform(0.5, 1.5))
    random_emoji = random.choice(PHAN_HOI_EMOJI)
    await bot.send_message(
        chat_id,
        f"{random_emoji} {noi_dung}",
        parse_mode="HTML",
        reply_markup=reply_markup,
        reply_to_message_id=tin_nhan.message_id
    )
    await asyncio.sleep(2)
    try:
        await bot.delete_message(chat_id, tin_nhan_bieu_tuong.message_id)
    except:
        pass

def gui_phan_hoi_dong_bo(chat_id, tin_nhan, noi_dung, reply_markup=None):
    asyncio.run(gui_phan_hoi_voi_emoji(chat_id, tin_nhan, noi_dung, reply_markup))

# ==============================================
# XỬ LÝ LỆNH
# ==============================================
@bot.message_handler(commands=['start'])
def xu_ly_bat_dau(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    
    if len(tin_nhan.text.split()) > 1:
        nguoi_moi_id = tin_nhan.text.split()[1]
        if nguoi_moi_id != str(tin_nhan.from_user.id):
            theo_doi_moi_ban(nguoi_moi_id, tin_nhan.from_user.id)
    
    ten = tin_nhan.from_user.first_name or "Nhà Thám Hiểm"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['nhom']} Xác Minh Nhóm", callback_data="xác_minh_nhóm"))
    noi_dung = (
        f"🌌 <b>Chào {ten}!</b> 🌌\n"
        f"═══ Bắt Đầu Hành Trình ═══\n"
        f"🚀 Tham gia nhóm để nhận <b>VIP 7 ngày miễn phí</b>!\n"
        f"{''.join(f'{BIỂU_TƯỢNG['nhom']} {nhom}\n' for nhom in NHOM_YEU_CAU)}"
        f"🪐 Nhấn nút để xác minh và nhận mã!"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, markup)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "bắt_đầu")

@bot.message_handler(commands=['ma'])
def xu_ly_ma(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    
    phan = tin_nhan.text.split()
    if len(phan) != 2:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /ma [mã]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    thanh_cong, thong_bao = su_dung_ma_vip(phan[1].upper(), tin_nhan.from_user.id)
    noi_dung = (
        f"🌌 <b>Kích Hoạt VIP</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{thong_bao}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"sử_dụng_mã:{phan[1]}")

@bot.message_handler(commands=['admin'])
def xu_ly_admin(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    noi_dung = (
        f"🌌 <b>Admin Control Panel</b> 🌌\n"
        f"═══ Lệnh Quản Trị ═══\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /cam [user_id] - Cấm người dùng\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /bo_cam [user_id] - Bỏ cấm người dùng\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /thong_tin_nguoi_dung [user_id] - Xem thông tin người dùng\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /kich_hoat [id] [ngày] - Kích hoạt VIP\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /huy_kich_hoat [id] - Hủy VIP\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /tao_ma [mã] [ngày] [lượt] - Tạo mã VIP\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /danh_sach_ma - Xem danh sách mã VIP\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /gui [thông_điệp] - Phát tin nhắn\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /thong_ke - Thống kê hệ thống\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /dao - Bật/tắt chế độ đảo\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /danh_sach_nguoi_dung - Xem danh sách người dùng\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /xoa_lich_su [user_id] - Xóa lịch sử người dùng\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /onserver - Bật bot cho tất cả\n"
        f"{BIỂU_TƯỢNG['quan_tri']} /stopserver - Tắt bot với người dùng thường"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "admin")

@bot.message_handler(commands=['onserver'])
def xu_ly_onserver(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    global SERVER_TRANG_THAI
    SERVER_TRANG_THAI = True
    cau_hinh_db['server_trang_thai'] = SERVER_TRANG_THAI
    CoSoDuLieu.luu(cau_hinh_db, 'cau_hinh')
    noi_dung = (
        f"🌌 <b>Server Status</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{BIỂU_TƯỢNG['thanh_cong']} Bot đã được bật cho tất cả người dùng!"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "bật_server")

@bot.message_handler(commands=['stopserver'])
def xu_ly_stopserver(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    global SERVER_TRANG_THAI
    SERVER_TRANG_THAI = False
    cau_hinh_db['server_trang_thai'] = SERVER_TRANG_THAI
    CoSoDuLieu.luu(cau_hinh_db, 'cau_hinh')
    noi_dung = (
        f"🌌 <b>Server Status</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{BIỂU_TƯỢNG['thanh_cong']} Bot đã tắt với người dùng thường!\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Admin vẫn có thể sử dụng."
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "tắt_server")

@bot.message_handler(commands=['quan_tri'])
def xu_ly_quan_tri(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    noi_dung = (
        f"🌌 <b>Admin Control Panel</b> 🌌\n"
        f"═══ Lệnh Quản Trị ═══\n"
        f"{BIỂU_TƯỢNG['quan_tri']} Dùng /admin để xem danh sách lệnh đầy đủ!"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "quan_tri")

@bot.message_handler(commands=['cam'])
def xu_ly_cam(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 2:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /cam [user_id]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = phan[1]
    nguoi_dung[uid] = nguoi_dung.get(uid, {})
    nguoi_dung[uid]["bi_cam"] = True
    CoSoDuLieu.luu(nguoi_dung, 'nguoi_dung')
    try:
        bot.send_message(uid, f"🌌 <b>Bị Cấm!</b> 🌌\n═══ Thông Báo ═══\n{BIỂU_TƯỢNG['loi']} Tài khoản của bạn đã bị cấm!", parse_mode="HTML")
    except:
        pass
    noi_dung = (
        f"🌌 <b>Quản Lý Người Dùng</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{BIỂU_TƯỢNG['thanh_cong']} Đã cấm ID <code>{uid}</code>"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"cấm:{uid}")

@bot.message_handler(commands=['bo_cam'])
def xu_ly_bo_cam(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 2:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /bo_cam [user_id]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = phan[1]
    if uid in nguoi_dung:
        nguoi_dung[uid]["bi_cam"] = False
        CoSoDuLieu.luu(nguoi_dung, 'nguoi_dung')
        try:
            bot.send_message(uid, f"🌌 <b>Đã Bỏ Cấm!</b> 🌌\n═══ Thông Báo ═══\n{BIỂU_TƯỢNG['thanh_cong']} Tài khoản của bạn đã được bỏ cấm!", parse_mode="HTML")
        except:
            pass
        noi_dung = (
            f"🌌 <b>Quản Lý Người Dùng</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thanh_cong']} Đã bỏ cấm ID <code>{uid}</code>"
        )
    else:
        noi_dung = (
            f"🌌 <b>Quản Lý Người Dùng</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['loi']} ID <code>{uid}</code> không tồn tại!"
        )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"bỏ_cấm:{uid}")

@bot.message_handler(commands=['thong_tin_nguoi_dung'])
def xu_ly_thong_tin_nguoi_dung(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 2:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /thong_tin_nguoi_dung [user_id]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = phan[1]
    if uid not in nguoi_dung:
        noi_dung = (
            f"🌌 <b>Thông Tin Người Dùng</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['loi']} ID <code>{uid}</code> không tồn tại!"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    nguoi = nguoi_dung[uid]
    thong_ke = lay_thong_ke_nguoi_dung(uid)
    thong_bao_thong_ke = (
        f"{BIỂU_TƯỢNG['thong_ke']} Thống kê:\n"
        f"   {BIỂU_TƯỢNG['dung']} Đúng: <code>{thong_ke['dung']}</code>\n"
        f"   {BIỂU_TƯỢNG['sai']} Sai: <code>{thong_ke['sai']}</code>\n"
        f"   {BIỂU_TƯỢNG['thong_ke']} Độ chính xác: <code>{thong_ke['do_chinh_xac']:.2f}%</code>"
    ) if thong_ke else f"{BIỂU_TƯỢNG['thong_tin']} Không có thống kê"
    noi_dung = (
        f"🌌 <b>User Info</b> 🌌\n"
        f"═══ Thông Tin Người Dùng ═══\n"
        f"{BIỂU_TƯỢNG['nguoi_dung']} ID: <code>{uid}</code>\n"
        f"{BIỂU_TƯỢNG['vip']} VIP: <code>{'Kích hoạt' if nguoi.get('vip_kich_hoat') else 'Không hoạt động'}</code>\n"
        f"{BIỂU_TƯỢNG['dong_ho']} Hết hạn: <code>{nguoi.get('vip_het_han', 'N/A')}</code>\n"
        f"{BIỂU_TƯỢNG['khoa']} Bị cấm: <code>{'Có' if nguoi.get('bi_cam') else 'Không'}</code>\n"
        f"{thong_bao_thong_ke}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"thông_tin_nguoi_dung:{uid}")

@bot.message_handler(commands=['danh_sach_nguoi_dung'])
def xu_ly_danh_sach_nguoi_dung(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    if not nguoi_dung:
        noi_dung = (
            f"🌌 <b>User List</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Không tìm thấy người dùng nào!"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    danh_sach = [f"🌌 <b>User List</b> 🌌\n═══ Danh Sách Người Dùng ═══"]
    for uid, chi_tiet in nguoi_dung.items():
        trang_thai_vip = "Kích hoạt" if chi_tiet.get("vip_kich_hoat") else "Không hoạt động"
        trang_thai_cam = "Bị cấm" if chi_tiet.get("bi_cam") else "Hoạt động"
        danh_sach.append(
            f"{BIỂU_TƯỢNG['nguoi_dung']} ID: <code>{uid}</code> | {BIỂU_TƯỢNG['vip']} {trang_thai_vip} | {BIỂU_TƯỢNG['khoa']} {trang_thai_cam}"
        )
    noi_dung = "\n".join(danh_sach)
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "danh_sach_nguoi_dung")

@bot.message_handler(commands=['xoa_lich_su'])
def xu_ly_xoa_lich_su(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 2:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /xoa_lich_su [user_id]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = phan[1]
    if uid in lich_su:
        del lich_su[uid]
        CoSoDuLieu.luu(lich_su, 'lich_su')
        noi_dung = (
            f"🌌 <b>Quản Lý Lịch Sử</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thanh_cong']} Đã xóa lịch sử của ID <code>{uid}</code>"
        )
    else:
        noi_dung = (
            f"🌌 <b>Quản Lý Lịch Sử</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Không tìm thấy lịch sử cho ID <code>{uid}</code>"
        )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"xóa_lịch_sử:{uid}")

@bot.message_handler(commands=['tro_giup'])
def xu_ly_tro_giup(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    noi_dung = (
        f"🌌 <b>Hướng Dẫn Sử Dụng</b> 🌌\n"
        f"═══ Lệnh Người Dùng ═══\n"
        f"{BIỂU_TƯỢNG['phan_tich']} /start - Bắt đầu & nhận VIP\n"
        f"{BIỂU_TƯỢNG['vip']} /ma [mã] - Kích hoạt VIP\n"
        f"{BIỂU_TƯỢNG['thong_ke']} /thong_ke - Xem thống kê cá nhân\n"
        f"{BIỂU_TƯỢNG['lich_su']} /lich_su - Xem lịch sử dự đoán\n"
        f"{BIỂU_TƯỢNG['moi_ban']} /moi - Mời bạn bè\n"
        f"{BIỂU_TƯỢNG['tro_giup']} /tro_giup - Hiển thị hướng dẫn\n"
        f"{BIỂU_TƯỢNG['nguoi_dung']} /id - Xem thông tin tài khoản\n"
        f"{BIỂU_TƯỢNG['phan_tich']} Gửi mã MD5 32 ký tự để phân tích\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
    theo_doi_hoat_dong(tin_nhan.from_user.id, "trợ_giúp")

@bot.message_handler(commands=['id'])
def xu_ly_id(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = str(tin_nhan.from_user.id)
    ten = tin_nhan.from_user.first_name or "Không Tên"
    trang_thai = "Không hoạt động"
    bieu_tuong_trang_thai = BIỂU_TƯỢNG["khoa"]
    het_han_str = "N/A"
    if uid in nguoi_dung and nguoi_dung[uid].get("vip_kich_hoat", False):
        het_han_str = nguoi_dung[uid].get("vip_het_han", "N/A")
        if datetime.now() <= datetime.strptime(het_han_str, "%Y-%m-%d %H:%M:%S"):
            trang_thai = "Kích hoạt"
            bieu_tuong_trang_thai = BIỂU_TƯỢNG["vip"]
        else:
            trang_thai = "Hết hạn"
            bieu_tuong_trang_thai = BIỂU_TƯỢNG["dong_ho"]
    so_lan_moi = len(moi_ban_db.get(uid, []))
    thong_ke = lay_thong_ke_nguoi_dung(uid)
    thong_bao_thong_ke = (
        f"{BIỂU_TƯỢNG['thong_ke']} Thống kê:\n"
        f"   {BIỂU_TƯỢNG['dung']} Đúng: <code>{thong_ke['dung']}</code>\n"
        f"   {BIỂU_TƯỢNG['sai']} Sai: <code>{thong_ke['sai']}</code>\n"
        f"   {BIỂU_TƯỢNG['thong_ke']} Độ chính xác: <code>{thong_ke['do_chinh_xac']:.2f}%</code>"
    ) if thong_ke else f"{BIỂU_TƯỢNG['thong_tin']} Không có thống kê"
    noi_dung = (
        f"🌌 <b>User Profile</b> 🌌\n"
        f"═══ Thông Tin Tài Khoản ═══\n"
        f"{BIỂU_TƯỢNG['nguoi_dung']} Tên: <code>{ten}</code>\n"
        f"{BIỂU_TƯỢNG['nguoi_dung']} ID: <code>{uid}</code>\n"
        f"{bieu_tuong_trang_thai} VIP: <code>{trang_thai}</code>\n"
        f"{BIỂU_TƯỢNG['dong_ho']} Hết hạn: <code>{het_han_str}</code>\n"
        f"{BIỂU_TƯỢNG['moi_ban']} Lượt mời: <code>{so_lan_moi}</code>\n"
        f"{thong_bao_thong_ke}\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
    theo_doi_hoat_dong(tin_nhan.from_user.id, "id")

@bot.message_handler(commands=['thong_ke'])
def xu_ly_thong_ke(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    thong_ke = lay_thong_ke_nguoi_dung(tin_nhan.from_user.id)
    if not thong_ke:
        noi_dung = (
            f"🌌 <b>Personal Stats</b> 🌌\n"
            f"═══ Thống Kê Cá Nhân ═══\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Không có thống kê!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
        return
    noi_dung = (
        f"🌌 <b>Personal Stats</b> 🌌\n"
        f"═══ Thống Kê Cá Nhân ═══\n"
        f"{BIỂU_TƯỢNG['dung']} Đúng: <code>{thong_ke['dung']}</code>\n"
        f"{BIỂU_TƯỢNG['sai']} Sai: <code>{thong_ke['sai']}</code>\n"
        f"{BIỂU_TƯỢNG['thong_ke']} Tổng: <code>{thong_ke['tong']}</code>\n"
        f"{BIỂU_TƯỢNG['thong_ke']} Độ chính xác: <code>{thong_ke['do_chinh_xac']:.2f}%</code>\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
    theo_doi_hoat_dong(tin_nhan.from_user.id, "thống_kê")

@bot.message_handler(commands=['lich_su'])
def xu_ly_lich_su(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = str(tin_nhan.from_user.id)
    if uid not in lich_su or not lich_su[uid]:
        noi_dung = (
            f"🌌 <b>Prediction History</b> 🌌\n"
            f"═══ Lịch Sử Dự Đoán ═══\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Không có lịch sử dự đoán!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
        return
    lich_su_nguoi_dung = lich_su[uid][-10:]
    thong_bao_lich_su = [f"🌌 <b>Prediction History (Top 10)</b> 🌌\n═══ Lịch Sử Dự Đoán ═══"]
    for idx, muc in enumerate(reversed(lich_su_nguoi_dung), 1):
        md5_ngan = f"{muc['md5'][:4]}...{muc['md5'][-4:]}"
        ket_qua = muc.get('du_doan', {}).get('cuoi', {}).get('ket_qua', 'N/A')
        thoi_gian_str = datetime.strptime(muc['thoi_gian'], "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        phan_hoi = BIỂU_TƯỢNG['dung'] if muc.get('la_dung') is True else BIỂU_TƯỢNG['sai'] if muc.get('la_dung') is False else ""
        thong_bao_lich_su.append(f"{idx}. <code>{md5_ngan}</code> → <b>{ket_qua}</b> {phan_hoi} | {thoi_gian_str}")
    noi_dung = "\n".join(thong_bao_lich_su)
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
    theo_doi_hoat_dong(tin_nhan.from_user.id, "lịch_sử")

@bot.message_handler(commands=['moi'])
def xu_ly_moi(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    user_id = tin_nhan.from_user.id
    lien_ket_moi = f"https://t.me/{TEN_BOT}?start={user_id}"
    noi_dung = (
        f"🌌 <b>Invite Friends</b> 🌌\n"
        f"═══ Mời Bạn Bè ═══\n"
        f"{BIỂU_TƯỢNG['moi_ban']} Link mời: <code>{lien_ket_moi}</code>\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Mời 1 bạn nhận VIP 1 ngày!\n"
        f"{BIỂU_TƯỢNG['moi_ban']} Tổng lượt mời: <code>{len(moi_ban_db.get(str(user_id), []))}</code>\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
    theo_doi_hoat_dong(tin_nhan.from_user.id, "mời")

@bot.message_handler(commands=['dao'])
def xu_ly_dao(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    global che_do_dao
    che_do_dao = not che_do_dao
    cau_hinh_db['che_do_dao'] = che_do_dao
    CoSoDuLieu.luu(cau_hinh_db, 'cau_hinh')
    trang_thai = "BẬT" if che_do_dao else "TẮT"
    noi_dung = (
        f"🌌 <b>Reverse Mode</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{BIỂU_TƯỢNG['thanh_cong']} Chế độ đảo: <code>{trang_thai}</code>"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"chế_độ_đảo:{trang_thai}")

@bot.message_handler(commands=['tao_ma'])
def xu_ly_tao_ma(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 4:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /tao_ma [mã] [ngày] [lượt]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    ma_ten = phan[1].upper()
    ngay = int(phan[2])
    so_lan_su_dung_toi_da = int(phan[3])
    tao_ma_vip(ma_ten, ngay, so_lan_su_dung_toi_da)
    noi_dung = (
        f"🌌 <b>Create VIP Code</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{BIỂU_TƯỢNG['thanh_cong']} Đã tạo mã <code>{ma_ten}</code>!\n"
        f"{BIỂU_TƯỢNG['dong_ho']} Thời hạn: <code>{ngay} ngày</code>\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Lượt sử dụng: <code>{so_lan_su_dung_toi_da}</code>"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"tạo_mã:{ma_ten}")

@bot.message_handler(commands=['danh_sach_ma'])
def xu_ly_danh_sach_ma(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    if not ma_vip_db:
        noi_dung = (
            f"🌌 <b>Danh Sách Mã VIP</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Không có mã VIP nào!"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    danh_sach = [f"🌌 <b>VIP Code List</b> 🌌\n═══ Danh Sách Mã VIP ═══"]
    for ma, chi_tiet in ma_vip_db.items():
        danh_sach.append(
            f"{BIỂU_TƯỢNG['moi']} Mã: <code>{ma}</code>\n"
            f"   {BIỂU_TƯỢNG['dong_ho']} Thời hạn: <code>{chi_tiet['days']} ngày</code>\n"
            f"   {BIỂU_TƯỢNG['thong_tin']} Lượt dùng: <code>{chi_tiet['so_lan_su_dung']}/{chi_tiet['so_lan_su_dung_toi_da']}</code>\n"
            f"   {BIỂU_TƯỢNG['thoi_gian']} Tạo: <code>{chi_tiet['ngay_tao']}</code>"
        )
    noi_dung = "\n\n".join(danh_sach)
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, "danh_sach_ma")

@bot.message_handler(commands=['kich_hoat'])
def xu_ly_kich_hoat(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 3:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /kich_hoat [id] [ngày]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = phan[1]
    try:
        ngay = int(phan[2])
        ngay_het_han = kich_hoat_vip(uid, ngay, mo_rong=True)
        try:
            bot.send_message(
                uid,
                f"🌌 <b>VIP Kích Hoạt</b> 🌌\n═══ Thông Báo ═══\n"
                f"{BIỂU_TƯỢNG['thanh_cong']} VIP đã được kích hoạt {ngay} ngày!\n"
                f"{BIỂU_TƯỢNG['dong_ho']} Hết hạn: <code>{ngay_het_han}</code>",
                parse_mode="HTML"
            )
        except:
            pass
        noi_dung = (
            f"🌌 <b>Quản Lý VIP</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thanh_cong']} Đã kích hoạt VIP cho ID <code>{uid}</code> {ngay} ngày!\n"
            f"{BIỂU_TƯỢNG['dong_ho']} Hết hạn: <code>{ngay_het_han}</code>"
        )
    except ValueError:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Số ngày phải là số nguyên!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"kich_hoat_vip:{uid}")

@bot.message_handler(commands=['huy_kich_hoat'])
def xu_ly_huy_kich_hoat(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    phan = tin_nhan.text.split()
    if len(phan) != 2:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /huy_kich_hoat [id]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = phan[1]
    if uid in nguoi_dung:
        nguoi_dung[uid]["vip_kich_hoat"] = False
        nguoi_dung[uid]["vip_het_han"] = "N/A"
        CoSoDuLieu.luu(nguoi_dung, 'nguoi_dung')
        try:
            bot.send_message(
                uid,
                f"🌌 <b>VIP Đã Hủy</b> 🌌\n═══ Thông Báo ═══\n"
                f"{BIỂU_TƯỢNG['loi']} Tài khoản VIP của bạn đã bị hủy!",
                parse_mode="HTML"
            )
        except:
            pass
        noi_dung = (
            f"🌌 <b>Quản Lý VIP</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thanh_cong']} Đã hủy VIP của ID <code>{uid}</code>"
        )
    else:
        noi_dung = (
            f"🌌 <b>Quản Lý VIP</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['loi']} ID <code>{uid}</code> không tồn tại!"
        )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"huy_vip:{uid}")

@bot.message_handler(commands=['gui'])
def xu_ly_gui(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    thong_diep = " ".join(tin_nhan.text.split()[1:])
    if not thong_diep:
        noi_dung = (
            f"🌌 <b>Lỗi Cú Pháp</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Nhập: /gui [thông_điệp]\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    so_luong_gui = 0
    for uid in nguoi_dung:
        try:
            bot.send_message(
                uid,
                f"🌌 <b>Thông Báo Hệ Thống</b> 🌌\n═══ Nội Dung ═══\n"
                f"{BIỂU_TƯỢNG['phat_tin']} {thong_diep}\n"
                f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}",
                parse_mode="HTML"
            )
            so_luong_gui += 1
            time.sleep(0.05)  # Tránh rate limit
        except:
            continue
    noi_dung = (
        f"🌌 <b>Broadcast Message</b> 🌌\n"
        f"═══ Kết Quả ═══\n"
        f"{BIỂU_TƯỢNG['thanh_cong']} Đã gửi đến <code>{so_luong_gui}</code> người dùng!"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
    theo_doi_hoat_dong(tin_nhan.from_user.id, f"phát_tin:{so_luong_gui}")

@bot.message_handler(commands=['phan_tich'])
def xu_ly_phan_tich(tin_nhan):
    if not SERVER_TRANG_THAI and tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Bot Offline</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bot hiện đang tắt!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    noi_dung = (
        f"🌌 <b>Phân Tích MD5</b> 🌌\n"
        f"═══ Hướng Dẫn ═══\n"
        f"{BIỂU_TƯỢNG['phan_tich']} Gửi mã MD5 (32 ký tự) để phân tích!\n"
        f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
    )
    gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
    theo_doi_hoat_dong(tin_nhan.from_user.id, "phan_tich")

@bot.callback_query_handler(func=lambda call: True)
async def xu_ly_callback(call):
    if call.data == "xác_minh_nhóm":
        nhom_thieu = await kiem_tra_tham_gia_nhom(call.from_user.id)
        if nhom_thieu:
            noi_dung = (
                f"🌌 <b>Xác Minh Nhóm</b> 🌌\n"
                f"═══ Kết Quả ═══\n"
                f"{BIỂU_TƯỢNG['loi']} Bạn chưa tham gia đủ nhóm:\n"
                f"{''.join(f'{BIỂU_TƯỢNG['nhom']} {nhom}\n' for nhom in nhom_thieu)}"
                f"{BIỂU_TƯỢNG['thong_tin']} Tham gia rồi nhấn lại nút!"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['nhom']} Xác Minh Lại", callback_data="xác_minh_nhóm"))
        else:
            thanh_cong, thong_bao = su_dung_ma_vip(MA_VIP, call.from_user.id)
            noi_dung = (
                f"🌌 <b>Xác Minh Thành Công</b> 🌌\n"
                f"═══ Kết Quả ═══\n"
                f"{thong_bao}\n"
                f"{BIỂU_TƯỢNG['thong_tin']} Dùng menu để khám phá!"
            )
            markup = GiaoDienNguoiDung.tao_menu_tuong_tac()
        await bot.edit_message_text(
            noi_dung,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
        theo_doi_hoat_dong(call.from_user.id, "xác_minh_nhóm")
    elif call.data == "menu_tro_giup":
        noi_dung = (
            f"🌌 <b>Hướng Dẫn Sử Dụng</b> 🌌\n"
            f"═══ Lệnh Người Dùng ═══\n"
            f"{BIỂU_TƯỢNG['phan_tich']} /start - Bắt đầu & nhận VIP\n"
            f"{BIỂU_TƯỢNG['vip']} /ma [mã] - Kích hoạt VIP\n"
            f"{BIỂU_TƯỢNG['thong_ke']} /thong_ke - Xem thống kê cá nhân\n"
            f"{BIỂU_TƯỢNG['lich_su']} /lich_su - Xem lịch sử dự đoán\n"
            f"{BIỂU_TƯỢNG['moi_ban']} /moi - Mời bạn bè\n"
            f"{BIỂU_TƯỢNG['tro_giup']} /tro_giup - Hiển thị hướng dẫn\n"
            f"{BIỂU_TƯỢNG['nguoi_dung']} /id - Xem thông tin tài khoản\n"
            f"{BIỂU_TƯỢNG['phan_tich']} Gửi mã MD5 32 ký tự để phân tích\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        await bot.edit_message_text(
            noi_dung,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=GiaoDienNguoiDung.tao_menu_tuong_tac()
        )
        theo_doi_hoat_dong(call.from_user.id, "menu_tro_giup")
    elif call.data == "menu_phan_tich":
        noi_dung = (
            f"🌌 <b>Phân Tích MD5</b> 🌌\n"
            f"═══ Hướng Dẫn ═══\n"
            f"{BIỂU_TƯỢNG['phan_tich']} Gửi mã MD5 (32 ký tự) để phân tích!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        await bot.edit_message_text(
            noi_dung,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=GiaoDienNguoiDung.tao_menu_tuong_tac()
        )
        theo_doi_hoat_dong(call.from_user.id, "menu_phan_tich")
    elif call.data in ["dung", "sai"]:
        uid = str(call.from_user.id)
        if uid in lich_su:
            for muc in lich_su[uid]:
                if muc.get("cho_phan_hoi", False):
                    muc["la_dung"] = call.data == "dung"
                    muc["cho_phan_hoi"] = False
                    CoSoDuLieu.luu(lich_su, 'lich_su')
                    break
        noi_dung = (
            f"🌌 <b>Phản Hồi</b> 🌌\n"
            f"═══ Kết Quả ═══\n"
            f"{BIỂU_TƯỢNG['thanh_cong']} Cảm ơn phản hồi của bạn!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Tiếp tục phân tích bằng cách gửi MD5!"
        )
        await bot.edit_message_text(
            noi_dung,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="HTML",
            reply_markup=GiaoDienNguoiDung.tao_menu_tuong_tac()
        )
        theo_doi_hoat_dong(call.from_user.id, f"phan_hoi:{call.data}")

@bot.message_handler(content_types=['text'])
def xu_ly_danh_sach_ma(tin_nhan):
    if tin_nhan.from_user.id != ADMIN_ID:
        noi_dung = (
            f"🌌 <b>Truy Cập Bị Từ Chối</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không có quyền admin!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    uid = str(tin_nhan.from_user.id)
    if uid in nguoi_dung and nguoi_dung[uid].get("bi_cam", False):
        noi_dung = (
            f"🌌 <b>Tài Khoản Bị Cấm</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn không thể sử dụng bot!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Liên hệ {LIEN_HE_HO_TRO} để được hỗ trợ."
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung)
        return
    if not kiem_tra_vip_kich_hoat(tin_nhan.from_user.id):
        noi_dung = (
            f"🌌 <b>Truy Cập Hạn Chế</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Bạn cần VIP để phân tích MD5!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Dùng /ma hoặc /start để kích hoạt VIP.\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
        return
    md5_input = tin_nhan.text.strip().lower()
    if len(md5_input) != 32 or not re.match(r'^[a-f0-9]{32}$', md5_input):
        noi_dung = (
            f"🌌 <b>Lỗi Định Dạng</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} Mã MD5 phải là 32 ký tự hex!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Ví dụ: <code>098f6bcd4621d373cade4e832627b4f6</code>\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())
        return
    cho_phan_hoi, md5_cho = kiem_tra_trang_thai_phan_hoi(tin_nhan.from_user.id)
    if cho_phan_hoi and md5_cho != md5_input:
        noi_dung = (
            f"🌌 <b>Phản Hồi Đang Chờ</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['canh_bao']} Vui lòng phản hồi kết quả cho MD5 <code>{md5_cho[:8]}...{md5_cho[-8:]}</code>!\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Nhấn nút 'Đúng' hoặc 'Sai' trước khi phân tích tiếp."
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['dung']} Đúng", callback_data="dung"),
            types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['sai']} Sai", callback_data="sai")
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, markup)
        return
    try:
        phan_tich = PhanTichMD5.dong_co_sieu_tri_tue(md5_input)
        bao_cao = GiaoDienNguoiDung.tao_bao_cao_phan_tich(md5_input, phan_tich)
        luu_du_doan(tin_nhan.from_user.id, md5_input, phan_tich)
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['dung']} Đúng", callback_data="dung"),
            types.InlineKeyboardButton(f"{BIỂU_TƯỢNG['sai']} Sai", callback_data="sai")
        )
        noi_dung = bao_cao + f"\n{BIỂU_TƯỢNG['thong_tin']} Phản hồi kết quả để cải thiện hệ thống!"
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, markup)
        theo_doi_hoat_dong(tin_nhan.from_user.id, f"phan_tich_md5:{md5_input}")
    except ValueError as e:
        noi_dung = (
            f"🌌 <b>Lỗi Phân Tích</b> 🌌\n"
            f"═══ Thông Báo ═══\n"
            f"{BIỂU_TƯỢNG['loi']} {str(e)}\n"
            f"{BIỂU_TƯỢNG['thong_tin']} Hỗ trợ: {LIEN_HE_HO_TRO}"
        )
        gui_phan_hoi_dong_bo(tin_nhan.chat.id, tin_nhan, noi_dung, GiaoDienNguoiDung.tao_menu_tuong_tac())

# ==============================================
# KHỞI CHẠY BOT
# ==============================================
if __name__ == "__main__":
    print(f"🌌 {TEN_BOT} đang khởi động...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Lỗi: {e}")
            time.sleep(5)