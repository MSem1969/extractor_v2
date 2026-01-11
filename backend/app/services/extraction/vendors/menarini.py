"""
EXTRACTOR_TO - Estrattore MENARINI
===================================
Convertito da TO_EXTRACTOR_v6_0_DB_def.ipynb - Cella 10
Regole: REGOLE_MENARINI.md

v2.0 - Supporto Espositore Parent/Child
- Parent: codice "--" + keywords (BANCO, FSTAND, etc.)
- Child: righe successive, non più filtrate
- Chiusura: basata su somma valore netto
"""

import re
from typing import Dict, List, Optional, Tuple

from ....utils import parse_date, format_piva
from ...espositore import elabora_righe_ordine

# Import pdfplumber opzionale
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Keywords per identificare espositori
ESPOSITORE_KEYWORDS = r'BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA'


def _is_parent_espositore(cod_min: str, descrizione: str, prezzo_netto: float = 0.0) -> Tuple[bool, Optional[int]]:
    """
    Verifica se la riga è un parent espositore MENARINI.

    Args:
        cod_min: Codice ministeriale (es. "--" per parent)
        descrizione: Descrizione prodotto
        prezzo_netto: Prezzo netto della riga

    Returns:
        (is_parent, pezzi_per_unita)

    Nota: La riga espositore vuoto (omaggio) ha codice "--" ma prezzo_netto = 0,
          quindi NON è un parent ma un child.
    """
    # MENARINI: parent ha codice "--" e keywords espositore E prezzo > 0
    if cod_min != '--':
        return False, None

    # IMPORTANTE: Se prezzo netto = 0, è l'espositore vuoto (child), non parent!
    if prezzo_netto <= 0:
        return False, None

    desc_upper = descrizione.upper() if descrizione else ''
    if not re.search(ESPOSITORE_KEYWORDS, desc_upper, re.I):
        return False, None

    # Estrai pezzi da pattern XXPZ (dentro la descrizione)
    pezzi_match = re.search(r'(\d+)\s*PZ', desc_upper)
    pezzi_per_unita = int(pezzi_match.group(1)) if pezzi_match else None

    return True, pezzi_per_unita


def extract_menarini(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore MENARINI v2.0.

    v2.0: Supporto espositore parent/child
    - NON filtra più i child
    - Rileva parent con codice "--" + keywords
    - Traccia relazioni parent/child per elaborazione espositore
    """
    if not pdf_path or not PDFPLUMBER_AVAILABLE:
        return _extract_menarini_text_fallback(text, lines)

    all_orders = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                words = page.extract_words()
                tables = page.extract_tables()

                # Raggruppa parole per Y (riga)
                rows_by_y = {}
                for w in words:
                    y_key = round(w['top'], 0)
                    if y_key not in rows_by_y:
                        rows_by_y[y_key] = []
                    rows_by_y[y_key].append(w)

                # Identifica coordinate X dei prodotti
                product_coords = []
                for y_key in sorted(rows_by_y.keys()):
                    row_words = sorted(rows_by_y[y_key], key=lambda w: w['x0'])
                    if row_words:
                        first_text = row_words[0]['text'].upper()
                        x0 = row_words[0]['x0']
                        # Keyword prodotti MENARINI
                        keywords = ['AFTAMED', 'FASTUM', 'SUSTENIUM', 'NEBUL', 
                                    'MOMENT', 'VIVIN', 'GLORIA', 'COLLIRIO']
                        if any(kw in first_text for kw in keywords):
                            is_child = (x0 >= 28)  # Soglia indentazione
                            product_coords.append({'y': y_key, 'is_child': is_child, 'x0': x0})

                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    if not header or 'Prodotto' not in str(header):
                        continue

                    data = {'vendor': 'MENARINI', 'righe': []}

                    # Estrazione header
                    m = re.search(r'Ordine\s+N\.?:?\s*(\d+)(?:_\d{8})?', page_text)
                    if m:
                        data['numero_ordine'] = m.group(1).strip()

                    m = re.search(r'Cliente\s+(.+?)\s+Cod\.?\s*Cliente', page_text)
                    if m:
                        data['ragione_sociale'] = m.group(1).strip()[:50]

                    m = re.search(r'Partita\s+IVA\s+(\d{11})', page_text)
                    if m:
                        data['partita_iva'] = format_piva(m.group(1))

                    m = re.search(r'Indirizzo\s+(.+?)\s+CAP\s+(\d{5})', page_text)
                    if m:
                        data['indirizzo'] = m.group(1).strip()[:50]
                        data['cap'] = m.group(2)

                    m = re.search(r"Città\s+([A-Z][A-Z\s/'-]+?)\s+Provincia\s+([A-Z]{2})", page_text)
                    if m:
                        data['citta'] = m.group(1).strip()[:50]
                        data['provincia'] = m.group(2)

                    m = re.search(r'Rep\s+([A-Z][A-Z\s]+?)\s+Tipo\s+Ordine', page_text)
                    if m:
                        data['nome_agente'] = m.group(1).strip()[:50]

                    m = re.search(r'Data\s+Ordine\s+(\d{2}/\d{2}/\d{4})', page_text)
                    if m:
                        data['data_ordine'] = parse_date(m.group(1))

                    m = re.search(r'Data\s+Consegna\s+(\d{2}/\d{2}/\d{4})', page_text)
                    if m:
                        data['data_consegna'] = parse_date(m.group(1))

                    m = re.search(r'(\d+)\s*GG', page_text, re.I)
                    data['gg_dilazione'] = int(m.group(1)) if m else 90

                    # Estrazione righe dalla tabella
                    data_rows = [r for r in table[1:] if r and r[0] and not str(r[0]).strip().startswith('Totale')]

                    n_riga = 0
                    # v2.0: Tracciamento parent/child per espositori
                    # La chiusura viene gestita da elabora_righe_ordine()
                    has_active_parent = False  # True se c'è un parent aperto

                    for idx, row in enumerate(data_rows):
                        desc_raw = str(row[0] or '').strip()
                        if not desc_raw:
                            continue

                        cod_min = str(row[1] or '').strip() if len(row) > 1 else ''

                        try:
                            qty = int(str(row[2] or '0').strip()) if len(row) > 2 else 0
                        except:
                            qty = 0

                        try:
                            prezzo = float(str(row[3] or '0').replace('€', '').replace(',', '.').strip()) if len(row) > 3 else 0.0
                        except:
                            prezzo = 0.0

                        sconto_str = str(row[4] or '--').strip() if len(row) > 4 else '--'
                        sconto1 = 0.0
                        if sconto_str != '--':
                            try:
                                sconto1 = float(sconto_str.replace('%', '').replace(',', '.'))
                            except:
                                pass

                        sm = str(row[5] or '--').strip() if len(row) > 5 else '--'
                        om = str(row[6] or '--').strip() if len(row) > 6 else '--'
                        q_sm = int(sm) if sm.isdigit() else 0
                        q_om = int(om) if om.isdigit() else 0
                        q_omaggio = q_sm + q_om

                        pn = str(row[7] or '--').replace('€', '').replace(',', '.').strip() if len(row) > 7 else '--'
                        prezzo_netto = float(pn) if pn and pn != '--' else 0.0

                        descrizione = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', desc_raw).strip()[:40]

                        # v2.0: Verifica se parent espositore (prezzo_netto > 0)
                        is_parent, pezzi_per_unita = _is_parent_espositore(cod_min, descrizione, prezzo_netto)

                        if is_parent:
                            # Nuovo parent - la chiusura del precedente viene gestita da elabora_righe_ordine()
                            has_active_parent = True

                            n_riga += 1
                            data['righe'].append({
                                'n_riga': n_riga,
                                'codice_aic': '',  # Parent non ha AIC
                                'codice_originale': cod_min,  # "--"
                                'descrizione': descrizione,
                                'data_consegna': data.get('data_consegna'),
                                'q_venduta': qty,
                                'quantita': qty,
                                'q_omaggio': q_omaggio,
                                'sconto1': sconto1,
                                'prezzo_pubblico': prezzo,
                                'prezzo_netto': prezzo_netto,
                                'is_espositore': True,
                                'is_child': False,
                                'tipo_riga': 'PARENT_ESPOSITORE',
                                'pezzi_per_unita': pezzi_per_unita,
                                'prezzo_netto_parent': prezzo_netto,
                                'anomalia_no_aic': False,
                            })
                            continue

                        # v2.0: Dopo un parent, TUTTE le righe successive sono child
                        # La chiusura viene determinata da elabora_righe_ordine() in base ai pezzi
                        is_child_of_parent = has_active_parent

                        # Codice non-AIC (es. 87AA09) in un child = espositore vuoto (omaggio)
                        is_aic = bool(re.match(r'^\d{9}$', cod_min))
                        is_espositore_vuoto = is_child_of_parent and not is_aic and cod_min != '--'

                        n_riga += 1
                        riga_data = {
                            'n_riga': n_riga,
                            'codice_aic': cod_min if is_aic else '',
                            'codice_originale': cod_min,
                            'descrizione': descrizione,
                            'data_consegna': data.get('data_consegna'),
                            'q_venduta': qty,
                            'quantita': qty,
                            'q_omaggio': q_omaggio,
                            'sconto1': sconto1,
                            'prezzo_pubblico': prezzo,
                            'prezzo_netto': prezzo_netto,
                            'is_espositore': False,  # Child non sono espositori
                            'is_child': is_child_of_parent,
                            'is_espositore_vuoto': is_espositore_vuoto,  # v2.0: marca espositore vuoto
                            'anomalia_no_aic': not is_aic and not is_child_of_parent,
                        }

                        # v2.0: Marca child
                        if is_child_of_parent:
                            riga_data['_belongs_to_parent'] = True
                            riga_data['tipo_riga'] = 'CHILD_ESPOSITORE'

                        data['righe'].append(riga_data)

                    # v2.0: Elabora righe con logica espositori
                    if data.get('righe'):
                        righe_raw = data['righe']
                        data['righe_raw'] = righe_raw

                        # Elabora con logica espositori MENARINI
                        ctx = elabora_righe_ordine(righe_raw, vendor='MENARINI')
                        data['righe'] = ctx.righe_output
                        data['anomalie_espositore'] = ctx.anomalie
                        data['_stats'] = {
                            'righe_raw': len(righe_raw),
                            'righe_output': len(ctx.righe_output),
                            'espositori': ctx.espositori_elaborati,
                            'chiusure_normali': ctx.chiusure_normali,
                            'chiusure_forzate': ctx.chiusure_forzate,
                            'anomalie': len(ctx.anomalie),
                        }

                        all_orders.append(data)

    except Exception as e:
        print(f"   ⚠️ Errore estrazione MENARINI: {e}")
        return _extract_menarini_text_fallback(text, lines)

    return all_orders if all_orders else _extract_menarini_text_fallback(text, lines)


def _extract_menarini_text_fallback(text: str, lines: List[str]) -> List[Dict]:
    """Fallback MENARINI quando pdf_path non è disponibile."""
    data = {'vendor': 'MENARINI', 'righe': []}

    m = re.search(r'Ordine\s+N\.?:?\s*(\d+)(?:_\d{8})?', text)
    if m:
        data['numero_ordine'] = m.group(1).strip()

    m = re.search(r'Cliente\s+(.+?)\s+Cod\.?\s*Cliente', text)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:50]

    m = re.search(r'Partita\s+IVA\s+(\d{11})', text)
    if m:
        data['partita_iva'] = format_piva(m.group(1))

    m = re.search(r'Indirizzo\s+(.+?)\s+CAP\s+(\d{5})', text)
    if m:
        data['indirizzo'] = m.group(1).strip()[:50]
        data['cap'] = m.group(2)

    m = re.search(r"Città\s+([A-Z][A-Z\s/'-]+?)\s+Provincia\s+([A-Z]{2})", text)
    if m:
        data['citta'] = m.group(1).strip()[:50]
        data['provincia'] = m.group(2)

    m = re.search(r'Data\s+Ordine\s+(\d{2}/\d{2}/\d{4})', text)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    m = re.search(r'Data\s+Consegna\s+(\d{2}/\d{2}/\d{4})', text)
    if m:
        data['data_consegna'] = parse_date(m.group(1))

    m = re.search(r'(\d+)\s*GG', text, re.I)
    data['gg_dilazione'] = int(m.group(1)) if m else 90

    n_riga = 0
    for line in lines:
        line_stripped = line.strip()
        m = re.search(r'(\d{9})\s+(\d+)\s+', line_stripped)
        if m:
            cod_min = m.group(1)
            qty = int(m.group(2))

            if line.startswith('  ') or line.startswith('\t'):
                continue

            desc_match = re.match(r'^(.+?)\s+\d{9}', line_stripped)
            descrizione = desc_match.group(1).strip()[:40] if desc_match else ''

            n_riga += 1
            is_espositore = (cod_min == '--' or not re.match(r'^\d{9}$', cod_min))

            data['righe'].append({
                'n_riga': n_riga,
                'codice_aic': '' if is_espositore else cod_min,
                'codice_originale': cod_min,
                'descrizione': descrizione,
                'q_venduta': qty,
                'is_espositore': is_espositore,
                'is_child': False,
                'anomalia_no_aic': is_espositore,
            })

    return [data] if data.get('righe') or data.get('numero_ordine') else [{'vendor': 'MENARINI', 'righe': []}]
