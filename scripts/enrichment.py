"""Public-safe UmClique enrichment: error groups, channel metadata, and origin labels.

Never serialize contact names, phone numbers, recipient samples, raw_examples,
message content or full delivery logs to the public GitHub Pages JSON.
"""
import re

MAX_TEXT = 260
# Error diagnostics suggestions only. A message that *looks* permanent is never
# automatically marked safe for re-sending without checking the official error.
PERMANENT = {"131026", "131009", "100"}
TEMPORARY = {"130429", "131048", "131000", "131031", "131056", "2"}
BLOCKED = {"131049", "131026", "131031"}


def clean_text(value, max_length=MAX_TEXT):
    if value is None:
        return ""
    # Mask sensitive substrings and remove embedded markup/control characters.
    value = str(value)
    value = re.sub(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)", "[dado omitido]", value)
    value = re.sub(r"[\x00-\x1f\x7f<>]", " ", value)
    return re.sub(r"\s+", " ", value).strip()[:max_length]


def category(code, title):
    lower = (code + " " + title).casefold()
    if code == "131049" or "engajamento" in lower:
        return "Política/engajamento", "Revisão manual", "Não reenviar automaticamente"
    if code == "131026" or "inválid" in lower or "inexistente" in lower:
        return "Número/destinatário", "Verificar destinatário", "Confirmar dados e consentimento"
    if "autentica" in lower or "token" in lower or "conex" in lower or code == "131031":
        return "Autenticação/conexão", "Investigar integração", "Verificar canal e credenciais"
    if "fila" in lower or "queue" in lower:
        return "Fila de processamento", "Revisão manual", "Investigar fila antes de nova tentativa"
    if "limite" in lower or "throttle" in lower or code in {"130429", "131048", "131056"}:
        return "Limite/ritmo", "Potencialmente temporário", "Aguardar janela e revisar limites"
    if code in TEMPORARY or "temporár" in lower:
        return "Falha temporária", "Potencialmente temporário", "Validar antes de tentar novamente"
    if code in PERMANENT:
        return "Falha persistente", "Verificar destinatário", "Não reenviar sem corrigir a causa"
    if "bloque" in lower:
        return "Bloqueio", "Revisão manual", "Não reenviar automaticamente"
    return "Outros/não classificados", "Revisão manual", "Consultar documentação oficial"


def sanitize_errors(payload):
    """Only aggregate groups. An empty payload is not proof of zero errors."""
    if not isinstance(payload, dict) or not isinstance(payload.get("groups"), list):
        return None
    result = []
    for group in payload["groups"][:200]:
        if not isinstance(group, dict):
            continue
        try:
            count = int(group.get("count", 0))
        except (TypeError, ValueError):
            continue
        if count < 0:
            continue
        code = clean_text(group.get("code") or group.get("key") or "Sem código", 50)
        title = clean_text(group.get("title") or "Erro não identificado")
        kind, recover, next_action = category(code, title)
        result.append({
            "code": code,
            "title": title,
            "description": clean_text(group.get("description")),
            "action": clean_text(group.get("action")),
            "count": count,
            "type": kind,
            "recoverability": recover,
            "suggestion": next_action,
            "explained": group.get("explained") if isinstance(group.get("explained"), bool) else None,
        })
    summary = payload.get("summary") or {}
    def n(value):
        try:
            return max(0, int(value)) if value is not None else None
        except (ValueError, TypeError):
            return None
    return {
        "groups": result,
        "summary": {
            "failedTotal": n(summary.get("failed_total")),
            "unexplained": n(summary.get("unexplained_count")),
            "scannedRows": n(summary.get("scanned_rows")),
            "truncated": bool(summary.get("truncated", False)),
            "throttleCount": n(summary.get("throttle_count")),
            "protectionPause": bool(summary.get("protection_pause", False))
        }
    }


def sanitize_channel(channel):
    if not isinstance(channel, dict) or not channel.get("id"):
        return None
    return {
        "id": str(channel["id"])[:100],
        "name": clean_text(channel.get("name") or "Canal não identificado", 70),
        "provider": clean_text(channel.get("provider"), 24),
        "status": clean_text(channel.get("status"), 30) or None,
        # Does not expose phone_number_id or direct phone number publicly.
    }


def sanitize_channel_list(payload, allowed_ids):
    if not isinstance(payload, dict):
        return []
    allowed = set(str(i) for i in allowed_ids)
    return [x for x in (sanitize_channel(c) for c in payload.get("channels", []))
            if x and x["id"] in allowed]


def safe_origin(value):
    allowed = {"PDF Instagram", "Reativação da base", "Lista Prioritária",
               "Orgânico", "Mídia paga", "Outras campanhas"}
    return value if value in allowed else None


def assign_origins(records, campaign_origins):
    """Campaign-level attribution; does not invent/overwrite original contact source."""
    for record in records:
        origin = safe_origin(campaign_origins.get(record.get("campaignId") or record.get("id")))
        if origin:
            record["campaignOrigin"] = origin
        elif not record.get("campaignOrigin"):
            record["campaignOrigin"] = None
    return records
