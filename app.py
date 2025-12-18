import streamlit as st
from docx import Document
import io
import re
import random
import zipfile
import copy

# --- CẤU HÌNH GIAO DIỆN CHUẨN ---
st.set_page_config(page_title="TNMix - GV Nguyễn Văn Hà", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, #f3605f 0%, #f9a066 100%); }
    .main-container { background-color: white; border-radius: 30px; padding: 30px; margin-top: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
    .teacher-info { text-align: center; color: white; margin-top: 10px; font-size: 1.1em; }
    div.stButton > button:first-child[kind="primary"] { background: linear-gradient(90deg, #f3605f, #f9a066); color: white; border: none; border-radius: 25px; height: 50px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- HÀM SAO CHÉP ĐỊNH DẠNG (GIỮ HÌNH ẢNH & CÔNG THỨC) ---
def copy_para_format(source_para, target_doc):
    """Sao chép nguyên khối paragraph bao gồm cả hình ảnh và công thức xml"""
    new_para = target_doc.add_paragraph()
    for run in source_para.runs:
        new_run = new_para.add_run(run.text)
        # Sao chép định dạng cơ bản
        new_run.bold = run.bold
        new_run.italic = run.italic
        new_run.underline = run.underline
        # Sao chép các thành phần XML (Hình ảnh, Công thức)
        new_para._p.append(copy.deepcopy(run._r))
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
            # Nhận diện câu hỏi
            if re.match(r'^CÂU \d+[:.]', text):
                if current_q: parts[current_part].append(current_q)
                current_q = [para]
            elif current_q or text:
                current_q.append(para)
    
    if current_q: parts[current_part].append(current_q)
    return parts

# --- TẠO ĐỀ MỚI ---
def generate_code(parts, code_name):
    new_doc = Document()
    new_doc.add_heading(f"MÃ ĐỀ: {code_name}", 0)
    
    for p_label in ["PHẦN I", "PHẦN II", "PHẦN III"]:
        if not parts[p_label]: continue
        new_doc.add_heading(p_label, level=1)
        
        shuffled_qs = list(parts[p_label])
        random.shuffle(shuffled_qs)

        for i, q_paras in enumerate(shuffled_qs, 1):
            # Sửa số thứ tự câu mà không làm mất định dạng
            first_para = q_paras[0]
            new_p = new_doc.add_paragraph()
            # Thay thế text "Câu X" bằng "Câu i"
            label_text = f"Câu {i}: "
            content_text = re.sub(r'^Câu \d+[:.]', '', first_para.text, flags=re.I).strip()
            new_p.add_run(label_text).bold = True
            new_p.add_run(content_text)
            
            # Chép các paragraph còn lại của câu đó (hình ảnh, đáp án...)
            for p in q_paras[1:]:
                new_p_extra = new_doc.add_paragraph()
                new_p_extra._p.append(copy.deepcopy(p._p))

    buf = io.BytesIO()
    new_doc.save(buf)
    buf.seek(0)
    return buf

# --- GIAO DIỆN ---
st.markdown("<h2 style='text-align:center; color:white;'>TNMix Pro - Nguyễn Văn Hà</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info">Zalo: 0907781595</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("Tải file đề .docx", type=["docx"], label_visibility="collapsed")

if uploaded_file:
    file_content = io.BytesIO(uploaded_file.read())
    num_codes = st.number_input("Số mã đề:", 1, 10, 4)
    
    if st.button("BẮT ĐẦU TRỘN ĐỀ", type="primary"):
        with st.spinner("Đang xử lý hình ảnh và công thức..."):
            parts = parse_exam_2025(file_content)
            
            # Kiểm tra dữ liệu
            if not any(parts.values()):
                st.error("Lỗi: Không tìm thấy câu hỏi! Hãy kiểm tra định dạng 'Câu 1:', 'Câu 2:'")
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "a") as zf:
                    for i in range(num_codes):
                        c_name = 1201 + i
                        out_doc = generate_code(parts, str(c_name))
                        zf.writestr(f"De_{c_name}.docx", out_doc.getvalue())
                
                st.success("Trộn đề thành công!")
                st.download_button("📥 TẢI FILE ZIP", zip_buf.getvalue(), "KetQua_ThayHa.zip")
