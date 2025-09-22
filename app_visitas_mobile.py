# -*- coding: utf-8 -*-
# Versão mobile com câmera nativa do Streamlit (sem libs extras)
import os, re, unicodedata, tempfile
from datetime import date
from io import BytesIO

import streamlit as st
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Visita - Banana (Mobile)", layout="wide")

def sanitize_filename(name: str) -> str:
    if not name:
        return "Relatorio"
    nfkd = unicodedata.normalize("NFKD", name)
    name_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    name_ascii = re.sub(r'[\\/:*?"<>|]+', "_", name_ascii)
    name_ascii = re.sub(r"\s+", "_", name_ascii).strip("_")
    return name_ascii or "Relatorio"

def save_bytes_as_png(img_bytes: bytes) -> str:
    img = Image.open(BytesIO(img_bytes))
    if img.mode not in ("RGB", "RGBA", "L"):
        img = img.convert("RGB")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name, "PNG")
    tmp.flush()
    tmp.close()
    return tmp.name

def add_wrapped(pdf, text, lh=6):
    if not text:
        return
    pdf.multi_cell(0, lh, text)

# ----- Sidebar -----
st.sidebar.title("Configurações")
consultor = st.sidebar.text_input("Consultor", value="Seu Nome")
empresa = st.sidebar.text_input("Empresa", value="Comtécnica Agro")
logo_upload = st.sidebar.file_uploader("Logomarca (PNG/JPG)", type=["png","jpg","jpeg"])
assinatura_upload = st.sidebar.file_uploader("Assinatura (PNG transparência)", type=["png"])
tema_55 = st.sidebar.checkbox("Exibir 'Comtécnica 55 anos' na capa", value=True)

DEFAULT_LOGO = "logo_placeholder.png"
logo_bytes = None
if logo_upload is not None:
    logo_bytes = logo_upload.read()
elif os.path.exists(DEFAULT_LOGO):
    with open(DEFAULT_LOGO, "rb") as f:
        logo_bytes = f.read()

assinatura_bytes = assinatura_upload.read() if assinatura_upload else None

# ----- Cabeçalho -----
st.title("Visita Técnica - Bananeicultura (Mobile)")

c1, c2 = st.columns(2)
with c1:
    produtor = st.text_input("Produtor")
    propriedade = st.text_input("Propriedade / Fazenda")
    area = st.number_input("Área (ha)", min_value=0.0, step=0.1, value=0.0)
    talhoes_lista = st.text_input("Talhões/Glebas (separe por vírgula)", placeholder="Ex.: Talhão A, Talhão B")
with c2:
    cidade = st.text_input("Cidade")
    bairro = st.text_input("Bairro / Localidade")
    data_visita = st.date_input("Data da Visita", value=date.today())
    proxima_visita = st.date_input("Próxima Visita (estimada)", value=date.today())

st.markdown('---')

# ----- Itens -----
st.subheader('Itens da Visita')
if 'itens' not in st.session_state:
    st.session_state.itens = []

def add_item_from_upload(file):
    st.session_state.itens.append({
        'img_bytes': file.read(),
        'nome': file.name,
        'talhao': '',
        'cats': [],
        'anot': '',
        'reco': ''
    })

def add_item_from_camera(img_bytes):
    st.session_state.itens.append({
        'img_bytes': img_bytes,
        'nome': 'foto_camera.png',
        'talhao': '',
        'cats': [],
        'anot': '',
        'reco': ''
    })

colU, colC = st.columns(2)
with colU:
    uploads = st.file_uploader('Adicionar fotos (galeria)', type=['png','jpg','jpeg'], accept_multiple_files=True)
    if uploads:
        for f in uploads:
            add_item_from_upload(f)
with colC:
    st.caption("Ou tirar foto agora:")
    foto = st.camera_input("Tirar foto")
    if foto is not None:
        add_item_from_camera(foto.getvalue())

talhoes_opcoes = [t.strip() for t in talhoes_lista.split(',') if t.strip()]
cat_opcoes = ['Praga', 'Doença', 'Destaque', 'Resultado de Tratamento']

for i, item in enumerate(st.session_state.itens):
    st.markdown(f'#### Item {i+1}')
    colA, colB = st.columns([1,1])
    with colA:
        try:
            img = Image.open(BytesIO(item['img_bytes']))
            st.image(img, use_container_width=True)
        except Exception as e:
            st.warning(f'Imagem inválida: {e}')
    with colB:
        if talhoes_opcoes:
            item['talhao'] = st.selectbox('Talhão/Gleba', ['(não informado)'] + talhoes_opcoes, index=0, key=f'talhao_{i}')
        else:
            item['talhao'] = st.text_input('Talhão/Gleba', value=item['talhao'], key=f'talhao_{i}')
        item['cats'] = st.multiselect('Categorias', cat_opcoes, default=item['cats'], key=f'cats_{i}')
        item['anot'] = st.text_area('Anotações', value=item['anot'], key=f'anot_{i}')
        item['reco'] = st.text_area('Recomendações', value=item['reco'], key=f'reco_{i}')
    st.divider()

st.subheader('Recomendação Geral')
reco_geral = st.text_area('Escreva a recomendação geral para toda a área', height=140)

def gerar_pdf():
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)

    # Capa
    pdf.add_page()
    if logo_bytes:
        try:
            logo_path = save_bytes_as_png(logo_bytes)
            pdf.image(logo_path, x=60, y=20, w=90)
            try: os.unlink(logo_path)
            except: pass
        except Exception as e:
            st.warning(f'Logo não pôde ser processada na capa: {e}')
    pdf.set_xy(10, 80)
    pdf.set_font('Arial', 'B', 22)
    pdf.cell(0, 12, 'Relatório de Visita - Bananeicultura', ln=1, align='C')

    pdf.set_font('Arial', '', 12)
    pdf.ln(4)
    pdf.cell(0, 8, f'Consultor: {consultor}  |  Empresa: {empresa}', ln=1, align='C')
    pdf.cell(0, 8, f'Produtor: {produtor}  |  Propriedade: {propriedade}', ln=1, align='C')
    pdf.cell(0, 8, f'Cidade: {cidade}  |  Bairro: {bairro}', ln=1, align='C')
    pdf.cell(0, 8, f'Área: {area:.2f} ha  |  Data: {data_visita.strftime("%d/%m/%Y")}', ln=1, align='C')
    if tema_55:
        pdf.ln(4)
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Comtécnica 55 anos (1970–2025)', ln=1, align='C')

    # Conteúdo
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 8, 'Cabeçalho da Visita', ln=1)
    pdf.set_font('Arial', size=11)
    pdf.multi_cell(0, 6, f'Talhões/Glebas: {talhoes_lista}')
    pdf.multi_cell(0, 6, f'Próxima visita (estimada): {proxima_visita.strftime("%d/%m/%Y")}')
    pdf.ln(2)
    pdf.set_draw_color(180,180,180); pdf.set_line_width(0.4)
    y = pdf.get_y(); pdf.line(10, y, 200, y); pdf.ln(5)

    for idx, it in enumerate(st.session_state.itens, start=1):
        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 8, f'Item {idx}', ln=1)
        try:
            img_path = save_bytes_as_png(it['img_bytes'])
            pdf.image(img_path, x=15, w=180)
            try: os.unlink(img_path)
            except: pass
        except Exception as e:
            pdf.set_font('Arial', 'I', 10)
            pdf.cell(0, 6, f'(Imagem não pôde ser processada: {e})', ln=1)

        pdf.ln(3)
        pdf.set_font('Arial', '', 11)
        talhao_txt = it['talhao'] if it['talhao'] else '(não informado)'
        cats_txt = ', '.join(it['cats']) if it['cats'] else '(sem categoria)'
        pdf.multi_cell(0, 6, f'Talhão/Gleba: {talhao_txt}')
        pdf.multi_cell(0, 6, f'Categorias: {cats_txt}')
        pdf.ln(1)
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 6, 'Anotações:', ln=1)
        pdf.set_font('Arial', '', 11); pdf.multi_cell(0, 6, it['anot'])
        pdf.ln(1)
        pdf.set_font('Arial', 'B', 12); pdf.cell(0, 6, 'Recomendações:', ln=1)
        pdf.set_font('Arial', '', 11); pdf.multi_cell(0, 6, it['reco'])

        pdf.ln(4)
        pdf.set_draw_color(210,210,210); pdf.set_line_width(0.2)
        y = pdf.get_y(); pdf.line(10, y, 200, y); pdf.ln(4)

    if reco_geral.strip():
        pdf.set_font('Arial', 'B', 13)
        pdf.cell(0, 8, 'Recomendação Geral', ln=1)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 6, reco_geral)

    if assinatura_bytes:
        try:
            sign_path = save_bytes_as_png(assinatura_bytes)
            pdf.ln(10)
            pdf.set_font('Arial', 'I', 10)
            pdf.cell(0, 6, 'Assinado eletronicamente pelo consultor:', ln=1)
            pdf.image(sign_path, x=80, w=50)
            try: os.unlink(sign_path)
            except: pass
        except Exception:
            pass

    base_dir = os.getcwd()
    out_dir = os.path.join(base_dir, 'Relatorios')
    os.makedirs(out_dir, exist_ok=True)
    safe = sanitize_filename(produtor)
    fname = f'Relatorio_Visita_{safe}_{date.today().strftime("%Y%m%d")}.pdf'
    out_path = os.path.join(out_dir, fname)
    try:
        pdf.output(out_path)
    except Exception as e:
        st.error(f'Erro ao salvar PDF: {e}')
        return None, None
    with open(out_path, 'rb') as f:
        pdf_bytes = f.read()
    return pdf_bytes, out_path

col1, col2 = st.columns([1,2])
with col1:
    gerar = st.button('Gerar PDF', use_container_width=True)

if gerar:
    pdf_bytes, path = gerar_pdf()
    if pdf_bytes:
        st.success('PDF gerado com sucesso!')
        st.download_button('Baixar PDF', data=pdf_bytes, file_name=os.path.basename(path), mime='application/pdf', use_container_width=True)
        st.caption(f'Salvo em: {path}')
    else:
        st.error('Falha ao gerar o PDF.')
