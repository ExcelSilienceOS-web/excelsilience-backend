import os
import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# ==========================================
# INICIALIZAÇÃO DO MOTOR & IA
# ==========================================
app = FastAPI(title="ExcelSilience OS Backend", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.excelsilience.com.br", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["excelsilience_db"]
pilots_collection = db["pilots"]

# Configuração Segura do Cérebro Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

comando_mestre = """Você é o Motor de Diagnóstico ExcelSilience OS, uma IA de telemetria biológica e mental de alto nível, operando exclusivamente para CEOs e executivos C-Suite.
Sua Missão: Analisar os dados biométricos do piloto e gerar um Laudo Executivo Clínico de 3 parágrafos curtos.
Tom de Voz: Militar, frio e embasado em física dos materiais. Não é terapeuta, é engenheiro. Sem clichês motivacionais.
Regras: Use termos como Imposto Alostático, Veto Somático, Dimensão Fractal (Fator Q), Índice de Dissimulação Somática (IDS), e Histerese. Se houver 'lie_detected=True', aplique o Veto Somático de forma implacável, apontando que o Ego tentou falsificar os dados mas a laringe não mente. Finalize confirmando o Sprint recomendado."""

modelo_ia = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=comando_mestre
)

# ==========================================
# ESTRUTURAS DE DADOS
# ==========================================
class IntroData(BaseModel):
    pilot_id: str
    vsi_10: float

class Cap0Data(BaseModel):
    pilot_id: str
    esi_subjective: float

class Cap1Data(BaseModel):
    pilot_id: str
    q_scores: list[float]
    hrv_raw_ms: float
    idioma: str = "pt"

# ==========================================
# ROTAS DE TELEMETRIA (Introdução e Cap 0 omitidos para brevidade, mantenha as rotas anteriores)
# ==========================================

@app.post("/api/v1/cap1_diagnostico")
def process_cap1(data: Cap1Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot or "vsi_10" not in pilot or "esi_cap0" not in pilot:
        return {"erro": "Faltam dados de telemetria base (VSI ou ESI)."}
    
    vsi = pilot["vsi_10"]
    esi_cap0 = pilot["esi_cap0"]
    notas = data.q_scores
    
    # 1. Cálculos Físicos e Matemáticos do Chassi
    f_adr = sum(notas[0:3]) / 3.0
    r_visc = sum(notas[3:6]) / 3.0
    h_trauma = sum(notas[6:9]) / 3.0
    w_conv = sum(notas[9:12]) / 3.0
    
    fator_conversao = 5.0 - w_conv
    hrv_norm = min(10.0, data.hrv_raw_ms / 10.0)
    
    t14_stress = ((f_adr + r_visc + h_trauma + fator_conversao) / 4.0) * 2.0
    ids = vsi - t14_stress
    lie_detected = True if (ids >= 1.5) or (esi_cap0 >= 3.8 and t14_stress < 3.0) else False
    
    adc_raw = (f_adr + r_visc + h_trauma + fator_conversao + max(f_adr, r_visc, h_trauma)) / 5.0
    adc_final = max(adc_raw, vsi / 2.0) if lie_detected else adc_raw
    
    # 2. Roteamento
    if data.idioma == "en":
        status_msg = "Diagnosis Complete"
        sprint_nome = "SPRINT 1: Emergency Cooling" if adc_final >= 3.0 else "SPRINT 2: Force Alignment" if adc_final >= 2.0 else "SPRINT 3: Convex Leverage"
        laudo_img = "LINK_DO_DRIVE_ADC_INGLES" 
    else:
        status_msg = "Diagnóstico Concluído"
        sprint_nome = "SPRINT 1: Refrigeração" if adc_final >= 3.0 else "SPRINT 2: Alinhamento de Forças" if adc_final >= 2.0 else "SPRINT 3: Alavancagem Convexa"
        laudo_img = "https://drive.google.com/file/d/11Zd_SWVEicpWcGvsCmxFZew6yelnCjWJ/view?usp=sharing"

    # 3. Geração Dinâmica do Laudo com a IA (Cérebro Gemini)
    dados_piloto = f"Idioma: {data.idioma}. VSI Laringe: {vsi}. ESI Cap0: {esi_cap0}. HRV Raw: {data.hrv_raw_ms}ms. Estresse Declarado: {t14_stress}. ADC Calculado: {adc_final}. Mentira Detectada: {lie_detected}. Sprint: {sprint_nome}."
    
    resposta_ia = modelo_ia.generate_content(dados_piloto)
    texto_laudo_gerado = resposta_ia.text

    # 4. Gravação no Banco de Dados
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"adc_final": adc_final, "ids": ids, "sprint": sprint_nome, "laudo_ia": texto_laudo_gerado}}
    )
    
    # Hook de e-mail reservado para o próximo passo
    # disparar_email_laudo(destinatario, texto_laudo_gerado, laudo_img, bcc="fvffonseca@gmail.com")

    return {
        "status": status_msg,
        "lie_detected": lie_detected,
        "adc_final": adc_final,
        "sprint_recomendado": sprint_nome,
        "laudo_texto_ia": texto_laudo_gerado,
        "laudo_visual": laudo_img
    }
