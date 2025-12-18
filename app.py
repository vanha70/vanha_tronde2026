import streamlit as st
from docx import Document
import random
import io
import re
import zipfile
import string
import pandas as pd

# --- GIAO DIỆN THEO HÌNH MẪU ---
st.set_page_config(page_title="TNMix - Trộn đề trắc nghiệm", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { 
        background: linear-gradient(180deg, #f3605f 0%, #f9a066 100%); 
    }
    .main-container { 
        background-color: white; border-radius: 30px; padding: 30px; 
        margin-top: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); 
    }
    .logo-badge { 
        background: rgba(255,255,255,0.3); padding: 10px 20px; border-radius: 15px; 
        color: white; font-weight: bold; text-align: center; width: fit-content; margin: auto; 
    }
    .teacher-info { text-align: center; color: white; margin-top: 10px; font-size: 1.1em; }
    div.stButton > button:first-child[kind="primary"] { 
        background: linear-gradient(90deg, #f3605f, #f9a066); 
        color: white; border: none; border-radius: 25px; height: 50px; width: 100%; font-weight: bold; 
    }
    .upload-box {
        border: 2px solid #f3605f; border-radius: 20px; padding: 40px;
        text-align: center; background-color: #fffafb;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC XỬ LÝ ĐỀ 3 PHẦN ---
def parse_document(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    parts = {"PHẦN I": [], "PHẦN II": [], "PHẦN III": []}
    current_part = None
    current_q = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if "PHẦN I" in text.upper(): current_part = "PHẦN I"; continue
        if "PHẦN II" in text.upper(): current_part = "PHẦN II"; continue
        if "PHẦN III" in text.upper(): current_part = "PHẦN III"; continue

        if current_part:
            # Nhận diện câu hỏi (Câu 1:, Câu 2...)
            if re.match(r'^Câu \d+[:.]', text, re.I):
                if current_q: parts[current_part].append(current_q)
                current_q = [para]
            elif text or current_q:
                current_q.append(para)
    
    if current_q: parts[current_part].append(current_q)
    return parts

def shuffle_and_create(parts, code):
    new_doc = Document()
    new_doc.add_heading(f"MÃ ĐỀ: {code}", 0)
    ans_key = {"I": [], "II": [], "III": []}

    for p_name, questions in parts.items():
        if not questions: continue
        new_doc.add_heading(p_name, level=1)
        shuffled_idx = list(range(len(questions)))
        random.shuffle(shuffled_idx)

        for i, idx in enumerate(shuffled_idx, 1):
            q_paras = questions[idx]
            # Đổi số câu
            q_head = re.sub(r'^Câu \d+[:.]', f'Câu {i}:', q_paras[0].text, flags=re.I)
            new_doc.add_paragraph(q_head)

            # Xử lý nội dung/đáp án dựa trên phần
            if p_name == "PHẦN I":
                options = []
                for p in q_paras[1:]:
                    is_correct = any(run.underline for run in p.runs)
                    clean_opt = re.sub(r'^[A-D][\.\)]', '', p.text.strip()).strip()
                    if clean_opt: options.append({'text': clean_opt, 'correct': is_correct})
                
                random.shuffle(options)
                for j, opt in enumerate(options):
                    label = string.ascii_uppercase[j]
                    new_doc.add_paragraph(f"{label}. {opt['text']}")
                    if opt['correct']: ans_key["I"].append(label)
            
            else: # Phần II và III (Giữ nguyên nội dung, chỉ trộn thứ tự câu)
                for p in q_paras[1:]:
                    new_doc.add_paragraph(p.text)
                    # Logic lấy key từ thẻ <key=...> nếu có trong file đề
                    key_match = re.search(r'<key=(.*?)>', p.text)
                    if key_match:
                        key_val = key_match.group(1)
                        ans_key["III" if p_name == "PHẦN III" else "II"].append(key_val)

    buf = io.BytesIO(); new_doc.save(buf); buf.seek(0)
    return buf, ans_key

# --- UI ---
st.markdown('<div class="logo-badge">TNMix</div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:white; margin:0;'>TNMix - Trộn đề trắc nghiệm</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info"><b>Giáo viên:</b> Nguyễn Văn Hà | <b>Zalo:</b> 0907781595</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    # Khu vực Upload giống ảnh mẫu
    uploaded_file = st.file_uploader("Kéo thả file .docx", type=["docx"], label_visibility="collapsed")
    
    if not uploaded_file:
        st.markdown("""
            <div class="upload-box">
                <img src="https://img.icons8.com/ios/50/f3605f/upload-2.png"/><br><br>
                Kéo thả file .docx hoặc .doc vào đây<br>hoặc chọn từ máy
            </div>
        """, unsafe_allow_html=True)
    
    if uploaded_file:
        num = st.number_input("Số mã đề:", 1, 10, 4)
        if st.button("Chọn tệp (Bắt đầu trộn)", type="primary"):
            parts = parse_document(uploaded_file.read())
            zip_buffer = io.BytesIO()
            all_keys = []

            with zipfile.ZipFile(zip_buffer, "a") as zf:
                for i in range(num):
                    code = 1201 + i
                    doc_buf, keys = shuffle_and_create(parts, code)
                    zf.writestr(f"De_{code}.docx", doc_buf.getvalue())
                    all_keys.append({"Mã đề": code, **keys})
                
                # Tạo file đáp án tổng hợp (Excel hoặc Word bảng)
                # (Phần này thầy có thể xem trực tiếp trên app hoặc xuất file)
            
            st.success("Trộn thành công!")
            st.download_button("📥 TẢI TRỌN BỘ (ZIP)", zip_buffer.getvalue(), "Ket_Qua_Tron_De.zip")
    st.markdown('</div>', unsafe_allow_html=True)
