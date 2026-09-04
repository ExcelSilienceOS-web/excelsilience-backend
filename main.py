import os
from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient

# Inicialização do Motor do ExcelSilience OS
app = FastAPI(title="ExcelSilience OS Backend", version="1.2")

# Conexão com o Banco de Dados
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["excelsilience_db"]
pilots_collection = db["pilots"]

# ==========================================
# 1. ESTRUTURAS DE DADOS (Modelos)
# ==========================================
class IntroData(BaseModel):
    pilot_id: str
    vsi_10: float

class Cap0Data(BaseModel):
    pilot_id: str
    esi_subjective: float

class Cap1Data(BaseModel):
    pilot_id: str

# ==========================================
# 2. ROTAS DA API
# ==========================================

# Rota de Ignição
@app.get("/")
def health_check():
    return {"status": "Reator ExcelSilience OS Operacional.", "versao": "1.2"}

# Introdução (Captura Laríngea)
@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"vsi_10": data.vsi_10}},
        upsert=True
    )
    return {"status": "sucesso", "pilot_id": data.pilot_id, "vsi_10": data.vsi_10}

# Capítulo 0 (Cálculo do ESI)
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

# Capítulo 1 (Cálculo do IDS e Veto Biológico)
@app.post("/api/v1/cap1_diagnostico")
def process_cap1(data: Cap1Data):
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    if not pilot or "vsi_10" not in pilot or "esi_cap0" not in pilot:
        return {"erro": "Faltam dados. Conclua a Intro e o Cap 0."}
    
    vsi = pilot["vsi_10"]
    esi = pilot["esi_cap0"]
    ids = abs(vsi - esi)
    
    if ids > 2.0:
        status_veto = "VETO BIOLÓGICO ATIVADO. Autoengano detectado."
        adc = 0.0
    else:
        status_veto = "SISTEMA LIBERADO. Alinhamento somático verificado."
        adc = (vsi + esi) / 2
        
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"ids": ids, "adc": adc, "status_veto": status_veto}}
    )
    
    return {
        "status": "Diagnóstico do Cap 1 Concluído",
        "pilot_id": data.pilot_id,
        "ids": ids,
        "veto_biologico": status_veto,
        "adc_score": adc
    }
