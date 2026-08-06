import re

with open('index.html', 'r') as f:
    content = f.read()

# 1. Eliminar el bloque de warning CORS (busca y elimina el div con el warning)
cors_warning_pattern = r'<div style="[^>]*">\s*⚠️ <strong>Nota:</strong> El envío directo desde el navegador está bloqueado por CORS\..*?</div>'
content = re.sub(cors_warning_pattern, '', content, flags=re.DOTALL)

# 2. Actualizar stats hardcodeadas a dinámicas (0 por defecto)
content = content.replace('id="stat-negocios">12', 'id="stat-negocios">0')
content = content.replace('id="stat-verificados">8', 'id="stat-verificados">0')
content = content.replace('id="stat-categorias">12', 'id="stat-categorias">12')

# 3. Reemplazar WhatsApp placeholder en botón flotante y footer
content = content.replace('535XXXXXXX', '5351234567')  # Reemplaza con tu número real

# 4. Actualizar PB_URL placeholder a comentario
content = content.replace(
    "const PB_URL = 'https://verificuba.trycloudflare.com';",
    "// const PB_URL = 'https://TU_TUNNEL.trycloudflare.com'; // Cambia cuando tengas tunnel\n    const PB_URL = 'http://localhost:8090';  // Funciona con CORS desde Netlify"
)

with open('index.html', 'w') as f:
    f.write(content)

print("✅ Fixes aplicados")
