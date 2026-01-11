# =============================================================================
# TO_EXTRACTOR v7.0 - ROUTER SUPERVISIONE
# =============================================================================
# Endpoint API per gestione supervisione espositori, listino e criteri ML
# v6.1: Aggiunto workflow ritorno a ordine
# v7.0: Aggiunto supporto supervisione listino
# =============================================================================

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database_pg import (
    get_db,
    get_supervisione_pending,
    get_supervisione_listino_pending,
    get_all_supervisioni_pending,
    get_supervisione_by_testata,
    get_supervisione_listino_by_testata,
    count_supervisioni_pending,
    count_supervisioni_espositore_pending,
    count_supervisioni_listino_pending,
    get_criterio_by_pattern,
    get_criterio_listino_by_pattern,
    get_criteri_ordinari,
    get_criteri_listino_ordinari,
    get_criteri_stats,
)
from ..services.supervisione import (
    approva_supervisione,
    rifiuta_supervisione,
    modifica_supervisione,
    get_supervisioni_per_ordine,
    get_storico_criteri_applicati,
)
from ..services.ordini import (
    get_stato_righe_ordine,
)


router = APIRouter(prefix="/supervisione", tags=["Supervisione"])


# =============================================================================
# MODELLI PYDANTIC
# =============================================================================

class DecisioneBase(BaseModel):
    """Base per decisioni supervisione."""
    operatore: str
    note: Optional[str] = None


class DecisioneApprova(DecisioneBase):
    """Richiesta approvazione."""
    pass


class DecisioneRifiuta(DecisioneBase):
    """Richiesta rifiuto (note obbligatorie)."""
    note: str  # Override per renderlo obbligatorio


class DecisioneModifica(DecisioneBase):
    """Richiesta modifica manuale."""
    modifiche: dict


class CorrezioneListinoRequest(BaseModel):
    """Richiesta correzione prezzi listino."""
    operatore: str
    prezzo_netto: Optional[float] = None
    prezzo_pubblico: Optional[float] = None
    sconto_1: Optional[float] = None
    sconto_2: Optional[float] = None
    sconto_3: Optional[float] = None
    sconto_4: Optional[float] = None
    aliquota_iva: Optional[float] = None
    applica_a_listino: bool = False  # Se True, aggiunge anche al listino vendor
    note: Optional[str] = None


class ArchiviazioneListinoRequest(BaseModel):
    """Richiesta archiviazione riga listino."""
    operatore: str
    motivo: str  # Motivo archiviazione obbligatorio
    note: Optional[str] = None


class SupervisioneResponse(BaseModel):
    """Risposta singola supervisione."""
    id_supervisione: int
    id_testata: int
    codice_anomalia: str
    codice_espositore: Optional[str]
    descrizione_espositore: Optional[str]
    pezzi_attesi: int
    pezzi_trovati: int
    valore_calcolato: float
    pattern_signature: Optional[str]
    stato: str
    operatore: Optional[str]
    timestamp_creazione: str
    timestamp_decisione: Optional[str]
    note: Optional[str]
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT SUPERVISIONI PENDING
# =============================================================================

@router.get("/pending", summary="Lista supervisioni in attesa")
async def get_pending(tipo: Optional[str] = Query(None, description="Tipo: 'espositore', 'listino', 'lookup' o None per tutti")):
    """
    Ritorna lista di tutte le supervisioni in attesa di revisione.

    Include informazioni su ordine, pattern, e conteggio approvazioni pattern.
    Supporta anomalie espositore, listino e lookup (v8.0).

    Parametri:
    - tipo: filtra per tipo (espositore/listino/lookup) o ritorna tutti se None
    """
    from ..database_pg import get_supervisione_lookup_pending

    if tipo == 'espositore':
        supervisioni = get_supervisione_pending()
        return {
            "count": len(supervisioni),
            "tipo": "espositore",
            "supervisioni": supervisioni
        }
    elif tipo == 'listino':
        supervisioni = get_supervisione_listino_pending()
        return {
            "count": len(supervisioni),
            "tipo": "listino",
            "supervisioni": supervisioni
        }
    elif tipo == 'lookup':
        supervisioni = get_supervisione_lookup_pending()
        return {
            "count": len(supervisioni),
            "tipo": "lookup",
            "supervisioni": supervisioni
        }
    else:
        # Ritorna tutti i tipi
        esp_supervisioni = get_supervisione_pending()
        listino_supervisioni = get_supervisione_listino_pending()
        lookup_supervisioni = get_supervisione_lookup_pending()

        # Aggiungi tipo per identificazione frontend
        for s in esp_supervisioni:
            s['tipo_supervisione'] = 'espositore'
        for s in listino_supervisioni:
            s['tipo_supervisione'] = 'listino'
        for s in lookup_supervisioni:
            s['tipo_supervisione'] = 'lookup'

        all_supervisioni = esp_supervisioni + listino_supervisioni + lookup_supervisioni

        return {
            "count": len(all_supervisioni),
            "count_espositore": len(esp_supervisioni),
            "count_listino": len(listino_supervisioni),
            "count_lookup": len(lookup_supervisioni),
            "supervisioni": all_supervisioni
        }


@router.get("/pending/count", summary="Conteggio supervisioni pending")
async def get_pending_count():
    """Ritorna conteggio delle supervisioni pending per tipo."""
    from ..database_pg import count_supervisioni_lookup_pending

    return {
        "count": count_supervisioni_pending(),
        "count_espositore": count_supervisioni_espositore_pending(),
        "count_listino": count_supervisioni_listino_pending(),
        "count_lookup": count_supervisioni_lookup_pending(),  # v8.0
    }


# =============================================================================
# ENDPOINT DETTAGLIO SUPERVISIONE
# =============================================================================

@router.get("/{id_supervisione}", summary="Dettaglio supervisione")
async def get_supervisione(id_supervisione: int):
    """
    Ritorna dettagli completi di una supervisione.
    
    Include:
    - Dati anomalia
    - Stato attuale
    - Informazioni pattern ML
    - Storico decisioni
    """
    db = get_db()
    
    row = db.execute("""
        SELECT se.*, coe.count_approvazioni, coe.is_ordinario, coe.pattern_descrizione
        FROM SUPERVISIONE_ESPOSITORE se
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return dict(row)


@router.get("/ordine/{id_testata}", summary="Supervisioni per ordine")
async def get_supervisioni_ordine(id_testata: int):
    """Ritorna tutte le supervisioni per un ordine specifico."""
    supervisioni = get_supervisioni_per_ordine(id_testata)
    return {
        "id_testata": id_testata,
        "count": len(supervisioni),
        "supervisioni": supervisioni
    }


# =============================================================================
# ENDPOINT DECISIONI
# =============================================================================

@router.post("/{id_supervisione}/approva", summary="Approva supervisione")
async def approva(id_supervisione: int, decisione: DecisioneApprova):
    """
    Approva una supervisione.
    
    Effetti:
    - Stato → APPROVED
    - Incrementa contatore pattern
    - Se pattern raggiunge soglia (5), diventa ordinario
    - Sblocca ordine se era l'ultima pending
    """
    success = approva_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "APPROVED",
        "operatore": decisione.operatore
    }


@router.post("/{id_supervisione}/rifiuta", summary="Rifiuta supervisione")
async def rifiuta(id_supervisione: int, decisione: DecisioneRifiuta):
    """
    Rifiuta una supervisione.
    
    Effetti:
    - Stato → REJECTED
    - Reset contatore pattern a 0
    - Ordine rimane bloccato (richiede intervento manuale)
    """
    success = rifiuta_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "REJECTED",
        "operatore": decisione.operatore
    }


@router.post("/{id_supervisione}/modifica", summary="Modifica manuale")
async def modifica(id_supervisione: int, decisione: DecisioneModifica):
    """
    Applica modifiche manuali a un ordine in supervisione.
    
    Effetti:
    - Stato → MODIFIED
    - Salva modifiche in JSON
    - NON incrementa pattern (caso speciale)
    - Sblocca ordine
    """
    success = modifica_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.modifiche,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "MODIFIED",
        "operatore": decisione.operatore
    }


# =============================================================================
# v6.1: ENDPOINT WORKFLOW RITORNO A ORDINE
# =============================================================================

@router.post("/{id_supervisione}/completa-e-torna", summary="Approva e torna a ordine")
async def approva_e_torna(id_supervisione: int, decisione: DecisioneApprova):
    """
    Approva supervisione e aggiorna stato riga a SUPERVISIONATO.
    
    Usato dal workflow Ordine → Supervisione → Ordine.
    """
    db = get_db()
    
    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    # Approva supervisione
    success = approva_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Errore approvazione")
    
    # Aggiorna stato riga a SUPERVISIONATO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'SUPERVISIONATO',
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || %s
        WHERE id_supervisione = %s
    """, (f"[{decisione.operatore}] Approvato", id_supervisione))
    db.commit()
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "azione": "APPROVED",
        "riga_stato": "SUPERVISIONATO",
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


@router.post("/{id_supervisione}/modifica-e-torna", summary="Modifica e torna a ordine")
async def modifica_e_torna(id_supervisione: int, decisione: DecisioneModifica):
    """
    Applica modifiche riga e torna a ordine.
    """
    db = get_db()
    
    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    # Applica modifica
    success = modifica_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.modifiche,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Errore modifica")
    
    # Aggiorna stato riga a SUPERVISIONATO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'SUPERVISIONATO',
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || %s
        WHERE id_supervisione = %s
    """, (f"[{decisione.operatore}] Modificato", id_supervisione))
    db.commit()
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "azione": "MODIFIED",
        "campi_modificati": list(decisione.modifiche.keys()),
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


@router.post("/{id_supervisione}/lascia-sospeso", summary="Lascia sospeso e torna")
async def lascia_sospeso(id_supervisione: int, operatore: str = Query(...)):
    """
    Torna a ordine senza decisione (riga rimane IN_SUPERVISIONE).
    """
    db = get_db()
    
    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "stato": "PENDING",
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


# =============================================================================
# ENDPOINT CRITERI ML
# =============================================================================

@router.get("/criteri/ordinari", summary="Lista criteri ordinari")
async def get_criteri():
    """
    Ritorna tutti i pattern promossi a criteri ordinari.

    Un pattern diventa ordinario dopo 5 approvazioni consecutive.
    I criteri ordinari vengono applicati automaticamente senza supervisione.
    """
    criteri = get_criteri_ordinari()
    return {
        "count": len(criteri),
        "criteri": criteri
    }


@router.get("/criteri/tutti", summary="Lista tutti i pattern ML")
async def get_tutti_criteri():
    """
    Ritorna TUTTI i pattern ML (ordinari + in apprendimento).

    Include pattern espositore e listino, con indicazione dello stato:
    - is_ordinario: true = automatico, false = in apprendimento
    - count_approvazioni: numero approvazioni attuali
    """
    db = get_db()

    # Pattern espositore
    criteri_esp = db.execute("""
        SELECT
            pattern_signature,
            pattern_descrizione,
            codice_espositore,
            fascia_scostamento,
            count_approvazioni,
            is_ordinario,
            data_promozione,
            'espositore' AS tipo
        FROM criteri_ordinari_espositore
        ORDER BY count_approvazioni DESC, data_promozione DESC NULLS LAST
    """).fetchall()

    # Pattern listino
    criteri_lst = db.execute("""
        SELECT
            pattern_signature,
            pattern_descrizione,
            codice_aic,
            vendor,
            count_approvazioni,
            is_ordinario,
            data_promozione,
            'listino' AS tipo
        FROM criteri_ordinari_listino
        ORDER BY count_approvazioni DESC, data_promozione DESC NULLS LAST
    """).fetchall()

    all_criteri = [dict(c) for c in criteri_esp] + [dict(c) for c in criteri_lst]

    # Ordina per count_approvazioni decrescente
    all_criteri.sort(key=lambda x: (x.get('count_approvazioni', 0), str(x.get('data_promozione') or '')), reverse=True)

    return {
        "count": len(all_criteri),
        "count_ordinari": sum(1 for c in all_criteri if c.get('is_ordinario')),
        "count_in_apprendimento": sum(1 for c in all_criteri if not c.get('is_ordinario') and c.get('count_approvazioni', 0) > 0),
        "criteri": all_criteri
    }


@router.get("/criteri/stats", summary="Statistiche criteri ML")
async def get_stats_criteri():
    """
    Ritorna statistiche sul sistema di apprendimento.
    
    Include:
    - Totale pattern
    - Pattern ordinari (applicati automaticamente)
    - Pattern in apprendimento (count > 0 ma < 5)
    - Applicazioni automatiche oggi
    """
    return get_criteri_stats()


@router.get("/criteri/{pattern_signature}", summary="Dettaglio pattern")
async def get_pattern(pattern_signature: str):
    """Ritorna dettagli di un pattern specifico."""
    criterio = get_criterio_by_pattern(pattern_signature)
    
    if not criterio:
        raise HTTPException(status_code=404, detail="Pattern non trovato")
    
    return criterio


@router.post("/criteri/{pattern_signature}/reset", summary="Reset pattern")
async def reset_pattern(pattern_signature: str, operatore: str = Query(...)):
    """
    Resetta contatore approvazioni di un pattern.

    Utile se un pattern ordinario inizia a generare falsi positivi.
    """
    from ..services.supervisione import registra_rifiuto_pattern

    registra_rifiuto_pattern(pattern_signature)

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "RESET",
        "operatore": operatore
    }


@router.post("/criteri/{pattern_signature}/promuovi", summary="Forza promozione pattern")
async def promuovi_pattern(pattern_signature: str, operatore: str = Query(...)):
    """
    Forza promozione di un pattern a "ordinario" (automatico).

    Permette di rendere automatico un pattern anche prima delle 5 approvazioni standard.
    """
    db = get_db()

    # Verifica che il pattern esista
    criterio_esp = db.execute(
        "SELECT pattern_signature, count_approvazioni FROM criteri_ordinari_espositore WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()

    criterio_lst = db.execute(
        "SELECT pattern_signature, count_approvazioni FROM criteri_ordinari_listino WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()

    if not criterio_esp and not criterio_lst:
        raise HTTPException(status_code=404, detail="Pattern non trovato")

    # Forza promozione settando count_approvazioni = 5 e is_ordinario = true
    if criterio_esp:
        db.execute("""
            UPDATE criteri_ordinari_espositore
            SET count_approvazioni = 5, is_ordinario = true,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_signature,))
        tipo = "espositore"
    else:
        db.execute("""
            UPDATE criteri_ordinari_listino
            SET count_approvazioni = 5, is_ordinario = true,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_signature,))
        tipo = "listino"

    db.commit()

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "tipo": tipo,
        "azione": "PROMOZIONE_FORZATA",
        "operatore": operatore
    }


# =============================================================================
# ENDPOINT STORICO
# =============================================================================

@router.get("/storico/applicazioni", summary="Storico applicazioni criteri")
async def get_storico(limit: int = Query(50, ge=1, le=200)):
    """
    Ritorna storico delle applicazioni criteri (automatiche e manuali).

    Utile per audit trail e debug.
    """
    storico = get_storico_criteri_applicati(limit)
    return {
        "count": len(storico),
        "applicazioni": storico
    }


# =============================================================================
# v6.2: ENDPOINT ML PATTERN MATCHING
# =============================================================================

class RisoluzioneConflittoRequest(BaseModel):
    """Richiesta risoluzione conflitto ML."""
    operatore: str
    scelta: str  # 'PATTERN', 'ESTRAZIONE', 'MANUALE'
    modifiche_manuali: Optional[dict] = None
    note: Optional[str] = None


@router.get("/{id_supervisione}/confronto-ml", summary="Confronto ML per supervisione")
async def get_confronto_ml(id_supervisione: int):
    """
    v6.2: Ritorna confronto tra child estratti e pattern ML.

    Usato per visualizzare le differenze quando si verifica
    un conflitto ESP-A06 (similarity < 50%).

    Returns:
        - child_estratti: Lista child estratti dal PDF
        - child_pattern: Lista child dal pattern appreso
        - similarity_score: Score di similarita (0-100)
        - similarity_details: Dettagli calcolo (jaccard, lcs, qty, count)
        - decision: Decisione suggerita ML
    """
    import json
    from ..services.ml_pattern_matching import (
        calcola_similarity_sequenze,
        determina_decisione_ml,
        cerca_pattern_per_espositore,
    )

    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT se.*, coe.child_sequence_json, coe.descrizione_normalizzata
        FROM supervisione_espositore se
        LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    sup = dict(sup)

    # Recupera child estratti dall'ordine
    parent = db.execute("""
        SELECT id_dettaglio, descrizione
        FROM ordini_dettaglio
        WHERE id_testata = %s
          AND codice_originale = %s
          AND is_espositore = TRUE
        LIMIT 1
    """, (sup['id_testata'], sup['codice_espositore'])).fetchone()

    child_estratti = []
    if parent:
        parent = dict(parent)
        children = db.execute("""
            SELECT codice_aic, codice_originale, descrizione, q_venduta AS quantita
            FROM ordini_dettaglio
            WHERE id_testata = %s
              AND id_parent_espositore = %s
              AND is_child = TRUE
            ORDER BY n_riga
        """, (sup['id_testata'], parent['id_dettaglio'])).fetchall()

        child_estratti = [
            {
                'aic': r['codice_aic'],
                'codice': r['codice_originale'],
                'descrizione': r['descrizione'],
                'quantita': r['quantita']
            }
            for r in children
        ]

    # Recupera child pattern
    child_pattern = []
    if sup.get('child_sequence_json'):
        child_pattern = json.loads(sup['child_sequence_json'])

    # Calcola similarity
    similarity_score, similarity_details = calcola_similarity_sequenze(
        child_estratti, child_pattern
    )

    # Determina decisione
    ml_decision = determina_decisione_ml(similarity_score)

    return {
        "id_supervisione": id_supervisione,
        "child_estratti": child_estratti,
        "child_pattern": child_pattern,
        "similarity_score": similarity_score,
        "similarity_details": similarity_details,
        "ml_decision": {
            "decision": ml_decision.decision,
            "reason": ml_decision.reason,
        },
        "pattern_signature": sup.get('pattern_signature'),
        "descrizione_pattern": sup.get('descrizione_normalizzata'),
    }


@router.post("/{id_supervisione}/risolvi-conflitto", summary="Risolvi conflitto ML")
async def risolvi_conflitto_ml(id_supervisione: int, req: RisoluzioneConflittoRequest):
    """
    v6.2: Risolve conflitto ML tra pattern e estrazione.

    L'operatore puo' scegliere:
    - PATTERN: Usa i child dal pattern appreso (corregge errore estrazione)
    - ESTRAZIONE: Usa i child estratti (pattern non valido per questo caso)
    - MANUALE: Specifica manualmente i child corretti

    La scelta aggiorna anche il pattern ML:
    - PATTERN: Incrementa confidence del pattern
    - ESTRAZIONE: Decrementa confidence o invalida pattern
    - MANUALE: Crea nuovo pattern con i dati corretti
    """
    import json
    from ..services.ml_pattern_matching import (
        aggiorna_esito_ml,
        aggiorna_statistiche_pattern,
    )

    db = get_db()

    # Recupera supervisione e log ML
    sup = db.execute("""
        SELECT se.*, lm.id_log
        FROM supervisione_espositore se
        LEFT JOIN log_ml_decisions lm ON lm.id_testata = se.id_testata
            AND lm.pattern_signature = se.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    sup = dict(sup)

    if req.scelta == 'PATTERN':
        # Usa pattern: l'estrazione era errata
        # Approva supervisione con nota
        approva_supervisione(
            id_supervisione,
            req.operatore,
            note=f"Conflitto ML risolto: usato PATTERN. {req.note or ''}"
        )

        # Aggiorna statistiche pattern (successo)
        if sup.get('pattern_signature'):
            aggiorna_statistiche_pattern(sup['pattern_signature'], successo=True)

        # Aggiorna esito ML log
        if sup.get('id_log'):
            aggiorna_esito_ml(sup['id_log'], 'CORRECT', req.operatore)

        return {
            "success": True,
            "id_supervisione": id_supervisione,
            "scelta": "PATTERN",
            "azione": "Supervisione approvata, pattern confermato",
        }

    elif req.scelta == 'ESTRAZIONE':
        # Usa estrazione: il pattern non e' valido per questo caso
        # Approva supervisione ma non incrementa pattern
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s
        """, (req.operatore, f"Conflitto ML risolto: usata ESTRAZIONE. {req.note or ''}", id_supervisione))

        # Aggiorna statistiche pattern (fallimento)
        if sup.get('pattern_signature'):
            aggiorna_statistiche_pattern(sup['pattern_signature'], successo=False)

        # Aggiorna esito ML log
        if sup.get('id_log'):
            aggiorna_esito_ml(sup['id_log'], 'INCORRECT', req.operatore)

        db.commit()

        return {
            "success": True,
            "id_supervisione": id_supervisione,
            "scelta": "ESTRAZIONE",
            "azione": "Supervisione approvata, estrazione mantenuta",
        }

    elif req.scelta == 'MANUALE':
        # Modifica manuale: richiede modifiche_manuali
        if not req.modifiche_manuali:
            raise HTTPException(
                status_code=400,
                detail="Per scelta MANUALE, specificare modifiche_manuali"
            )

        modifica_supervisione(
            id_supervisione,
            req.operatore,
            req.modifiche_manuali,
            note=f"Conflitto ML risolto: modifica MANUALE. {req.note or ''}"
        )

        # Aggiorna esito ML log
        if sup.get('id_log'):
            aggiorna_esito_ml(sup['id_log'], 'MODIFIED', req.operatore)

        return {
            "success": True,
            "id_supervisione": id_supervisione,
            "scelta": "MANUALE",
            "azione": "Supervisione modificata manualmente",
            "modifiche": list(req.modifiche_manuali.keys()),
        }

    else:
        raise HTTPException(
            status_code=400,
            detail="Scelta non valida. Usare: PATTERN, ESTRAZIONE, MANUALE"
        )


@router.get("/ml/stats", summary="Statistiche sistema ML")
async def get_ml_stats():
    """
    v6.2: Ritorna statistiche complete del sistema ML.

    Include:
    - Pattern totali, ordinari, con sequenza child
    - Decisioni ML ultimi 30 giorni (per tipo)
    - Accuracy (decisioni con esito verificato)
    """
    from ..services.ml_pattern_matching import get_statistiche_ml

    return get_statistiche_ml()


@router.get("/ml/log", summary="Log decisioni ML")
async def get_ml_log(
    limit: int = Query(50, ge=1, le=200),
    decision: Optional[str] = Query(None, description="Filtra per decisione: APPLY_ML, APPLY_WARNING, SEND_SUPERVISION")
):
    """
    v6.2: Ritorna log delle decisioni ML.

    Utile per audit e analisi del comportamento del sistema.
    """
    db = get_db()

    query = """
        SELECT lm.*, ot.numero_ordine_vendor AS numero_ordine
        FROM log_ml_decisions lm
        LEFT JOIN ordini_testata ot ON lm.id_testata = ot.id_testata
    """

    params = []
    if decision:
        query += " WHERE lm.decision = %s"
        params.append(decision)

    query += " ORDER BY lm.timestamp DESC LIMIT %s"
    params.append(limit)

    rows = db.execute(query, tuple(params)).fetchall()

    return {
        "count": len(rows),
        "log": [dict(r) for r in rows]
    }


@router.post("/ml/processa-retroattive", summary="Processa anomalie risolte retroattivamente")
async def processa_retroattive():
    """
    v6.2: Processa retroattivamente le anomalie ESPOSITORE già risolte.

    Crea pattern ML dalle anomalie storiche risolte prima dell'implementazione
    del sistema ML. Da eseguire una tantum dopo la migrazione.

    Returns:
        Statistiche del processamento
    """
    from ..services.ml_pattern_matching import processa_anomalie_risolte_retroattive

    stats = processa_anomalie_risolte_retroattive()

    return {
        "success": True,
        "message": f"Processate {stats['processate']} anomalie retroattive",
        "stats": stats
    }


# =============================================================================
# v7.0: ENDPOINT SUPERVISIONE LISTINO
# =============================================================================

@router.get("/listino/{id_supervisione}", summary="Dettaglio supervisione listino")
async def get_supervisione_listino_detail(id_supervisione: int):
    """
    Ritorna dettagli completi di una supervisione listino.

    Include:
    - Dati anomalia (AIC, descrizione, vendor)
    - Dati riga ordine corrente
    - Pattern esistenti per lo stesso AIC
    - Suggerimenti prezzo da altre fonti
    """
    db = get_db()

    # Recupera supervisione con dati ordine
    row = db.execute("""
        SELECT sl.*,
               od.descrizione AS descrizione_riga,
               od.q_venduta, od.prezzo_netto AS prezzo_netto_attuale,
               od.prezzo_pubblico AS prezzo_pubblico_attuale,
               od.sconto_1 AS sconto_1_attuale, od.sconto_2 AS sconto_2_attuale,
               od.sconto_3 AS sconto_3_attuale, od.sconto_4 AS sconto_4_attuale,
               od.aliquota_iva AS aliquota_iva_attuale,
               ot.numero_ordine_vendor, ot.ragione_sociale_1,
               col.count_approvazioni AS pattern_count,
               col.is_ordinario AS pattern_ordinario,
               col.prezzo_netto_pattern, col.sconto_1_pattern, col.sconto_2_pattern
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        LEFT JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
        LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
        WHERE sl.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Supervisione listino non trovata")

    result = dict(row)

    # Cerca prezzi in altri listini o ordini precedenti
    if result.get('codice_aic'):
        # Cerca nel listino vendor
        listino_row = db.execute("""
            SELECT prezzo_netto, prezzo_pubblico, sconto_1, sconto_2, aliquota_iva
            FROM listini_vendor
            WHERE codice_aic = %s AND attivo = TRUE
            LIMIT 1
        """, (result['codice_aic'],)).fetchone()

        if listino_row:
            result['suggerimento_listino'] = dict(listino_row)

        # Cerca in ordini precedenti con stesso AIC e prezzi compilati
        ordini_prec = db.execute("""
            SELECT prezzo_netto, prezzo_pubblico, sconto_1, sconto_2, aliquota_iva,
                   COUNT(*) as occorrenze
            FROM ordini_dettaglio
            WHERE codice_aic = %s AND prezzo_netto > 0
            GROUP BY prezzo_netto, prezzo_pubblico, sconto_1, sconto_2, aliquota_iva
            ORDER BY occorrenze DESC
            LIMIT 3
        """, (result['codice_aic'],)).fetchall()

        if ordini_prec:
            result['suggerimenti_storici'] = [dict(r) for r in ordini_prec]

    return result


@router.post("/listino/{id_supervisione}/correggi", summary="Correggi prezzi listino")
async def correggi_listino(id_supervisione: int, req: CorrezioneListinoRequest):
    """
    v7.0: Corregge i prezzi di una riga con anomalia listino.

    Effetti:
    - Aggiorna prezzi/sconti nella riga ordine
    - Marca supervisione come CORRETTA
    - Se applica_a_listino=True, aggiunge AIC al listino vendor
    - Incrementa pattern per apprendimento automatico
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT sl.*, od.id_dettaglio, od.codice_aic
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        WHERE sl.id_supervisione = %s AND sl.stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o già processata")

    sup = dict(sup)

    # Costruisci aggiornamenti per la riga
    updates = []
    params = []

    if req.prezzo_netto is not None:
        updates.append("prezzo_netto = %s")
        params.append(req.prezzo_netto)
    if req.prezzo_pubblico is not None:
        updates.append("prezzo_pubblico = %s")
        params.append(req.prezzo_pubblico)
    if req.sconto_1 is not None:
        updates.append("sconto_1 = %s")
        params.append(req.sconto_1)
    if req.sconto_2 is not None:
        updates.append("sconto_2 = %s")
        params.append(req.sconto_2)
    if req.sconto_3 is not None:
        updates.append("sconto_3 = %s")
        params.append(req.sconto_3)
    if req.sconto_4 is not None:
        updates.append("sconto_4 = %s")
        params.append(req.sconto_4)
    if req.aliquota_iva is not None:
        updates.append("aliquota_iva = %s")
        params.append(req.aliquota_iva)

    # Marca come modificato manualmente
    updates.append("modificato_manualmente = TRUE")
    updates.append("confermato_da = %s")
    params.append(req.operatore)
    updates.append("data_conferma = CURRENT_TIMESTAMP")

    if updates and sup.get('id_dettaglio'):
        params.append(sup['id_dettaglio'])
        db.execute(f"""
            UPDATE ordini_dettaglio
            SET {', '.join(updates)}
            WHERE id_dettaglio = %s
        """, tuple(params))

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_listino
        SET stato = 'CORRETTA',
            azione = 'CORREGGI',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s,
            prezzo_proposto = %s,
            sconto_1_proposto = %s,
            sconto_2_proposto = %s
        WHERE id_supervisione = %s
    """, (req.operatore, req.note, req.prezzo_netto, req.sconto_1, req.sconto_2, id_supervisione))

    # Se richiesto, aggiungi al listino vendor
    if req.applica_a_listino and sup.get('codice_aic') and sup.get('vendor'):
        db.execute("""
            INSERT INTO listini_vendor (vendor, codice_aic, descrizione, prezzo_netto,
                                        prezzo_pubblico, sconto_1, sconto_2, aliquota_iva, fonte_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'CORREZIONE_MANUALE')
            ON CONFLICT (vendor, codice_aic) DO UPDATE SET
                prezzo_netto = EXCLUDED.prezzo_netto,
                prezzo_pubblico = EXCLUDED.prezzo_pubblico,
                sconto_1 = EXCLUDED.sconto_1,
                sconto_2 = EXCLUDED.sconto_2,
                aliquota_iva = EXCLUDED.aliquota_iva,
                data_import = CURRENT_TIMESTAMP
        """, (sup['vendor'], sup['codice_aic'], sup.get('descrizione_prodotto', ''),
              req.prezzo_netto, req.prezzo_pubblico, req.sconto_1, req.sconto_2, req.aliquota_iva))

    # Aggiorna/crea pattern per apprendimento
    pattern_sig = f"LST_{sup.get('vendor', '')}_{sup.get('codice_aic', '')}"
    db.execute("""
        INSERT INTO criteri_ordinari_listino
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia, codice_aic,
             count_approvazioni, prezzo_netto_pattern, sconto_1_pattern, sconto_2_pattern,
             prezzo_pubblico_pattern, aliquota_iva_pattern, azione_pattern)
        VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, 'CORREGGI')
        ON CONFLICT (pattern_signature) DO UPDATE SET
            count_approvazioni = criteri_ordinari_listino.count_approvazioni + 1,
            prezzo_netto_pattern = EXCLUDED.prezzo_netto_pattern,
            sconto_1_pattern = EXCLUDED.sconto_1_pattern,
            sconto_2_pattern = EXCLUDED.sconto_2_pattern,
            is_ordinario = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN TRUE ELSE FALSE END,
            data_promozione = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN CURRENT_TIMESTAMP ELSE NULL END
    """, (pattern_sig, f"AIC {sup.get('codice_aic')} - {sup.get('descrizione_prodotto', '')}",
          sup.get('vendor', ''), sup.get('codice_anomalia', ''), sup.get('codice_aic', ''),
          req.prezzo_netto, req.sconto_1, req.sconto_2, req.prezzo_pubblico, req.aliquota_iva))

    # Risolvi anomalia
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s
        WHERE id_anomalia = %s
    """, (f"Correzione manuale da {req.operatore}", sup.get('id_anomalia')))

    db.commit()

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "CORRETTA",
        "operatore": req.operatore,
        "aggiunto_a_listino": req.applica_a_listino,
        "pattern_signature": pattern_sig
    }


@router.post("/listino/{id_supervisione}/archivia", summary="Archivia riga listino")
async def archivia_listino(id_supervisione: int, req: ArchiviazioneListinoRequest):
    """
    v7.0: Archivia una riga con anomalia listino (esclude da export).

    Usare quando la riga non deve essere inclusa nel tracciato finale
    (es: prodotto non gestito, errore estrazione, etc.)

    Effetti:
    - Marca riga come ARCHIVIATA (esclusa da export)
    - Marca supervisione come ARCHIVIATA
    - Crea pattern se archiviazione ricorrente per stesso AIC
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT sl.*, od.id_dettaglio
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        WHERE sl.id_supervisione = %s AND sl.stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o già processata")

    sup = dict(sup)

    # Archivia la riga ordine
    if sup.get('id_dettaglio'):
        db.execute("""
            UPDATE ordini_dettaglio
            SET stato_riga = 'ARCHIVIATA',
                note_supervisione = %s,
                confermato_da = %s,
                data_conferma = CURRENT_TIMESTAMP
            WHERE id_dettaglio = %s
        """, (f"Archiviata: {req.motivo}", req.operatore, sup['id_dettaglio']))

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_listino
        SET stato = 'ARCHIVIATA',
            azione = 'ARCHIVIA',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s
        WHERE id_supervisione = %s
    """, (req.operatore, f"{req.motivo}. {req.note or ''}", id_supervisione))

    # Crea/aggiorna pattern per archiviazione
    pattern_sig = f"LST_ARCH_{sup.get('vendor', '')}_{sup.get('codice_aic', '')}"
    db.execute("""
        INSERT INTO criteri_ordinari_listino
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia, codice_aic,
             count_approvazioni, azione_pattern)
        VALUES (%s, %s, %s, %s, %s, 1, 'ARCHIVIA')
        ON CONFLICT (pattern_signature) DO UPDATE SET
            count_approvazioni = criteri_ordinari_listino.count_approvazioni + 1,
            is_ordinario = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN TRUE ELSE FALSE END,
            data_promozione = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN CURRENT_TIMESTAMP ELSE NULL END
    """, (pattern_sig, f"Archivia AIC {sup.get('codice_aic')} - {req.motivo}",
          sup.get('vendor', ''), sup.get('codice_anomalia', ''), sup.get('codice_aic', '')))

    # Risolvi anomalia
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s
        WHERE id_anomalia = %s
    """, (f"Archiviata da {req.operatore}: {req.motivo}", sup.get('id_anomalia')))

    db.commit()

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "ARCHIVIATA",
        "operatore": req.operatore,
        "motivo": req.motivo,
        "pattern_signature": pattern_sig
    }


@router.get("/listino/pattern/{codice_aic}", summary="Pattern per AIC")
async def get_pattern_listino(codice_aic: str, vendor: Optional[str] = None):
    """
    v7.0: Ritorna pattern appresi per un codice AIC.

    Usato per suggerire automaticamente correzioni basate su decisioni precedenti.
    """
    db = get_db()

    query = """
        SELECT * FROM criteri_ordinari_espositore_listino
        WHERE codice_aic = %s
    """
    params = [codice_aic]

    if vendor:
        query += " AND vendor = %s"
        params.append(vendor)

    query += " ORDER BY count_approvazioni DESC"

    rows = db.execute(query, tuple(params)).fetchall()

    return {
        "codice_aic": codice_aic,
        "count": len(rows),
        "patterns": [dict(r) for r in rows]
    }


# =============================================================================
# v8.0: ENDPOINT SUPERVISIONE RAGGRUPPATA PER PATTERN
# =============================================================================

@router.get("/pending/grouped", summary="Supervisioni raggruppate per pattern")
async def get_pending_grouped():
    """
    v8.0: Ritorna supervisioni pending raggruppate per pattern_signature.

    Ogni gruppo include:
    - pattern_signature: Identificativo univoco pattern
    - tipo_supervisione: espositore/listino/lookup
    - total_count: Numero supervisioni nel gruppo
    - affected_order_ids: Lista ID ordini coinvolti
    - affected_orders_preview: Preview numeri ordine (es: "123, 456, 789")
    - pattern_count: Contatore approvazioni ML
    - pattern_ordinario: Se il pattern e automatico

    Usato per approvazione bulk: approvando un pattern si risolvono
    tutte le supervisioni con quel pattern.
    """
    from ..services.supervision.bulk import get_supervisioni_grouped_pending

    groups = get_supervisioni_grouped_pending()

    return {
        "count": len(groups),
        "total_supervisioni": sum(g.get('total_count', 0) for g in groups),
        "groups": groups
    }


@router.post("/pattern/{pattern_signature}/approva-bulk", summary="Approva bulk per pattern")
async def approva_pattern_bulk(pattern_signature: str, decisione: DecisioneApprova):
    """
    v8.0: Approva TUTTE le supervisioni pending con un dato pattern.

    Effetti:
    - Stato di tutte le supervisioni -> APPROVED
    - Pattern ML incrementato di 1 (non N per N supervisioni)
    - Tutti gli ordini coinvolti vengono sbloccati se non hanno altre supervisioni pending

    Args:
        pattern_signature: Signature del pattern da approvare
        decisione: Operatore e note opzionali

    Returns:
        Conteggio per tipo (espositore, listino, lookup) e lista ordini sbloccati
    """
    from ..services.supervision.bulk import approva_pattern_bulk

    results = approva_pattern_bulk(
        pattern_signature,
        decisione.operatore,
        decisione.note
    )

    if results['total'] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Nessuna supervisione pending trovata per pattern {pattern_signature}"
        )

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "APPROVED_BULK",
        "operatore": decisione.operatore,
        "approvate": results
    }


@router.post("/pattern/{pattern_signature}/rifiuta-bulk", summary="Rifiuta bulk per pattern")
async def rifiuta_pattern_bulk(pattern_signature: str, decisione: DecisioneRifiuta):
    """
    v8.0: Rifiuta TUTTE le supervisioni pending con un dato pattern.

    Effetti:
    - Stato di tutte le supervisioni -> REJECTED
    - Pattern ML resettato a 0
    - Gli ordini coinvolti rimangono bloccati (richiede intervento manuale)

    Args:
        pattern_signature: Signature del pattern da rifiutare
        decisione: Operatore e note (obbligatorie per motivazione)

    Returns:
        Conteggio per tipo
    """
    from ..services.supervision.bulk import rifiuta_pattern_bulk

    results = rifiuta_pattern_bulk(
        pattern_signature,
        decisione.operatore,
        decisione.note
    )

    if results['total'] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Nessuna supervisione pending trovata per pattern {pattern_signature}"
        )

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "REJECTED_BULK",
        "operatore": decisione.operatore,
        "note": decisione.note,
        "rifiutate": results
    }


# =============================================================================
# v8.0: ENDPOINT SUPERVISIONE LOOKUP
# =============================================================================

class RisoluzioneLookupRequest(BaseModel):
    """Richiesta risoluzione supervisione lookup."""
    operatore: str
    min_id: Optional[str] = None
    id_farmacia: Optional[int] = None
    note: Optional[str] = None


@router.get("/lookup/{id_supervisione}", summary="Dettaglio supervisione lookup")
async def get_supervisione_lookup_detail(id_supervisione: int):
    """
    v8.0: Ritorna dettagli supervisione lookup con suggerimenti farmacia.

    Include:
    - Dati anomalia (P.IVA estratta, metodo, score)
    - Suggerimenti farmacie simili dall'anagrafica
    - Pattern ML se esistente
    """
    db = get_db()

    # Recupera supervisione lookup
    sup = db.execute("""
        SELECT slk.*, colk.pattern_descrizione, colk.count_approvazioni, colk.is_ordinario
        FROM supervisione_lookup slk
        LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
        WHERE slk.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione lookup non trovata")

    sup = dict(sup)

    # Cerca farmacie suggerite per P.IVA parziale o simile
    suggerimenti = []
    if sup.get('partita_iva_estratta'):
        piva = sup['partita_iva_estratta']
        rows = db.execute("""
            SELECT id_farmacia, min_id, ragione_sociale, partita_iva, indirizzo, citta, provincia
            FROM anagrafica_farmacie
            WHERE partita_iva LIKE %s OR partita_iva = %s
            ORDER BY similarity(partita_iva, %s) DESC
            LIMIT 10
        """, (f"{piva}%", piva, piva)).fetchall()
        suggerimenti = [dict(r) for r in rows]

    return {
        **sup,
        "suggerimenti_farmacie": suggerimenti
    }


@router.post("/lookup/{id_supervisione}/risolvi", summary="Risolvi supervisione lookup")
async def risolvi_lookup(id_supervisione: int, req: RisoluzioneLookupRequest):
    """
    v8.0: Risolve supervisione lookup assegnando farmacia.

    Effetti:
    - Supervisione -> APPROVED
    - Ordine aggiornato con MIN ID e id_farmacia selezionata
    - Pattern ML incrementato
    - Ordine sbloccato se non ha altre supervisioni pending
    """
    from ..services.supervision.lookup import approva_supervisione_lookup

    success = approva_supervisione_lookup(
        id_supervisione,
        req.operatore,
        req.min_id,
        req.id_farmacia,
        req.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Supervisione lookup non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "APPROVED",
        "operatore": req.operatore,
        "min_id_assegnato": req.min_id
    }


@router.post("/lookup/{id_supervisione}/rifiuta", summary="Rifiuta supervisione lookup")
async def rifiuta_lookup(id_supervisione: int, decisione: DecisioneRifiuta):
    """
    v8.0: Rifiuta supervisione lookup.

    Effetti:
    - Supervisione -> REJECTED
    - Pattern ML resettato
    - Ordine sbloccato
    """
    from ..services.supervision.lookup import rifiuta_supervisione_lookup

    success = rifiuta_supervisione_lookup(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Supervisione lookup non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "REJECTED",
        "operatore": decisione.operatore,
        "note": decisione.note
    }
