import os
import smtplib
from email.message import EmailMessage
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# ==========================================
# 1. INICIALIZAÇÃO DO MOTOR
# ==========================================
app = FastAPI(title="ExcelSilience OS Backend", version="5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.excelsilience.com.br", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
pilots_collection = client["excelsilience_db"]["pilots"]

# Configuração de IA
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# 2. CONFIGURAÇÃO DOS DOIS CÉREBROS (PROMPTS)
# ==========================================
prompt_esi = """Você é o Avatar de Inteligência Artificial do Flávio Veríssimo, o Arquiteto do ExcelSilience OS. 
Sua missão é realizar a calibração de bordo (Capítulo 0). Analise o nível de autoengano intelectual do piloto correlacionando a voz involuntária (VSI_10) com a mente consciente (ESI_subjective).
1. SINCERIDADE DE ENGENHARIA: Tom militar, focado na fisiologia do eixo HPA. Sem consolos.
2. DIRETO AO PONTO: Revelar o status imediatamente.
3. IDIOMA: Português.
4. EXCLUSÃO DE $: Não use cifrão.
REGRAS (ESI = VSI_10 - ESI_subjective):
- FAIXA 1: NEGAÇÃO CEGA (ESI >= 3.0). Risco iminente de colapso cognitivo.
- FAIXA 2: COERÊNCIA SOBERANA (-3.0 < ESI < 3.0). Sintonia biológica.
- FAIXA 3: HIPERVIGILÂNCIA DA ANSIEDADE (ESI <= -3.0). Estresse de software, não hardware.
ESTRUTURA: 
1. OPERATIONAL STATUS BLOCK (com nome, voz, declarado, ESI e diagnóstico). 
2. O VEREDITO DA LARINGE. 
3. O PREÇO DO DESALINHAMENTO. 
4. PROTOCOLO DE CALIBRAÇÃO DE CAPÍTULO (3 passos rápidos). Assine: Flávio's Avatar // SDC Engine // ExcelSilience OS."""

modelo_esi = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=prompt_esi)

prompt_adc = """Você é o Motor de Diagnóstico ExcelSilience OS. Analise os dados biométricos do C-Suite (Capítulo 1).
Sua Missão: Gerar um Laudo Executivo Clínico de 3 parágrafos. Tom frio, de engenharia de materiais.
Use os termos: Imposto Alostático, Veto Somático, Fator Q, Índice de Dissimulação Somática.
Se 'lie_detected=True', aplique o Veto Somático: a laringe não mente. Confirme o Sprint recomendado."""

modelo_adc = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=prompt_adc)

# ==========================================
# 3. O CARTEIRO (SISTEMA DE DISPARO SMTP)
# ==========================================
def disparar_email(destinatario: str, assunto: str, corpo_html: str):
    msg = EmailMessage()
    msg['Subject'] = assunto
    msg['From'] = os.getenv("GMAIL_REMETENTE")
    msg['To'] = destinatario
    msg['Bcc'] = "fvffonseca@gmail.com"
    msg.set_content(corpo_html, subtype='html')
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(os.getenv("GMAIL_REMETENTE"), os.getenv("GMAIL_APP_PASSWORD"))
            smtp.send_message(msg)
    except Exception as e:
        print(f"Falha na válvula de e-mail: {e}")

# ==========================================
# 4. ESTRUTURAS DE DADOS
# ==========================================
class IntroData(BaseModel):
    pilot_id: str
    pilot_name: str
    email_piloto: str
    vsi_10: float

class Cap0Data(BaseModel):
    pilot_id: str
    esi_subjective: float

class Cap1Data(BaseModel):
    pilot_id: str
    q_scores: list[float]
    hrv_raw_ms: float

# ==========================================
# 5. AS TRÊS TURBINAS DE DIAGNÓSTICO
# ==========================================
@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"vsi_10": data.vsi_10, "pilot_name": data.pilot_name, "email_piloto": data.email_piloto}}, upsert=True)
    
    img_intro = "https://drive.google.com/file/d/1bkUzih_80nGCSmN2fSSaZuyDlr7z624u/view?usp=sharing"
    corpo = f"<h2>Assinatura Vocal de Bordo Calibrada e Guardada</h2><p>Piloto {data.pilot_name}, seu VSI aferido é: <b>{data.vsi_10}</b>.</p><p><a href='{img_intro}'>Acessar Dashboard da Introdução</a></p>"
    
    disparar_email(data.email_piloto, "ExcelSilience OS - Calibração de Bordo (VSI)", corpo)
    return {"status": "VSI registrado"}

@app.post("/api/v1/cap0")
def process_cap0(data: Cap0Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot: return {"erro": "Piloto não encontrado."}
    
    vsi_10 = pilot["vsi_10"]
    esi_cap0 = vsi_10 - data.esi_subjective
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"esi_cap0": esi_cap0}})
    
    # Aciona a IA com as regras do ESI
    dados_ia = f"Piloto: {pilot['pilot_name']}. VSI_10: {vsi_10}. ESI_subjective: {data.esi_subjective}. ESI_cap0: {esi_cap0}."
    texto_laudo = modelo_esi.generate_content(dados_ia).text
    
    img_cap0 = "https://drive.google.com/file/d/1_xpYdIZXczS00rf2QeY3hQZLm9zCpfMD/view?usp=drive_link"
    corpo_email = f"{texto_laudo}<br><br><p><a href='{img_cap0}'>Acessar Black Box do ESI</a></p>"
    
    disparar_email(pilot["email_piloto"], "ExcelSilience OS - Laudo de Alinhamento (ESI)", corpo_email)
    return {"status": "Laudo ESI enviado"}

@app.post("/api/v1/cap1_diagnostico")
def process_cap1(data: Cap1Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    vsi = pilot.get("vsi_10", 0)
    esi_cap0 = pilot.get("esi_cap0", 0)
    notas = data.q_scores
    
    f_adr = sum(notas[0:3]) / 3.0
    r_visc = sum(notas[3:6]) / 3.0
    h_trauma = sum(notas[6:9]) / 3.0
    w_conv = sum(notas[9:12]) / 3.0
    
    t14_stress = ((f_adr + r_visc + h_trauma + (5.0 - w_conv)) / 4.0) * 2.0
    ids = vsi - t14_stress
    lie_detected = True if (ids >= 1.5) or (esi_cap0 >= 3.8 and t14_stress < 3.0) else False
    
    adc_raw = (f_adr + r_visc + h_trauma + (5.0 - w_conv) + max(f_adr, r_visc, h_trauma)) / 5.0
    adc_final = max(adc_raw, vsi / 2.0) if lie_detected else adc_raw
    sprint = "SPRINT 1: Refrigeração" if adc_final >= 3.0 else "SPRINT 2: Alinhamento" if adc_final >= 2.0 else "SPRINT 3: Alavancagem"
    
    dados_adc = f"VSI: {vsi}. ESI: {esi_cap0}. HRV: {data.hrv_raw_ms}ms. Estresse: {t14_stress}. Mentira: {lie_detected}. Sprint: {sprint}."
    texto_laudo_adc = modelo_adc.generate_content(dados_adc).text
    
    img_cap1 = "https://drive.google.com/file/d/11Zd_SWVEicpWcGvsCmxFZew6yelnCjWJ/view?usp=sharing"
    corpo_email_adc = f"{texto_laudo_adc}<br><br><a href='{img_cap1}'>Acessar Laudo Gráfico (ADC)</a>"
    
    disparar_email(pilot["email_piloto"], "ExcelSilience OS - Laudo Executivo ADC", corpo_email_adc)
    
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"adc_final": adc_final, "sprint": sprint}})
    return {"status": "ADC Supremo Concluído"}
