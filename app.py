import streamlit as st
from docx import Document
from docx.oxml import OxmlElement
import io, re, random, zipfile, string, copy

# --- GIAO DIỆN THEO MẪU ---
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

# --- HÀM SAO CHÉP ĐOẠN VĂN GIỮ NGUYÊN HÌNH ẢNH ---
def copy_para_full(source_para, target_doc):
    new_p = target_doc.add_paragraph()
    new_p._p.append(copy.deepcopy(source_para._p))
    # Loại bỏ nội dung cũ để dán đè XML mới tránh bị lặp
    for p in new_p._p.xpath("./w:p"):
        if p != new_p._p: new_p._p.remove(p)
    return new_p

# --- LOGIC NHẬN DIỆN 3 PHẦN ---
def parse_exam_v3(file_stream):
    doc = Document(file_stream)
    parts = {"I": [], "II": [], "III": []}
    current_part = None
    current_q = []

    for para in doc.paragraphs:
        txt = para.text.strip().upper()
        if "PHẦN I" in txt: current_part = "I"; continue
        elif "PHẦN II" in txt: current_part = "II"; continue
        elif "PHẦN III" in txt: current_part = "III"; continue

        if current_part:
            # Nhận diện câu (Câu 1: hoặc 1.)
            if re.match(r'^(Câu|Câu hỏi)\s+\d+[:.]', para.text.strip(), re.I):
                if current_q: parts[current_part].append(current_q)
                current_q = [para]
            elif current_q: current_q.append(para)
            elif para.text.strip(): current_q = [para] # Trường hợp câu đầu tiên không có chữ "Câu"
            
    if current_q: parts[current_part].append(current_q)
    return parts

# --- TẠO ĐỀ VÀ ĐÁP ÁN ---
def create_exam_with_key(parts, code):
    doc = Document()
    doc.add_heading(f"MÃ ĐỀ: {code}", 0)
    keys = {"I": [], "II": [], "III": []}

    for p_label, p_key in [("PHẦN I", "I"), ("PHẦN II", "II"), ("PHẦN III", "III")]:
        if not parts[p_key]: continue
        doc.add_heading(p_label, level=1)
        qs = list(parts[p_key])
        random.shuffle(qs)

        for i, q_paras in enumerate(qs, 1):
            # Thân câu hỏi
            p0 = doc.add_paragraph()
            p0.add_run(f"Câu {i}: ").bold = True
            body = re.sub(r'^(Câu|Câu hỏi)\s+\d+[:.]', '', q_paras[0].text, flags=re.I).strip()
            p0.add_run(body)

            # Nội dung đi kèm (Hình ảnh, đáp án)
            for p in q_paras[1:]:
                # Lưu đáp án nếu có gạch chân (Phần I)
                if p_key == "I":
                    for run in p.runs:
                        if run.underline and re.match(r'^[A-D]', run.text.strip()):
                            keys["I"].append(f"{i}-{run.text.strip()[0]}")
                # Lưu key phần III nếu có thẻ <key=...>
                if p_key == "III":
                    match = re.search(r'<key=(.*?)>', p.text)
                    if match: keys["III"].append(f"{i}-{match.group(1)}")
                
                # Copy nguyên paragraph (Giữ hình ảnh)
                new_p = doc.add_paragraph()
                new_p._p.append(copy.deepcopy(p._p))
    
    buf = io.BytesIO(); doc.save(buf); buf.seek(0)
    return buf, keys

# --- GIAO DIỆN ---
st.markdown('<div class="logo-badge">TNMix</div>', unsafe_allow_html=True)
st.markdown("<h2 style='text-align:center; color:white;'>TNMix Pro - Nguyễn Văn Hà</h2>", unsafe_allow_html=True)
st.markdown(f'<div class="teacher-info">Zalo: 0907781595</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    uploaded = st.file_uploader("Chọn file đề gốc .docx", type=["docx"], label_visibility="collapsed")
    
    if uploaded:
        num = st.number_input("Số mã đề:", 1, 10, 4)
        if st.button("BẮT ĐẦU TRỘN ĐỀ", type="primary"):
            parts = parse_exam_v3(io.BytesIO(uploaded.read()))
            zip_buf = io.BytesIO()
            all_keys = []

            with zipfile.ZipFile(zip_buf, "a") as zf:
                for i in range(num):
                    c = 1201 + i
                    d_buf, k = create_exam_with_key(parts, c)
                    zf.writestr(f"De_{c}.docx", d_buf.getvalue())
                    all_keys.append((c, k))
                
                # Tạo file đáp án tổng hợp giống mẫu
                key_doc = Document()
                key_doc.add_heading("BẢNG ĐÁP ÁN TỔNG HỢP", 1)
                for c, k in all_keys:
                    key_doc.add_paragraph(f"MÃ ĐỀ {c}: " + ", ".join(k["I"] + k["III"]))
                
                k_buf = io.BytesIO(); key_doc.save(k_buf); k_buf.seek(0)
                zf.writestr("DapAn_TongHop.docx", k_buf.getvalue())

            st.success("Thành công! Hình ảnh và công thức đã được giữ nguyên.")
            st.download_button("📥 TẢI TRỌN BỘ (.ZIP)", zip_buf.getvalue(), "KetQua_TNMix.zip")
    st.markdown('</div>', unsafe_allow_html=True)
