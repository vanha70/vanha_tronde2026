import streamlit as st
from docx import Document
import random
import io
import re
import zipfile
import string

# --- CẤU HÌNH GIAO DIỆN GIỐNG HÌNH MẪU ---
st.set_page_config(page_title="TNMix - GV Nguyễn Văn Hà", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, #f3605f 0%, #f9a066 100%); }
    .main-container { background-color: white; border-radius: 30px; padding: 30px; margin-top: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    .logo-badge { background: rgba(255,255,255,0.3); padding: 10px 20px; border-radius: 15px; color: white; font-weight: bold; text-align: center; width: fit-content; margin: auto; }
    .teacher-info { text-align: center; color: white; margin-top: 10px; font-size: 1.1em; }
    div.stButton > button:first-child[kind="primary"] { background: linear-gradient(90deg, #f3605f, #f9a066); color: white; border: none; border-radius: 25px; height: 50px; width: 100%; font-weight: bold; font-size: 18px; }
    .upload-area { border: 2px solid #f3605f; border-radius: 20px; padding: 40px; text-align: center; background-color: #fffafb; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC XỬ LÝ CHUYÊN SÂU ---
def parse_docx_2025(file_bytes):
    doc = Document(io.BytesIO(file_bytes))
    parts = {"PHẦN I": [], "PHẦN II": [], "PHẦN III": []}
    current_part = None
    current_q = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text and not current_q: continue
        
        # Nhận diện phần
        if "PHẦN I" in text.upper(): current_part = "PHẦN I"; continue
        if "PHẦN II" in text.upper(): current_part = "PHẦN II"; continue
        if "PHẦN III" in text.upper(): current_part = "PHẦN III"; continue

        if current_part:
            if re.match(r'^Câu \d+[:.]', text, re.I):
                if current_q: parts[current_part].append(current_q)
                current_q = [para]
            elif current_q:
                current_q.append(para)
    
    if current_q: parts[current_part].append(current_q)
    return parts

def create_exam_and_keys(parts, code):
    new_doc = Document()
    new_doc.add_heading(f"MÃ ĐỀ: {code}", 0)
    ans_key = {"I": [], "II": [], "III": []}

    for p_label in ["PHẦN I", "PHẦN II", "PHẦN III"]:
        questions = parts[p_label]
        if not questions: continue
        
        new_doc.add_heading(p_label, level=1)
        shuffled_questions = list(questions)
        random.shuffle(shuffled_questions)

        for i, q_paras in enumerate(shuffled_questions, 1):
            # Ghi câu hỏi
            q_head = re.sub(r'^Câu \d+[:.]', f'Câu {i}:', q_paras[0].text, flags=re.I)
            new_doc.add_paragraph(q_head)

            if p_label == "PHẦN I":
                options = []
                for p in q_paras[1:]:
                    if not p.text.strip(): continue
                    # Nhận diện đáp án đúng qua gạch chân
                    is_correct = any(run.underline for run in p.runs)
                    # Tách nội dung bỏ A. B. C. D.
                    opt_content = re.sub(r'^[A-D][\.\)\s]+', '', p.text.strip()).strip()
                    options.append({'text': opt_content, 'correct': is_correct})
                
                random.shuffle(options)
                for j, opt in enumerate(options):
                    if j < 26: # Bảo vệ IndexError
                        label = string.ascii_uppercase[j]
                        new_doc.add_paragraph(f"{label}. {opt['text']}")
                        if opt['correct']: ans_key["I"].append(label)
            
            elif p_label == "PHẦN II":
                # Giữ nguyên thứ tự a, b, c, d của Phần II nhưng trộn câu hỏi
                for p in q_paras[1:]:
                    new_doc.add_paragraph(p.text)
            
            elif p_label == "PHẦN III":
                # Trả lời ngắn
                for p in q_paras[1:]:
                    new_doc.add_paragraph(p.text)

    buf = io.BytesIO(); new_doc.save(buf); buf.seek(0)
    return buf, ans_key

# --- GIAO DIỆN ---
st.markdown('<div class="logo-badge">TNMix</div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:white; margin-bottom:0;'>TNMix - Trộn đề trắc nghiệm</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info"><b>Giáo viên:</b> Nguyễn Văn Hà<br><b>Zalo:</b> 0907781595</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Upload file .docx", type=["docx"], label_visibility="collapsed")
    
    if not uploaded_file:
        st.markdown("""
            <div class="upload-area">
                <img src="https://img.icons8.com/ios/50/f3605f/upload-2.png"/><br>
                <p>Kéo thả file .docx vào đây hoặc chọn từ máy</p>
            </div>
        """, unsafe_allow_html=True)
    
    if uploaded_file:
        num_codes = st.number_input("Số lượng mã đề:", 1, 20, 4)
        if st.button("Chọn tệp", type="primary"):
            parts = parse_docx_2025(uploaded_file.read())
            zip_buf = io.BytesIO()
            
            with zipfile.ZipFile(zip_buf, "a") as zf:
                for i in range(num_codes):
                    code = 1201 + i
                    doc_file, keys = create_exam_and_keys(parts, str(code))
                    zf.writestr(f"De_Thi_Ma_{code}.docx", doc_file.getvalue())
            
            st.success("Đã trộn xong!")
            st.download_button("📥 TẢI XUỐNG FILE ZIP", zip_buf.getvalue(), "Ket_Qua_Tron_De.zip")
    st.markdown('</div>', unsafe_allow_html=True)
