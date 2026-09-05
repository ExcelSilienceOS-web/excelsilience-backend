import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# ==========================================
# INICIALIZAÇÃO DO MOTOR
# ==========================================
app = FastAPI(title="ExcelSilience OS Backend", version="2.1")

# O Escudo de Segurança (CORS) - Liberando o seu site
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.excelsilience.com.br", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexão com o Banco de Dados (MongoDB)
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["excelsilience_db"]
pilots_collection = db["pilots"]

# ==========================================
# ESTRUTURAS DE DADOS (Modelos)
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
    idioma: str = "pt"  # O padrão é português, mas aceita "en"

# ==========================================
# ROTAS DE TELEMETRIA
# ==========================================

@app.get("/")
def health_check():
    return {"status": "Reator ExcelSilience OS Operacional.", "versao": "2.1"}

@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"vsi_10": data.vsi_10}},
        upsert=True
    )
    return {"status": "sucesso", "pilot_id": data.pilot_id, "vsi_10": data.vsi_10}

@app.post("/api/v1/cap0")
def process_cap0(data: Cap0Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot or "vsi_10" not in pilot:
        return {"erro": "VSI_10 não encontrado. Calibre o microfone na Introdução."}
    
    esi_cap0 = pilot["vsi_10"] - data.esi_subjective
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"esi_cap0": esi_cap0}}
    )
    return {"status": "sucesso", "pilot_id": data.pilot_id, "esi_cap0": esi_cap0}

@app.post("/api/v1/cap1_diagnostico")
def process_cap1(data: Cap1Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot or "vsi_10" not in pilot or "esi_cap0" not in pilot:
        return {"erro": "Faltam dados de telemetria base (VSI ou ESI)."}
    
    vsi = pilot["vsi_10"]
    esi_cap0 = pilot["esi_cap0"]
    notas = data.q_scores
    
    # Cálculos Matemáticos do Chassi
    f_adr = sum(notas[0:3]) / 3.0
    r_visc = sum(notas[3:6]) / 3.0
    h_trauma = sum(notas[6:9]) / 3.0
    w_conv = sum(notas[9:12]) / 3.0
    
    fator_conversao = 5.0 - w_conv
    hrv_norm = min(10.0, data.hrv_raw_ms / 10.0)
    
    # Detector de Mentiras (Veto Biológico)
    t14_stress = ((f_adr + r_visc + h_trauma + fator_conversao) / 4.0) * 2.0
    ids = vsi - t14_stress
    
    lie_detected = True if (ids >= 1.5) or (esi_cap0 >= 3.8 and t14_stress < 3.0) else False
    
    # Acurácia de Decisão sob Caos (ADC)
    adc_raw = (f_adr + r_visc + h_trauma + fator_conversao + max(f_adr, r_visc, h_trauma)) / 5.0
    adc_final = max(adc_raw, vsi / 2.0) if lie_detected else adc_raw
    
    # Roteamento de Idioma para o Laudo
    if data.idioma == "en":
        status_msg = "Diagnosis Complete"
        sprint_nome = "SPRINT 1: Emergency Cooling" if adc_final >= 3.0 else "SPRINT 2: Force Alignment" if adc_final >= 2.0 else "SPRINT 3: Convex Leverage"
        laudo_img = "LINK_DO_DRIVE_ADC_INGLES" 
    else:
        status_msg = "Diagnóstico Concluído"
        sprint_nome = "SPRINT 1: Refrigeração" if adc_final >= 3.0 else "SPRINT 2: Alinhamento de Forças" if adc_final >= 2.0 else "SPRINT 3: Alavancagem Convexa"
        laudo_img = "https://drive.google.com/file/d/11Zd_SWVEicpWcGvsCmxFZew6yelnCjWJ/view?usp=sharing"

    # Gravação no Banco de Dados
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"adc_final": adc_final, "ids": ids, "sprint": sprint_nome}}
    )
    
    return {
        "status": status_msg,
        "lie_detected": lie_detected,
        "adc_final": adc_final,
        "sprint_recomendado": sprint_nome,
        "laudo_visual": laudo_img
    }
