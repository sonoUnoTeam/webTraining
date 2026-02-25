#!/usr/bin/env python
"""
Script para compilar archivos .po a .mo usando polib
"""
import polib
from pathlib import Path

# Directorio base 
BASE_DIR = Path(__file__).resolve().parent.parent

# Buscar todos los archivos .po
locale_dir = BASE_DIR / 'locale'

po_files = list(locale_dir.glob('**/LC_MESSAGES/*.po'))

print(f"Encontrados {len(po_files)} archivos .po para compilar\n")

success_count = 0
error_count = 0

for po_file in po_files:
    mo_file = po_file.with_suffix('.mo')
    print(f"Compilando: {po_file.relative_to(BASE_DIR)}")
    print(f"  → {mo_file.relative_to(BASE_DIR)}")
    
    try:
        # Cargar el archivo .po
        po = polib.pofile(str(po_file))
        
        # Guardar como .mo
        po.save_as_mofile(str(mo_file))
        
        print(f"  ✓ Compilado exitosamente ({len(po)} entradas)\n")
        success_count += 1
        
    except Exception as e:
        print(f"  ✗ Error: {e}\n")
        error_count += 1

print("="*60)
print(f"Proceso completado:")
print(f"  ✓ Éxitos: {success_count}")
print(f"  ✗ Errores: {error_count}")
print("="*60)
