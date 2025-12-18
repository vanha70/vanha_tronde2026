import streamlit as st
from docx import Document
import io
import re
import random
import zipfile
import string

# --- CẤU HÌNH GIAO DIỆN THEO MẪU ---
st.set_page_config(page_title="TNMix Pro - GV Nguyễn Văn Hà", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, #f3605f 0%, #f9a066 100%); }
    .main-container { background-color: white; border-radius: 30px; padding: 30px; margin-top: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    .logo-badge { background: rgba(255,255,255,0.3); padding: 10px 20px; border-radius: 15px; color: white; font-weight: bold; text-align: center; width: fit-content; margin: auto; }
    .teacher-info { text-align: center; color: white; margin-top: 10px; font-size: 1.1em; }
    div.stButton > button:first-child[kind="primary"] { background: linear-gradient(90deg, #f3605f, #f9a066); color: white; border: none; border-radius: 25px; height: 50px; width: 100%; font-weight: bold; font-size: 18px; }
    .upload-area { border: 2px solid #f3605f; border-radius: 20px; padding: 40px; text-align: center; background-color: #fffafb; color: #555; }
    </style>
    """, unsafe_allow_html=True)

# --- HÀM SAO CHÉP AN TOÀN ---
def copy_paragraph_safely(source_para, target_doc):
    """Sao chép paragraph sang file mới mà không làm hỏng cấu trúc Word"""
    new_para = target_doc.add_paragraph()
    new_para.paragraph_format.alignment = source_para.alignment
    for run in source_para.runs:
        new_run = new_para.add_run()
        # Sao chép text và định dạng
        new_run.text = run.text
        new_run.bold = run.bold
        new_run.italic = run.italic
        new_run.underline = run.underline
        # Sao chép các thành phần nội dung khác (hình ảnh/công thức) qua XML thô
        new_run._r.append(run._r) if not run.text else None
    return new_para

# --- LOGIC PHÂN TÁCH ĐỀ ---
def parse_exam_2025(file_stream):
    doc = Document(file_stream)
    parts = {"PHẦN I": [], "PHẦN II": [], "PHẦN III": []}
    current_part = None
    current_q = []

    for para in doc.paragraphs:
        text = para.text.strip().upper()
        if "PHẦN I" in text: current_part = "PHẦN I"; continue
        if "PHẦN II" in text: current_part = "PHẦN II"; continue
        if "PHẦN III" in text: current_part = "PHẦN III"; continue

        if current_part:
            if re.match(r'^CÂU \d+[:.]', text):
                if current_q: parts[current_part].append(current_q)
                current_q = [para]
            elif current_q:
                current_q.append(para)
    
    if current_q: parts[current_part].append(current_q)
    return parts

# --- TẠO ĐỀ VÀ BẢNG ĐÁP ÁN ---
def generate_exam_package(parts, code):
    new_doc = Document()
    new_doc.add_heading(f"MÃ ĐỀ: {code}", 0)
    ans_key = {"I": [], "II": [], "III": []}

    for p_label in ["PHẦN I", "PHẦN II", "PHẦN III"]:
        if not parts[p_label]: continue
        new_doc.add_heading(p_label, level=1)
        
        shuffled_qs = list(parts[p_label])
        random.shuffle(shuffled_qs)

        for i, q_paras in enumerate(shuffled_qs, 1):
            # Paragraph đầu tiên (Thân câu hỏi)
            q_head = new_doc.add_paragraph()
            q_head.add_run(f"Câu {i}: ").bold = True
            # Lấy nội dung sau chữ "Câu X:"
            raw_text = re.sub(r'^Câu \d+[:.]', '', q_paras[0].text, flags=re.I).strip()
            q_head.add_run(raw_text)

            if p_label == "PHẦN I":
                options = []
                for p in q_paras[1:]:
                    if not p.text.strip(): continue
                    is_correct = any(run.underline for run in p.runs)
                    opt_content = re.sub(r'^[A-D][\.\)\s]+', '', p.text.strip()).strip()
                    options.append({'para': p, 'correct': is_correct, 'content': opt_content})
                
                random.shuffle(options)
                for j, opt in enumerate(options):
                    label = string.ascii_uppercase[j]
                    new_p = new_doc.add_paragraph(f"{label}. {opt['content']}")
                    if opt['correct']: ans_key["I"].append(label)
            else:
                # Phần II và III giữ nguyên nội dung
                for p in q_paras[1:]:
                    new_doc.add_paragraph(p.text)

    buf = io.BytesIO(); new_doc.save(buf); buf.seek(0)
    return buf, ans_key

# --- GIAO DIỆN ---
st.markdown('<div class="logo-badge">TNMix</div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:white; margin-bottom:0;'>TNMix Pro - Nguyễn Văn Hà</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info">Zalo: 0907781595</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload file .docx", type=["docx"], label_visibility="collapsed")
    
    if not uploaded_file:
        st.markdown('<div class="upload-area">Kéo thả file .docx vào đây</div>', unsafe_allow_html=True)
    
    if uploaded_file:
        num = st.number_input("Số lượng mã đề:", 1, 10, 4)
        if st.button("BẮT ĐẦU TRỘN ĐỀ", type="primary"):
            file_bytes = uploaded_file.read()
            parts = parse_exam_2025(io.BytesIO(file_bytes))
            
            if not any(parts.values()):
                st.error("Dữ liệu trống! Hãy kiểm tra từ khóa 'Câu 1:', 'PHẦN I'...")
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "a") as zf:
                    for i in range(num):
                        code = 1201 + i
                        doc_file, keys = generate_exam_package(parts, code)
                        zf.writestr(f"De_{code}.docx", doc_file.getvalue())
                
                st.success("Trộn đề thành công!")
                st.download_button("📥 TẢI TRỌN BỘ (.ZIP)", zip_buf.getvalue(), "TNMix_ThayHa.zip")
    st.markdown('</div>', unsafe_allow_html=True)
