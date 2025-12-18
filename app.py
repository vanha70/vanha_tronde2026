import streamlit as st
from docx import Document
import io
import re
import random
import zipfile
import string

# --- GIAO DIỆN THEO HÌNH MẪU ---
st.set_page_config(page_title="TNMix Pro - GV Nguyễn Văn Hà", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, #f3605f 0%, #f9a066 100%); }
    .main-container { background-color: white; border-radius: 30px; padding: 30px; margin-top: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    .logo-badge { background: rgba(255,255,255,0.3); padding: 10px 20px; border-radius: 15px; color: white; font-weight: bold; text-align: center; width: fit-content; margin: auto; }
    .teacher-info { text-align: center; color: white; margin-top: 10px; font-size: 1.1em; }
    div.stButton > button:first-child[kind="primary"] { background: linear-gradient(90deg, #f3605f, #f9a066); color: white; border: none; border-radius: 25px; height: 50px; width: 100%; font-weight: bold; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC NHẬN DIỆN DỮ LIỆU LINH HOẠT ---
def parse_exam_flexible(file_stream):
    doc = Document(file_stream)
    parts = {"PHẦN I": [], "PHẦN II": [], "PHẦN III": []}
    current_part = None
    current_q = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text: continue
        
        # 1. Nhận diện chuyển phần (không phân biệt hoa thường, dấu chấm)
        text_up = text.upper()
        if "PHẦN I" in text_up: current_part = "PHẦN I"; continue
        if "PHẦN II" in text_up: current_part = "PHẦN II"; continue
        if "PHẦN III" in text_up: current_part = "PHẦN III"; continue

        if current_part:
            # 2. Nhận diện câu hỏi mới:
            # - Bắt đầu bằng "Câu X:" 
            # - HOẶC bắt đầu bằng nội dung mà paragraph tiếp theo là các lựa chọn A, B, C, D
            is_new_q = re.match(r'^Câu \d+[:.]', text, re.I) 
            
            # Đối với file của thầy (không có chữ Câu 1), ta nhận diện khi gặp nội dung mới 
            # sau khi đã kết thúc đáp án của câu trước.
            if is_new_q:
                if current_q: parts[current_part].append(current_q)
                current_q = [para]
            else:
                # Nếu là PHẦN I và dòng này chứa A. B. C. D. thì nó thuộc câu đang xét
                if current_part == "PHẦN I" and re.search(r'[A-D][\.\)]', text):
                    current_q.append(para)
                # Nếu là dòng chữ bình thường và chưa có câu nào hoặc câu trước đã có đáp án
                elif not current_q or (current_part == "PHẦN I" and any(re.search(r'[A-D][\.\)]', p.text) for p in current_q)):
                    if current_q: parts[current_part].append(current_q)
                    current_q = [para]
                else:
                    current_q.append(para)
    
    if current_q: parts[current_part].append(current_q)
    return parts

def generate_exam(parts, code):
    new_doc = Document()
    new_doc.add_heading(f"MÃ ĐỀ: {code}", 0)
    
    for p_label, questions in parts.items():
        if not questions: continue
        new_doc.add_heading(p_label, level=1)
        
        shuffled_qs = list(questions)
        random.shuffle(shuffled_qs)

        for i, q_paras in enumerate(shuffled_qs, 1):
            # Paragraph đầu tiên làm thân câu hỏi
            new_p = new_doc.add_paragraph()
            new_p.add_run(f"Câu {i}: ").bold = True
            
            # Xử lý nội dung câu hỏi (bỏ chữ Câu cũ nếu có)
            body_text = re.sub(r'^Câu \d+[:.]', '', q_paras[0].text, flags=re.I).strip()
            new_p.add_run(body_text)

            # Chép các paragraph còn lại (Hình ảnh, công thức, đáp án)
            for p in q_paras[1:]:
                target_p = new_doc.add_paragraph()
                for run in p.runs:
                    new_run = target_p.add_run(run.text)
                    new_run.bold, new_run.italic, new_run.underline = run.bold, run.italic, run.underline
                    # Đưa hình ảnh/công thức vào XML
                    if not run.text:
                        target_p._p.append(run._r)

    buf = io.BytesIO(); new_doc.save(buf); buf.seek(0)
    return buf

# --- GIAO DIỆN ---
st.markdown('<div class="logo-badge">TNMix</div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:white;'>TNMix Pro - Nguyễn Văn Hà</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info">Zalo: 0907781595</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload file .docx", type=["docx"], label_visibility="collapsed")

if uploaded_file:
    file_bytes = uploaded_file.read()
    parts = parse_exam_flexible(io.BytesIO(file_bytes))
    
    if not any(parts.values()):
        st.error("Dữ liệu trống! Hãy đảm bảo file có chữ 'PHẦN I' và các đáp án 'A.', 'B.'...")
    else:
        num = st.number_input("Số mã đề:", 1, 10, 4)
        if st.button("BẮT ĐẦU TRỘN ĐỀ", type="primary"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "a") as zf:
                for i in range(num):
                    code = 1201 + i
                    doc_buf = generate_exam(parts, code)
                    zf.writestr(f"De_{code}.docx", doc_buf.getvalue())
            st.success("Thành công!")
            st.download_button("📥 TẢI FILE ZIP", zip_buf.getvalue(), "TNMix_ThayHa.zip")
