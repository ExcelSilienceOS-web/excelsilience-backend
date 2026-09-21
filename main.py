import json
import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ExcelSilience SRT Backend")

# Libera acesso para o GitHub Pages (Dashboard e Index)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "banco_testes.json"


def load_records():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def save_records(records):
  try:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
      json.dump(records, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"Erro ao salvar arquivo: {e}", flush=True)


@app.get("/")
def home():
  return {"status": "SRT Bio-Health API Online", "total_records": len(load_records())}


@app.get("/api/v1/smartwatch/sync")
def get_records():
  # Retorna o histórico salvo no arquivo permanente
  return load_records()


@app.post("/api/v1/smartwatch/sync")
async def receive_sync(request: Request):
  try:
    data = await request.json()

    # 1. IMPRESSÃO FORÇADA NOS LOGS DO RENDER (Impossível perder)
    print("========================================", flush=True)
    print(
        f"🚨 NOVO CHECK-IN RECEBIDO [{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}]",
        flush=True,
    )
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)
    print("========================================", flush=True)

    # 2. EXTRAÇÃO E FORMATACÃO DOS DADOS
    telemetry = data.get("telemetry", {})
    new_record = {
        "timestamp": datetime.now().strftime("%H:%M"),
        "company": data.get("company")
        or data.get("empresa")
        or "ExcelSilience Direct",
        "name": data.get("name") or data.get("nome") or "Operador",
        "whatsapp": data.get("whatsapp") or data.get("user_id") or "N/A",
        "sector": data.get("sector") or data.get("setor") or "Operacional",
        "reaction_ms": telemetry.get("reaction_ms")
        or data.get("reaction_ms")
        or 0,
        "veto_errors": telemetry.get("veto_errors")
        if telemetry.get("veto_errors") is not None
        else data.get("veto_errors", 0),
        "status": telemetry.get("status") or data.get("status") or "GREEN",
        "date_iso": datetime.now().isoformat(),
    }

    # 3. GRAVAÇÃO NO BANCO FIXO
    records = load_records()
    records.insert(0, new_record)  # Coloca o mais recente no topo
    save_records(records)

    return {"status": "success", "message": "Check-in gravado com sucesso!", "record": new_record}

  except Exception as e:
    print(f"❌ ERRO AO PROCESSAR SYNC: {e}", flush=True)
    return {"status": "error", "detail": str(e)}
