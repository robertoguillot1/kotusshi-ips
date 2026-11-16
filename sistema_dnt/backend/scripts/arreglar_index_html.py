import re

with open('sistema_dnt/frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar bloques duplicados de tab-reportes-oficiales
# Eliminar todas las secciones tab-reportes-oficiales existentes
patron_seccion = r'<!-- 7\. PESTAÑA: CENTRO OFICIAL DE REPORTES Y GENERACIÓN DE ARCHIVOS -->[\s\S]*?</section>'
bloques = re.findall(patron_seccion, content)
print(f"Bloques encontrados: {len(bloques)}")

if len(bloques) > 0:
    # Quitar todos
    content_limpio = re.sub(patron_seccion, '', content)
    # Ahora insertar exactamente UN bloque antes de </main>
    bloque_unico = bloques[0]
    
    # Asegurarnos de que quede justo antes de </main>
    if '</main>' in content_limpio:
        partes = content_limpio.split('</main>')
        nuevo_content = partes[0] + bloque_unico + '\n\n  </main>' + partes[1]
        with open('sistema_dnt/frontend/index.html', 'w', encoding='utf-8') as f:
            f.write(nuevo_content)
        print("index.html reparado con exito con 1 solo bloque antes de </main>.")
    else:
        print("No se encontro </main>.")
else:
    print("No se encontraron bloques de tab-reportes-oficiales.")
