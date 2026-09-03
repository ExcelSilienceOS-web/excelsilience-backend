from fastapi import FastAPI
from pydantic import BaseModel

# Inicialização do Motor do ExcelSilience OS
app = FastAPI(title="ExcelSilience OS Backend", version="1.0")

# 1. Estruturas de Dados (O que o site vai enviar para a nuvem)
class IntroData(BaseModel):
    pilot_id: str
    vsi_10: float

class Cap0Data(BaseModel):
    pilot_id: str
    esi_subjective: float

# 2. Rota de Teste de Ignição (Para sabermos se o servidor está online)
@app.get("/")
def health_check():
    return {"status": "Reator ExcelSilience OS Operacional e Blindado."}

# 3. Rota da Introdução (Captura Laríngea)
@app.post("/api/v1/intro")
def process_intro(data: IntroData):
    # Futuramente: Integração com MongoDB para salvar o VSI_10
    return {
        "status": "sucesso",
        "mensagem": "Assinatura laríngea registrada no cache.",
        "pilot_id": data.pilot_id,
        "vsi_10": data.vsi_10
    }

# 4. Rota do Capítulo 0 (Cálculo do ESI)
@app.post("/api/v1/cap0")
def process_cap0(data: Cap0Data):
    # Futuramente: Busca do VSI_10 no MongoDB e cálculo do esi_cap0
    return {
        "status": "sucesso",
        "mensagem": "Diagnóstico do Capítulo 0 processado.",
        "pilot_id": data.pilot_id
    }
