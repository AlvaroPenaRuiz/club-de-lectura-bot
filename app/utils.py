from app.db import quienes_leyeron, quienes_faltan


WHITELIST_ENABLED = True
OWNER_ID: int | None = None


def configurar_whitelist(enabled: bool, owner_id: int | None):
    global WHITELIST_ENABLED, OWNER_ID
    WHITELIST_ENABLED = enabled
    OWNER_ID = owner_id


def es_owner(user_id: int) -> bool:
    return OWNER_ID is not None and user_id == OWNER_ID


def nombre_de_usuario(user) -> str:
    nombre = " ".join(p for p in [user.first_name, user.last_name] if p).strip()
    return nombre or user.username or str(user.id)


def lista_progreso(chat_id: int) -> str:
    leidos = quienes_leyeron(chat_id)
    faltan = quienes_faltan(chat_id)
    ids_leidos = {r['user_id'] for r in leidos}
    lineas = []
    for r in leidos + faltan:
        marca = "✅" if r['user_id'] in ids_leidos else "⬜"
        lineas.append(f"{marca} {r['nombre']}")
    return "\n".join(lineas)


def parsear_capitulos(texto: str) -> list[int] | None:
    """Parsea formatos como '1-5', '1,2,3' o '1, 2, 3'. Devuelve lista ordenada o None si inválido."""
    texto = texto.strip()
    if not texto:
        return None

    # Formato rango: 1-5
    if "-" in texto and "," not in texto:
        partes = texto.split("-")
        if len(partes) != 2:
            return None
        try:
            inicio, fin = int(partes[0].strip()), int(partes[1].strip())
        except ValueError:
            return None
        if inicio < 1 or fin < inicio:
            return None
        return list(range(inicio, fin + 1))

    # Formato lista: 1,2,3 o 1, 2, 3
    try:
        capitulos = sorted(set(int(c.strip()) for c in texto.split(",")))
    except ValueError:
        return None
    if any(c < 1 for c in capitulos):
        return None
    return capitulos


def formato_capitulos(capitulos_str: str) -> str:
    """Convierte '1,2,3,4,5' almacenado en DB a texto bonito."""
    nums = [int(c) for c in capitulos_str.split(",")]
    if len(nums) == 1:
        return f"Capítulo {nums[0]}"
    return f"Capítulos {', '.join(str(n) for n in nums[:-1])} y {nums[-1]}"
