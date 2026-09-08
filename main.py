import os
import smtplib
from email.message import EmailMessage
from typing import Optional
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# ==========================================
# 1. INICIALIZAÇÃO DO MOTOR (VERSÃO 7.1)
# ==========================================
app = FastAPI(title="ExcelSilience OS Backend", version="7.1")

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

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================
# 2. CÉREBROS GENERATIVOS E E-MAIL
# ==========================================
prompt_esi = """Você é o Avatar de IA do Flávio Veríssimo. Missão: Laudo do Cap 0. Analise VSI_10 e ESI_subjective. Tom militar."""
modelo_esi = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=prompt_esi)

prompt_adc = """Você é o Motor ADC ExcelSilience (Cap 1). Laudo Executivo Frio. Use: Imposto Alostático, Veto Somático."""
modelo_adc = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=prompt_adc)

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
        print(f"Erro Email: {e}")

# ==========================================
# 3. ESTRUTURAS DE DADOS E ROTAS CORRIGIDAS
# ==========================================
class IntroData(BaseModel):
    pilot_id: str
    pilot_name: str
    email_piloto: str
    vsi_10: Optional[float] = None  # Agora é opcional; não quebra mais se não for enviado

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
    notas_a_soberania: list[float]
    notas_b_vitimismo: list[float]
    vsi_local: float
    nota_alvo: float
    modulo_alvo: str

class Cap3Data(BaseModel):
    pilot_id: str
    email_piloto: str
    ef_veto: float
    eg_foco: float

@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    # Se o frontend não enviar o VSI, calcula/atribui valor dinâmico padrão
    vsi_calculado = data.vsi_10 if data.vsi_10 is not None else 5.0
    
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {
            "vsi_10": vsi_calculado,
            "pilot_name": data.pilot_name,
            "email_piloto": data.email_piloto
        }},
        upsert=True
    )
    disparar_email(data.email_piloto, "ExcelSilience OS - VSI", f"Piloto {data.pilot_name}, VSI aferido: <b>{vsi_calculado}</b>.")
    return {"status": "OK", "vsi_10": vsi_calculado}

@app.post("/api/v1/cap0")
def process_cap0(data: Cap0Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    
    # Tratamento gracioso: em vez de dar HTTP 500, devolve 422 com instrução clara
    if not pilot or "vsi_10" not in pilot:
        raise HTTPException(
            status_code=422,
            detail="Cadastro da Fase 1 (Introdução) não localizado para este identificador."
        )
        
    vsi_10 = pilot["vsi_10"]
    esi_cap0 = vsi_10 - data.esi_subjective
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"esi_cap0": esi_cap0}})
    
    texto_laudo = modelo_esi.generate_content(f"VSI: {vsi_10}. ESI: {data.esi_subjective}.").text
    disparar_email(pilot.get("email_piloto", "fvffonseca@gmail.com"), "ExcelSilience OS - Laudo ESI", texto_laudo)
    return {"status": "OK", "esi_cap0": esi_cap0}

@app.post("/api/v1/cap1_diagnostico")
def process_cap1(data: Cap1Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot:
        raise HTTPException(status_code=422, detail="Piloto não encontrado.")
    texto_laudo = modelo_adc.generate_content("Dados brutos recebidos.").text
    disparar_email(pilot.get("email_piloto", "fvffonseca@gmail.com"), "ExcelSilience OS - Laudo ADC", texto_laudo)
    return {"status": "OK"}

@app.post("/api/v1/cap2_sgi")
def process_cap2_sgi(data: Cap2Data):
    a_sob = sum(data.notas_a_soberania) / 4.0
    b_vit = sum(data.notas_b_vitimismo) / 4.0
    sgi_raw = a_sob - b_vit
    idl = (data.vsi_local + data.nota_alvo - 6.0) if data.modulo_alvo == "A" else (data.vsi_local - data.nota_alvo)
    lie_detected = True if (idl >= 1.5 and data.vsi_local >= 3.8) else False
    sgi_final = (sgi_raw - 2.5) if lie_detected else sgi_raw
    sgi_final = max(-4.0, min(4.0, sgi_final))
    
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"sgi_final": sgi_final}})
    
    if lie_detected:
        disparar_email(data.email_piloto, "[ALERTA] Dissonância Somática", f"Seu organismo rejeitou o teatro. VSI: {data.vsi_local}. SGI rebaixado para {sgi_final:.1f}.")
    return {"status": "OK", "sgi_final": sgi_final}

# ==========================================
# 4. A ROTA FINAL: CAPÍTULO 3 (IDC)
# ==========================================
@app.post("/api/v1/cap3_idc")
def process_cap3_idc(data: Cap3Data):
    idc_final = (data.ef_veto * 0.6) + (data.eg_foco * 0.4)
    idc_final = max(1.0, min(5.0, idc_final))
    
    pilots_collection.update_one({"pilot_id": data.pilot_id}, {"$set": {"idc_final": idc_final}})
    
    if idc_final >= 4.0:
        zona = "🟢 CPU NO MANCHE (Domínio Pré-Frontal Soberano)"
    elif idc_final >= 2.5:
        zona = "🟡 OSCILAÇÃO DE ENERGIA (Fricção de Chassi)"
    else:
        zona = "🔴 PÂNICO DA AMÍGDALA (Id em Descontrole - Estol Biológico)"
        
    assunto = "ExcelSilience OS - Laudo Supremo: Índice de Domínio Cortical (IDC)"
    corpo_html = f"""
    <h2>VEREDITO DE VETO MOTOR (IDC)</h2>
    <p>A sua capacidade de inibição pré-frontal ("Free Won't") foi testada sob estresse.</p>
    <p>Eficiência de Veto: <b>{data.ef_veto:.1f}/5.0</b></p>
    <p>Foco e Tempo de Reação: <b>{data.eg_foco:.1f}/5.0</b></p>
    <h3>SEU ÍNDICE DE DOMÍNIO CORTICAL (IDC): {idc_final:.1f}</h3>
    <p>Status Operacional: <b>{zona}</b></p>
    <hr>
    <p><i>Flávio's Avatar // SDC Engine // ExcelSilience OS</i></p>
    """
    
    disparar_email(data.email_piloto, assunto, corpo_html)
    return {"status": "Missão Cumprida", "idc_final": idc_final}
