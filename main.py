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
   # 5. Rota do Capítulo 1 (Cálculo do IDS e ADC)
class Cap1Data(BaseModel):
    pilot_id: str

@app.post("/api/v1/cap1_diagnostico")
def process_cap1(data: Cap1Data):
    # 1. Puxa a memória do piloto no banco
    pilot = pilots_collection.find_one({"pilot_id": data.pilot_id})
    
    if not pilot or "vsi_10" not in pilot or "esi_cap0" not in pilot:
        return {"erro": "Faltam dados de telemetria. Conclua a Introdução e o Capítulo 0."}
    
    vsi = pilot["vsi_10"]
    esi = pilot["esi_cap0"]
    
    # 2. Calcula o Índice de Dissimulação Somática (IDS)
    ids = abs(vsi - esi)
    
    # 3. Trava de Segurança (Veto Biológico)
    # Se a discrepância entre mente e corpo for maior que 2.0, o sistema trava.
    if ids > 2.0:
        status_veto = "VETO BIOLÓGICO ATIVADO. Autoengano detectado."
        adc = 0.0 # O piloto perde a capacidade de decisão sob caos
    else:
        status_veto = "SISTEMA LIBERADO. Alinhamento somático verificado."
        # Matemática simplificada do ADC (Exemplo de baseline)
        adc = (vsi + esi) / 2
        
    # 4. Grava o resultado no chassi do piloto
    pilots_collection.update_one(
        {"pilot_id": data.pilot_id},
        {"$set": {
            "ids": ids,
            "adc": adc,
            "status_veto": status_veto
        }}
    )
    
    return {
        "status": "Diagnóstico do Capítulo 1 Concluído",
        "pilot_id": data.pilot_id,
        "ids": ids,
        "veto_biologico": status_veto,
        "adc_score": adc
    } 
        "status": "sucesso",
        "mensagem": "Diagnóstico ESI calculado e blindado no cache.",
        "pilot_id": data.pilot_id,
        "esi_cap0": esi_cap0
    }
