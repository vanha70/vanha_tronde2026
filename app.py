import streamlit as st
from docx import Document
import random
import io
import re
import zipfile
import string

# --- CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="TNMix Pro - GV Nguyễn Văn Hà", layout="centered")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background: linear-gradient(180deg, #f3605f 0%, #f9a066 100%); }
    .main-container { background-color: white; border-radius: 30px; padding: 30px; margin-top: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); color: #333; }
    .logo-badge { background: rgba(255,255,255,0.3); padding: 10px 20px; border-radius: 15px; color: white; font-weight: bold; text-align: center; width: fit-content; margin: auto; border: 1px solid rgba(255,255,255,0.4); }
    .teacher-info { text-align: center; color: white; margin-top: 10px; font-size: 1.1em; line-height: 1.4; }
    div.stButton > button:first-child[kind="primary"] { background: linear-gradient(90deg, #f3605f, #f9a066); color: white; border: none; border-radius: 25px; height: 50px; font-weight: bold; width: 100%; font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIC XỬ LÝ LÕI ---
def process_single_code(file_bytes, code_name):
    doc = Document(io.BytesIO(file_bytes))
    questions = []
    current_q = []

    # Tách câu hỏi dựa trên từ khóa "Câu X"
    for para in doc.paragraphs:
        text = para.text.strip()
        if re.match(r'^Câu \d+[:.]', text, re.IGNORECASE):
            if current_q: questions.append(current_q)
            current_q = [para]
        else:
            if text or current_q: current_q.append(para)
    if current_q: questions.append(current_q)

    # Trộn thứ tự câu hỏi
    random.shuffle(questions)
    
    quiz_doc = Document()
    quiz_doc.add_heading(f'MÃ ĐỀ: {code_name}', 1)
    ans_key = []

    for i, q_paras in enumerate(questions, 1):
        # Nội dung câu hỏi
        q_text = re.sub(r'^Câu \d+[:.]', '', q_paras[0].text, flags=re.IGNORECASE).strip()
        quiz_doc.add_paragraph(f"Câu {i}: {q_text}")
        
        options = []
        for p in q_paras[1:]:
            # Kiểm tra gạch chân để xác định đáp án đúng
            is_correct = any(run.underline for run in p.runs)
            # Lọc nội dung, bỏ A. B. C. D. ở đầu dòng nếu có
            opt_text = re.sub(r'^[A-Z][\.\)]', '', p.text.strip()).strip()
            if opt_text:
                options.append({'text': opt_text, 'correct': is_correct})
        
        # Trộn phương án
        random.shuffle(options)
        
        # Tạo nhãn động (A, B, C, D...) dựa trên số lượng option thực tế
        # Tránh lỗi IndexError nếu có nhiều hơn 4 đáp án
        dynamic_labels = list(string.ascii_uppercase) # ['A', 'B', 'C', ...]
        
        for j, opt in enumerate(options):
            label = dynamic_labels[j] if j < len(dynamic_labels) else f"Op{j+1}"
            quiz_doc.add_paragraph(f"{label}. {opt['text']}")
            if opt['correct']:
                ans_key.append((i, label))
        
        quiz_doc.add_paragraph("")

    # Tạo file Đáp án
    key_doc = Document()
    key_doc.add_heading(f'ĐÁP ÁN MÃ ĐỀ: {code_name}', 1)
    table = key_doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    table.rows[0].cells[0].text = 'Câu'
    table.rows[0].cells[1].text = 'Đáp án'
    for q_num, a_val in ans_key:
        row = table.add_row().cells
        row[0].text = str(q_num)
        row[1].text = a_val

    q_buf = io.BytesIO(); quiz_doc.save(q_buf); q_buf.seek(0)
    k_buf = io.BytesIO(); key_doc.save(k_buf); k_buf.seek(0)
    return q_buf, k_buf

# --- GIAO DIỆN ---
st.markdown('<div class="logo-badge">TNMix</div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:white; margin-bottom:0;'>TNMix - Trộn đề trắc nghiệm</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info"><b>Giáo viên:</b> Nguyễn Văn Hà<br><b>Zalo:</b> 0907781595</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Tải lên file đề gốc (Gạch chân đáp án đúng)", type=["docx"])
    
    if uploaded_file:
        file_bytes = uploaded_file.read()
        num_codes = st.number_input("Số lượng mã đề cần tạo:", 1, 20, 4)
        
        if st.button("BẮT ĐẦU TRỘN ĐỀ & ĐÓNG GÓI ZIP", type="primary"):
            try:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                    for i in range(num_codes):
                        code = 100 + i + 1
                        q_buf, k_buf = process_single_code(file_bytes, str(code))
                        zip_file.writestr(f"De_Thi_Ma_{code}.docx", q_buf.getvalue())
                        zip_file.writestr(f"Dap_An_Ma_{code}.docx", k_buf.getvalue())
                
                st.success(f"✅ Đã tạo xong {num_codes} mã đề!")
                st.download_button(
                    label="📥 TẢI XUỐNG TẤT CẢ (FILE ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="Bo_De_Thi_Thay_Ha.zip",
                    mime="application/zip"
                )
            except Exception as e:
                st.error(f"Có lỗi xảy ra trong quá trình xử lý: {e}")
    else:
        st.info("💡 Lưu ý: File đề cần định dạng 'Câu 1:', 'Câu 2:'... Đáp án đúng cần được gạch chân chữ cái đầu.")
    st.markdown('</div>', unsafe_allow_html=True)
