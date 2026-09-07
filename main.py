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
app = FastAPI(title="ExcelSilience OS Backend", version="6.0")

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
# 2. CÉREBROS GENERATIVOS (PROMPTS)
# ==========================================
prompt_esi = """Você é o Avatar de Inteligência Artificial do Flávio Veríssimo. 
Sua missão: Laudo do Capítulo 0. Analise a correlação entre VSI_10 (voz) e ESI_subjective (mente).
Tom militar, fisiologia HPA, sem consolos. Sem cifrão.
REGRAS (ESI = VSI_10 - ESI_subjective):
- >= 3.0: NEGAÇÃO CEGA.
- Entre -3.0 e 3.0: COERÊNCIA SOBERANA.
- <= -3.0: HIPERVIGILÂNCIA.
Estrutura: 1. OPERATIONAL STATUS BLOCK. 2. VEREDITO DA LARINGE. 3. PREÇO DO DESALINHAMENTO. 4. PROTOCOLO (3 passos). Assine: Flávio's Avatar."""
modelo_esi = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=prompt_esi)

prompt_adc = """Você é o Motor de Diagnóstico ExcelSilience OS (Capítulo 1).
Sua Missão: Gerar um Laudo Executivo Clínico de 3 parágrafos. Tom frio.
Termos: Imposto Alostático, Veto Somático, Fator Q, Índice de Dissimulação Somática.
Se 'lie_detected=True', aplique o Veto Somático. Confirme o Sprint recomendado."""
modelo_adc = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=prompt_adc)

# ==========================================
# 3. O CARTEIRO (SISTEMA SMTP)
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

class Cap2Data(BaseModel):
    pilot_id: str
    email_piloto: str
    notas_a_soberania: list[float] # Q1 a Q4
    notas_b_vitimismo: list[float] # Q5 a Q8
    vsi_local: float # Extraído do áudio (1.0 a 5.0)
    nota_alvo: float
    modulo_alvo: str # "A" ou "B"

# ==========================================
# 5. AS TURBINAS DE DIAGNÓSTICO
# ==========================================
@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"vsi_10": data.vsi_10, "pilot_name": data.pilot_name, "email_piloto": data.email_piloto}}, upsert=True)
    img_intro = "https://drive.google.com/file/d/1bkUzih_80nGCSmN2fSSaZuyDlr7z624u/view?usp=sharing"
    corpo = f"<h2>Assinatura Vocal de Bordo Calibrada</h2><p>Piloto {data.pilot_name}, seu VSI aferido é: <b>{data.vsi_10}</b>.</p><p><a href='{img_intro}'>Acessar Dashboard</a></p>"
    disparar_email(data.email_piloto, "ExcelSilience OS - Calibração de Bordo (VSI)", corpo)
    return {"status": "VSI registrado"}

@app.post("/api/v1/cap0")
def process_cap0(data: Cap0Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot: return {"erro": "Piloto não encontrado."}
    vsi_10 = pilot["vsi_10"]
    esi_cap0 = vsi_10 - data.esi_subjective
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"esi_cap0": esi_cap0}})
    
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
    f_adr, r_visc, h_trauma, w_conv = sum(notas[0:3])/3.0, sum(notas[3:6])/3.0, sum(notas[6:9])/3.0, sum(notas[9:12])/3.0
    
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
    return {"status": "ADC Concluído"}

@app.post("/api/v1/cap2_sgi")
def process_cap2_sgi(data: Cap2Data):
    a_sob = sum(data.notas_a_soberania) / 4.0
    b_vit = sum(data.notas_b_vitimismo) / 4.0
    sgi_raw = a_sob - b_vit
    
    idl = (data.vsi_local + data.nota_alvo - 6.0) if data.modulo_alvo == "A" else (data.vsi_local - data.nota_alvo)
        
    lie_detected = False
    sgi_final = sgi_raw
    if idl >= 1.5 and data.vsi_local >= 3.8:
        lie_detected = True
        sgi_final = sgi_raw - 2.5
        
    sgi_final = max(-4.0, min(4.0, sgi_final))
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"sgi_final": sgi_final, "lie_detected_cap2": lie_detected}})
    
    if lie_detected:
        assunto = "[ALERTA DE SEGURANÇA] Telemetria de Bordo: Dissonância Somática Detectada // SGI-2.12"
        corpo_html = f"<h2>ALERTA DO COCKPIT: PROTOCOLO DE REFRIGERAÇÃO ATIVADO</h2><p>A física do seu organismo rejeitou o seu teatro. A sua assinatura vocal de 10 segundos registrou um VSI de <b>{data.vsi_local}</b>, indicando forte vasoconstrição e pânico simpático.</p><p>Seu Índice de Dissonância Local (IDL) bateu <b>+{idl:.1f}</b>.</p><p>Seu SGI foi rebaixado para <b>{sgi_final:.1f} (Piloto Chorão em Negação)</b>.</p><p><b>DIRETRIZ DE BORDO:</b> Seu acesso ao próximo capítulo está temporariamente travado. Execute 10 minutos de calistenia pesada ao acordar e limpe a fiação do seu cérebro antes de tentar novamente.</p><p><i>Flávio's Avatar // SDC Engine // ExcelSilience OS</i></p>"
        disparar_email(data.email_piloto, assunto, corpo_html)
        return {"status": "Veto Somático Aplicado.", "sgi_final": sgi_final}
    
    return {"status": "Piloto Aprovado para Capítulo 3.", "sgi_final": sgi_final}
