#!/usr/bin/env python3
"""
MCP Server para PocketBase - VerifiCuba
Conecta a PocketBase vía REST API y expone herramientas MCP.
"""
import os
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx
from mcp.server.fastmcp import FastMCP

# Configuración
POCKETBASE_URL = os.getenv("POCKETBASE_URL", "http://localhost:8090")
ADMIN_EMAIL = os.getenv("POCKETBASE_ADMIN_EMAIL", "arangorobe380@gmail.com")
ADMIN_PASSWORD = os.getenv("POCKETBASE_ADMIN_PASSWORD", "")

# Cliente HTTP global
client = httpx.AsyncClient(base_url=POCKETBASE_URL, timeout=30.0)

# MCP Server
mcp = FastMCP("pocketbase-verificuba")

# Cache de token admin
_admin_token: Optional[str] = None
_token_expiry: float = 0

async def get_admin_token() -> str:
    """Obtiene y cachea token de admin."""
    global _admin_token, _token_expiry
    import time
    if _admin_token and time.time() < _token_expiry:
        return _admin_token
    
    resp = await client.post("/api/admins/auth-with-password", json={
        "identity": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    resp.raise_for_status()
    data = resp.json()
    _admin_token = data["token"]
    _token_expiry = time.time() + 3600  # 1 hora
    return _admin_token

def auth_headers() -> Dict[str, str]:
    """Headers con token de admin."""
    token = asyncio.run(get_admin_token())
    return {"Authorization": f"Bearer {_admin_token}", "Content-Type": "application/json"}

# ===== HERRAMIENTAS MCP =====

@mcp.tool()
async def list_collections() -> str:
    """Lista todas las colecciones disponibles en PocketBase."""
    token = await get_admin_token()
    resp = await client.get("/api/collections", headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    data = resp.json()
    collections = data.get("items", [])
    result = [f"📋 Colecciones en PocketBase ({len(collections)}):"]
    for c in collections:
        ctype = "🔐" if c.get("type") == "auth" else "📊"
        result.append(f"  {ctype} {c['name']} ({c['id']}) - {c.get('type','base')}")
    return "\n".join(result)

@mcp.tool()
async def get_collection_schema(collection_name: str) -> str:
    """Obtiene el esquema (campos) de una colección."""
    token = await get_admin_token()
    resp = await client.get(f"/api/collections/{collection_name}", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 404:
        return f"❌ Colección '{collection_name}' no encontrada."
    resp.raise_for_status()
    data = resp.json()
    schema = data.get("schema", [])
    result = [f"📋 Esquema de '{collection_name}' ({len(schema)} campos):"]
    for field in schema:
        req = "🔴" if field.get("required") else "⚪"
        result.append(f"  {req} {field['name']}: {field['type']} {json.dumps(field.get('options', {}))}")
    return "\n".join(result)

@mcp.tool()
async def list_records(
    collection_name: str,
    page: int = 1,
    per_page: int = 20,
    filter_expr: str = "",
    sort: str = "-created",
    expand: str = ""
) -> str:
    """Lista registros de una colección con filtros y paginación."""
    token = await get_admin_token()
    params = {"page": page, "perPage": per_page, "sort": sort}
    if filter_expr:
        params["filter"] = filter_expr
    if expand:
        params["expand"] = expand
    
    resp = await client.get(
        f"/api/collections/{collection_name}/records",
        headers={"Authorization": f"Bearer {await get_admin_token()}"},
        params=params
    )
    if resp.status_code == 404:
        return f"❌ Colección '{collection_name}' no encontrada."
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    total = data.get("totalItems", 0)
    
    if not items:
        return f"📭 No hay registros en '{collection_name}' (total: {total})"
    
    result = [f"📋 {collection_name} - Página {page}/{data.get('totalPages',1)} (Total: {total}):"]
    for i, item in enumerate(items, 1):
        # Mostrar campos clave
        key_fields = []
        for k, v in item.items():
            if k not in ["id", "created", "updated", "collectionId", "collectionName"] and v is not None:
                key_fields.append(f"{k}={v}")
        result.append(f"  {i}. {', '.join(key_fields[:5])}... (id: {item['id']})")
    return "\n".join(result)

@mcp.tool()
async def get_record(collection_name: str, record_id: str, expand: str = "") -> str:
    """Obtiene un registro específico por ID."""
    token = await get_admin_token()
    params = {}
    if expand:
        params["expand"] = expand
    resp = await client.get(
        f"/api/collections/{collection_name}/records/{record_id}",
        headers={"Authorization": f"Bearer {await get_admin_token()}"},
        params=params
    )
    if resp.status_code == 404:
        return f"❌ Registro no encontrado."
    resp.raise_for_status()
    item = resp.json()
    return json.dumps(item, indent=2, ensure_ascii=False)

@mcp.tool()
async def create_record(collection_name: str, data: dict) -> str:
    """Crea un nuevo registro en una colección."""
    token = await get_admin_token()
    resp = await client.post(
        f"/api/collections/{collection_name}/records",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=data
    )
    if resp.status_code >= 400:
        return f"❌ Error: {resp.status_code} - {resp.text}"
    item = resp.json()
    return f"✅ Creado en {collection_name}: {item['id']}\n{json.dumps(item, indent=2, ensure_ascii=False)}"

@mcp.tool()
async def update_record(collection_name: str, record_id: str, data: dict) -> str:
    """Actualiza un registro existente."""
    token = await get_admin_token()
    resp = await client.patch(
        f"/api/collections/{collection_name}/records/{record_id}",
        headers={"Authorization": f"Bearer {await get_admin_token()}", "Content-Type": "application/json"},
        json=data
    )
    if resp.status_code >= 400:
        return f"❌ Error: {resp.status_code} - {resp.text}"
    item = resp.json()
    return f"✅ Actualizado {collection_name}/{record_id}\n{json.dumps(item, indent=2, ensure_ascii=False)}"

@mcp.tool()
async def delete_record(collection_name: str, record_id: str) -> str:
    """Elimina un registro."""
    token = await get_admin_token()
    resp = await client.delete(
        f"/api/collections/{collection_name}/records/{record_id}",
        headers={"Authorization": f"Bearer {await get_admin_token()}"}
    )
    if resp.status_code >= 400:
        return f"❌ Error: {resp.status_code} - {resp.text}"
    return f"✅ Eliminado {collection_name}/{record_id}"

@mcp.tool()
async def query_businesses(
    provincia: str = "",
    estado: str = "",
    categoria: str = "",
    limit: int = 20
) -> str:
    """Consulta negocios con filtros específicos para VerifiCuba."""
    filter_parts = []
    if provincia:
        filter_parts.append(f"provincia='{provincia}'")
    if estado:
        filter_parts.append(f"estado='{estado}'")
    if categoria:
        filter_parts.append(f"categoria='{categoria}'")
    
    filter_expr = " && ".join(filter_parts) if filter_parts else ""
    
    token = await get_admin_token()
    resp = await client.get(
        "/api/collections/negocios/records",
        headers={"Authorization": f"Bearer {await get_admin_token()}"},
        params={"page": 1, "perPage": limit, "sort": "-created", "filter": filter_expr, "expand": "categoria"}
    )
    resp.raise_for_status()
    data = resp.json()
    items = data.get("items", [])
    total = data.get("totalItems", 0)
    
    if not items:
        return f"📭 No hay negocios con esos filtros (total: {total})"
    
    result = [f"🏢 Negocios encontrados ({total}):"]
    for i, n in enumerate(items, 1):
        cat = n.get("expand", {}).get("categoria", {}).get("nombre", "Sin categoría")
        result.append(
            f"  {i}. 🏢 {n['nombre']} | 📂 {cat} | 📍 {n.get('municipio','')}, {n.get('provincia','')} | "
            f"🏷️ {n.get('estado','')} | 📱 {n.get('whatsapp','N/A')} | ID: {n['id']}"
        )
    return "\n".join(result)

@mcp.tool()
async def verify_business(record_id: str) -> str:
    """Marca un negocio como Verificado y plan Destacado."""
    return await update_record("negocios", record_id, {
        "estado": "Verificado",
        "plan": "Destacado",
        "fecha_verificacion": "2026-08-03"
    })

@mcp.tool()
async def business_stats() -> str:
    """Estadísticas generales de VerifiCuba."""
    token = await get_admin_token()
    
    # Contar por estado
    stats = {}
    for estado in ["Pendiente", "Verificado", "Activo", "Suspendido"]:
        resp = await client.get(
            "/api/collections/negocios/records",
            headers={"Authorization": f"Bearer {await get_admin_token()}"},
            params={"page": 1, "perPage": 1, "filter": f"estado='{estado}'"}
        )
        stats[estado] = resp.json().get("totalItems", 0)
    
    # Por provincia
    resp = await client.get("/api/collections/negocios/records", 
        headers={"Authorization": f"Bearer {await get_admin_token()}"},
        params={"perPage": 100, "fields": "provincia"})
    provincias = {}
    for n in resp.json().get("items", []):
        prov = n.get("provincia", "Sin provincia")
        provincias[prov] = provincias.get(prov, 0) + 1
    
    result = ["📊 VerifiCuba - Estadísticas"]
    result.append(f"🏪 Total: {sum(stats.values())}")
    for k, v in stats.items():
        result.append(f"  {k}: {v}")
    result.append(f"\n💰 Ingresos estimados (500 CUP/verificado): {(stats.get('Verificado',0)+stats.get('Activo',0))*500} CUP/mes")
    result.append("\n📍 Por provincia:")
    for p, c in sorted(provincias.items(), key=lambda x: -x[1]):
        result.append(f"  {p}: {c}")
    
    return "\n".join(result)

# ===== MAIN =====
if __name__ == "__main__":
    import sys
    print("🚀 PocketBase MCP Server - VerifiCuba", file=sys.stderr)
    print(f"  URL: {POCKETBASE_URL}", file=sys.stderr)
    print(f"  Admin: {ADMIN_EMAIL}", file=sys.stderr)
    print("  Tools: list_collections, get_collection_schema, list_records, get_record,", file=sys.stderr)
    print("         create_record, update_record, delete_record, query_businesses,", file=sys.stderr)
    print("         verify_business, business_stats", file=sys.stderr)
    mcp.run()
