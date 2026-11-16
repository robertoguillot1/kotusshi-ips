"""
Lógica de Negocio Clínica y Reglas Normativas
Conforme a la Resolución 000115 de 2026 (Actualización Res. 2350 de 2020)
"""

from datetime import date, timedelta
from typing import Optional, Tuple

def clasificar_estado_nutricional(z_score: Optional[float]) -> str:
    """
    Clasifica el estado nutricional según el Puntaje Z (P/T):
    - Z < -3.0: Desnutrición aguda severa
    - -3.0 <= Z < -2.0: Desnutrición aguda moderada
    - -2.0 <= Z < -1.0: Riesgo de desnutrición aguda
    - -1.0 <= Z <= 1.0: Peso adecuado para la talla
    - Z > 1.0: Sobrepeso / Obesidad
    """
    if z_score is None:
        return "Sin dato antropométrico"
    if z_score < -3.0:
        return "Desnutrición aguda severa"
    elif z_score < -2.0:
        return "Desnutrición aguda moderada"
    elif z_score < -1.0:
        return "Riesgo de desnutrición aguda"
    elif z_score <= 1.0:
        return "Peso adecuado para la talla"
    else:
        return "Sobrepeso / Obesidad"

def calcular_proxima_cita(fecha_base: Optional[date], z_score: Optional[float]) -> Optional[date]:
    """
    Calcula la próxima fecha de cita clínica según el último Z-Score:
    - Z < -2.0 (DNT Severa o Moderada): 7 días
    - -2.0 <= Z < -1.0 (Riesgo de DNT): 15 días
    - Z >= -1.0 (Peso adecuado): 30 días (~1 mes)
    """
    if not fecha_base or z_score is None:
        return None
    if z_score < -2.0:
        return fecha_base + timedelta(days=7)
    elif z_score < -1.0:
        return fecha_base + timedelta(days=15)
    else:
        return fecha_base + timedelta(days=30)

def evaluar_ventana_etaria(fecha_nacimiento: date, fecha_referencia: Optional[date] = None) -> Tuple[int, bool, bool]:
    """
    Calcula edad en meses y evalúa alertas de ventana etaria:
    - Retorna: (edad_en_meses, alerta_ingreso_fuera_rango, alerta_egreso_obligatorio)
    - Alerta ingreso: edad > 59 meses al momento de referencia
    - Alerta egreso: edad >= 60 meses a la fecha actual
    """
    hoy = date.today()
    ref = fecha_referencia or hoy

    meses_ref = (ref.year - fecha_nacimiento.year) * 12 + (ref.month - fecha_nacimiento.month)
    if ref.day < fecha_nacimiento.day:
        meses_ref -= 1

    meses_actual = (hoy.year - fecha_nacimiento.year) * 12 + (hoy.month - fecha_nacimiento.month)
    if hoy.day < fecha_nacimiento.day:
        meses_actual -= 1

    ingreso_fuera_rango = meses_ref > 59
    egreso_obligatorio = meses_actual >= 60

    return max(0, meses_actual), ingreso_fuera_rango, egreso_obligatorio
