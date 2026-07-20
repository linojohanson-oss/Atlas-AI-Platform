ATLAS AI - WORKFLOW ENGINE V1
=============================

1. Cerrá Uvicorn si está ejecutándose.

2. Copiá la carpeta "atlas/workflows" dentro de tu proyecto:
   Atlas-AI\atlas\workflows

3. Reemplazá:
   Atlas-AI\atlas\kernel\kernel.py

4. Reemplazá:
   Atlas-AI\app\api\main.py

5. Desde la raíz del proyecto ejecutá:

   .\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload

6. Abrí:
   http://127.0.0.1:8000/docs

7. Probá POST /workflows/execute con:

{
  "prompt": "Diseñá una solución de IA generativa para analizar y priorizar reclamos de clientes de un banco.",
  "workflow": "enterprise_ai_solution"
}

También podés probar desde PowerShell:

$body = @{
    prompt = "Diseñá una solución de IA generativa para analizar y priorizar reclamos de clientes de un banco."
    workflow = "enterprise_ai_solution"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/workflows/execute" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body | ConvertTo-Json -Depth 20

NUEVOS ENDPOINTS
================
POST /workflows/execute
GET  /workflows/history
GET  /workflows/last

ARCHIVO DE TRAZABILIDAD
=======================
Se crea automáticamente dentro de memory_dir:

workflow_history.jsonl
