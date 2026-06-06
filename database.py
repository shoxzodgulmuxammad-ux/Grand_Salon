import json
import os
from datetime import datetime

DB_FILE = "appointments.json"

def _load():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def _save(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_all_appointments():
    return _load()

def get_appointment_by_time(time_str: str):
    """Berilgan vaqtda navbat bormi?"""
    appts = _load()
    for a in appts:
        if a["time"] == time_str and a["status"] == "active":
            return a
    return None

def add_appointment(user_id: int, username: str, name: str, phone: str, time_str: str):
    appts = _load()
    appt = {
        "id": len(appts) + 1,
        "user_id": user_id,
        "username": username,
        "name": name,
        "phone": phone,
        "time": time_str,
        "status": "active",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    appts.append(appt)
    _save(appts)
    return appt

def cancel_appointment_by_id(appt_id: int):
    appts = _load()
    for a in appts:
        if a["id"] == appt_id:
            a["status"] = "cancelled"
            break
    _save(appts)

# YANGI QO'SHILDI: Bazadan butunlay o'chirish funksiyasi
def delete_appointment_by_id(appt_id: int):
    appts = _load()
    # Navbatni ro'yxatdan butunlay olib tashlaymiz
    appts = [a for a in appts if a["id"] != appt_id]
    _save(appts)

def get_user_appointments(user_id: int):
    return [a for a in _load() if a["user_id"] == user_id and a["status"] == "active"]

def postpone_all_to_tomorrow():
    """Barcha aktiv navbatlarni ertangi kunga ko'chirish"""
    from datetime import timedelta
    appts = _load()
    changed = []
    for a in appts:
        if a["status"] == "active":
            try:
                dt = datetime.strptime(a["time"], "%Y-%m-%d %H:%M")
                new_dt = dt + timedelta(days=1)
                old_time = a["time"]
                a["time"] = new_dt.strftime("%Y-%m-%d %H:%M")
                changed.append({"appt": a, "old_time": old_time})
            except:
                pass
    _save(appts)
    return changed