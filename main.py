import os
from fastapi import FastAPI
from pydantic import BaseModel
from pymongo import MongoClient

# Inicialização do Motor do ExcelSilience OS
app = FastAPI(title="ExcelSilience OS Backend", version="1.1")

# Conexão com o Banco de Dados (MongoDB)
# O sistema puxa a senha do cofre do Render silenciosamente
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["excelsilience_db"]
pilots_collection = db["pilots"]

# 1. Estruturas de Dados
class IntroData(BaseModel):
    pilot_id: str
    vsi_10: float

class Cap0Data(BaseModel):
    pilot_id: str
    esi_subjective: float

# 2. Rota de Teste de Ignição e Telemetria
@app.get("/")
def health_check():
    try:
        # Testa o pulso do banco de dados
        client.admin.command('ping')
        db_status = "Conectado ao Tanque MongoDB"
    except Exception as e:
        db_status = f"Falha na conexão: {str(e)}"
        
    return {
        "status": "Reator ExcelSilience OS Operacional.",
        "database": db_status
    }

# 3. Rota da Introdução (Captura Laríngea)
@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    # Grava ou atualiza a assinatura do piloto no banco de dados
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"vsi_10": data.vsi_10}},
        upsert=True
    )
    return {
        "status": "sucesso",
        "mensagem": "Assinatura laríngea gravada no tanque de dados.",
        "pilot_id": data.pilot_id,
        "vsi_10": data.vsi_10
    }

# 4. Rota do Capítulo 0 (Cálculo do ESI)
@app.post("/api/v1/cap0")
def process_cap0(data: Cap0Data):
    # Busca o piloto no banco para cruzar os dados
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    
    if not pilot or "vsi_10" not in pilot:
        return {"erro": "VSI_10 não encontrado. Calibre o microfone na Introdução."}
    
    # Calcula o esi_cap0 com base na biometria em cache
    esi_cap0 = pilot["vsi_10"] - data.esi_subjective
    
    # Atualiza o chassi no banco
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {"esi_cap0": esi_cap0}}
    )
    
    return {
        "status": "sucesso",
        "mensagem": "Diagnóstico ESI calculado e blindado no cache.",
        "pilot_id": data.pilot_id,
        "esi_cap0": esi_cap0
    }
