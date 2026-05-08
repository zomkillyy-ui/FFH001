import streamlit as st
from supabase import create_client, Client
import datetime

# ==========================================
# ตั้งค่าหน้าเพจ
# ==========================================
st.set_page_config(page_title="My Photo Log", page_icon="📸", layout="centered")
st.title("📸 My Photo Log")

# ==========================================
# ส่วนที่ 1: เชื่อมต่อ Supabase
# ==========================================
# ⚠️ นำ URL และ Key ของโปรเจกต์ Supabase มาวางแทนที่ข้อความด้านล่างนี้
SUPABASE_URL = "https://wcumqheyetylkijojvri.supabase.co"
SUPABASE_KEY = "sb_publishable_uf0gpBmWN13Eh3-hobOSQg_hhA3GSBq"

# ใช้ cache_resource เพื่อให้เชื่อมต่อฐานข้อมูลแค่ครั้งเดียวตอนเปิดแอป
@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase = init_connection()
except Exception as e:
    st.error("ไม่สามารถเชื่อมต่อฐานข้อมูลได้ โปรดตรวจสอบ URL และ API Key")
    st.stop()

# ==========================================
# ส่วนที่ 2: ฟอร์มอัปโหลด และบันทึกขึ้น Cloud
# ==========================================
st.subheader("อัปโหลดรูปใหม่")

with st.form("upload_form", clear_on_submit=True):
    uploaded_file = st.file_uploader("เลือกรูปภาพ...", type=["jpg", "jpeg", "png"])
    caption_text = st.text_area("✍️ เพิ่มคำบรรยายรูปภาพ (ไม่บังคับ):", placeholder="บันทึกเรื่องราวสั้นๆ...")
    
    submitted = st.form_submit_button("บันทึกรูปลงแกลลอรี")
    
    if submitted:
        if uploaded_file is not None:
            # แสดงวงล้อโหลดระหว่างส่งข้อมูลขึ้น Cloud
            with st.spinner("กำลังบันทึกข้อมูลขึ้น Cloud..."):
                try:
                    # 1. จัดการชื่อไฟล์ไม่ให้ซ้ำกัน
                    file_extension = uploaded_file.name.split('.')[-1]
                    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    new_file_name = f"photo_{timestamp_str}.{file_extension}"
                    
                    # 2. อัปโหลดรูปขึ้น Supabase Storage (Bucket ชื่อ "photo_logs")
                    file_bytes = uploaded_file.getvalue()
                    supabase.storage.from_("photo_logs").upload(new_file_name, file_bytes)
                    
                    # 3. ดึงลิงก์รูป (Public URL) ที่เพิ่งอัปโหลดเสร็จ
                    image_url = supabase.storage.from_("photo_logs").get_public_url(new_file_name)
                    
                    # 4. นำลิงก์รูปรวมถึงคำบรรยาย ไปบันทึกลง Database Table (Table ชื่อ "photos")
                    supabase.table("Photo").insert({"image_url": image_url, "caption": caption_text}).execute()
                    
                    st.success("บันทึกสำเร็จ! ข้อมูลถูกเก็บอย่างปลอดภัยบน Cloud แล้ว ☁️")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: โปรดตรวจสอบว่าสร้าง Bucket และ Table ถูกต้องหรือไม่ ({e})")
        else:
            st.warning("⚠️ กรุณาเลือกรูปภาพก่อนกดบันทึกครับ")

st.divider()

# ==========================================
# ส่วนที่ 3: ดึงข้อมูลจาก Cloud มาแสดงเป็น Gallery
# ==========================================
st.subheader("แกลลอรีรูปภาพ")

try:
    # ดึงข้อมูลทั้งหมดจากตาราง photos เรียงจากใหม่ไปเก่า
    response = supabase.table("Photo").select("*").order("created_at", desc=True).execute()
    photos_data = response.data

    if not photos_data:
        st.info("ยังไม่มีรูปภาพ เริ่มอัปโหลดรูปแรกได้เลยครับ")
    else:
        cols = st.columns(2)
        for index, item in enumerate(photos_data):
            # แปลงรูปแบบเวลาที่ดึงมาจากฐานข้อมูล (เวลาสากล UTC)
            db_time = datetime.datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            
            # ปรับเป็นโซนเวลาที่คุณต้องการ (+7 สำหรับไทย, หากใช้งานที่อื่นสามารถปรับตัวเลขนี้ได้)
            local_time = db_time + datetime.timedelta(hours=7) 
            time_caption = local_time.strftime("%d %b %Y, %H:%M")
            
            custom_caption = item.get("caption", "")
            if custom_caption:
                final_caption = f"{custom_caption}\n\n🕒 {time_caption}"
            else:
                final_caption = f"🕒 {time_caption}"

            with cols[index % 2]:
                st.image(item["image_url"], caption=final_caption, use_container_width=True)
except Exception as e:
    st.error(f"รายละเอียด Error: {e}")