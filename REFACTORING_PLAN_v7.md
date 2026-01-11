# Piano di Refactoring TO_EXTRACTOR v6.2 → v7.0

> **Stato**: In attesa - Prima risolvere bug esistenti
> **Data creazione**: 2026-01-09
> **Autore**: Claude Code

## Obiettivo
Refactoring Full Stack modulare con modernizzazione, mantenendo stabilità operativa attraverso verifiche progressive dopo ogni fase.

## Principi Guida
- **Modulare**: Un modulo alla volta, completamente testato prima del successivo
- **Progressivo**: Ogni fase include test di verifica funzionale
- **Retrocompatibile**: API esistenti mantenute durante transizione
- **Modernizzazione**: Nuove dipendenze dove portano valore reale

---

## Analisi Criticità Attuali

### Backend (21.530 LOC)
| File | LOC | Problema |
|------|-----|----------|
| `services/ordini.py` | 1307 | Monolite, 77 query sparse, responsabilità miste |
| `services/tracciati.py` | 965 | Formattazione + generazione + validazione |
| `services/supervisione.py` | 857 | Anomalie + ML + approval workflow |
| `extractors/` + `services/extractors/` | 3350 | **Duplicazione 50%** - stesso codice in 2 cartelle |
| `database.py` + `database_pg.py` | 1614 | **2 implementazioni parallele** |
| `utils.py` | 748 | 20+ funzioni sparse senza coesione |

### Frontend (10.000+ LOC)
| File | LOC | Problema |
|------|-----|----------|
| `OrdineDetailPage.jsx` | 1462 | 20 useState, logica mista |
| `DatabasePage.jsx` | 1236 | 25 useState, tab + filtri + batch |
| `SettingsPage.jsx` | 1092 | 4 tab, config miste |
| `App_old.jsx` | 3963 | **FILE LEGACY da eliminare** |

### Database
| Problema | Impatto |
|----------|---------|
| N+1 in `get_ordine_detail()` | 4 query per 1 ordine |
| Dashboard stats | 8+ query invece di 1 |
| Indici mancanti | Performance degradata |
| Fuzzy lookup O(N) | 20K match per ordine |

---

## Fasi di Implementazione

### FASE 0: Preparazione (1 giorno)
**Obiettivo**: Setup ambiente e backup

- [ ] Creare branch `refactor/v7.0`
- [ ] Backup database PostgreSQL
- [ ] Documentare API endpoints attuali per regression test
- [ ] Installare dipendenze dev (pytest, jest se mancanti)

**Verifica**: Branch creato, backup funzionante

---

### FASE 1: Pulizia e Organizzazione (2 giorni)

#### 1.1 Backend - Eliminare duplicazione extractors
**File coinvolti**:
- `backend/app/extractors/` (deprecare)
- `backend/app/services/extractors/` (mantenere e consolidare)

**Azioni**:
- [ ] Unificare extractors in `services/extraction/`
- [ ] Creare factory pattern in `__init__.py`
- [ ] Deprecare cartella `/extractors/` con warning
- [ ] Aggiornare import in `pdf_processor.py`

**Nuova struttura**:
```
services/extraction/
├── __init__.py          # get_extractor() factory
├── base.py              # BaseExtractor (esistente)
├── vendors/
│   ├── angelini.py
│   ├── bayer.py
│   ├── codifi.py
│   ├── chiesi.py
│   ├── menarini.py
│   ├── opella.py
│   └── doc_generici.py
└── detector.py          # detect_vendor() da utils.py
```

#### 1.2 Backend - Riorganizzare utils.py
**Azioni**:
- [ ] Creare `utils/` package con moduli tematici:
  - `utils/dates.py` - parse_date, format_date_edi, etc.
  - `utils/quantities.py` - calcola_q_totale
  - `utils/hashing.py` - compute_file_hash
  - `utils/conversions.py` - parse_decimal, format_currency
- [ ] Mantenere `utils/__init__.py` con re-export per retrocompatibilità

#### 1.3 Frontend - Eliminare file legacy
**Azioni**:
- [ ] Rimuovere `App_old.jsx` (3963 LOC)
- [ ] Rimuovere `OrdineDetailPage.jsx.backup`
- [ ] Creare struttura directory:
  ```
  src/
  ├── pages/           # Spostare *Page.jsx qui
  ├── hooks/           # Custom hooks
  ├── context/         # Context providers
  ├── components/      # (esistente)
  ├── common/          # (esistente)
  └── layout/          # (esistente)
  ```
- [ ] Aggiornare import in `App.jsx`

**Verifica Fase 1**:
- [ ] `npm run dev` frontend funziona
- [ ] `uvicorn app.main:app` backend funziona
- [ ] Upload PDF → estrazione → ordine creato OK
- [ ] Tutti i vendor estratti correttamente

---

### FASE 2: Database Layer (3 giorni)

#### 2.1 Deprecare SQLite, consolidare PostgreSQL
**File coinvolti**:
- `backend/app/database.py` (deprecare)
- `backend/app/database_pg.py` (refactoring)

**Azioni**:
- [ ] Creare `persistence/` package:
  ```
  persistence/
  ├── __init__.py         # get_db(), init_pool()
  ├── connection.py       # PostgreSQLConnection (da database_pg.py)
  └── repositories/
      ├── __init__.py
      ├── base.py         # BaseRepository
      ├── ordini.py       # OrdiniRepository
      ├── anomalie.py     # AnomalieRepository
      └── acquisizioni.py # AcquisizioniRepository
  ```
- [ ] Implementare Repository pattern per query comuni
- [ ] Deprecare `database.py` con warning (non rimuovere subito)

#### 2.2 Ottimizzare query critiche
**Azioni**:
- [ ] Creare vista `V_ORDINE_COMPLETO_JSON` con LEFT JOIN + JSON aggregation
- [ ] Consolidare dashboard stats in 1 query CTE
- [ ] Aggiungere indici mancanti:
  ```sql
  CREATE INDEX idx_testata_stato_data ON ordini_testata(stato, data_estrazione DESC);
  CREATE INDEX idx_dettaglio_stato_testata ON ordini_dettaglio(stato_riga, id_testata);
  CREATE INDEX idx_anomalie_operatore ON anomalie(id_operatore_gestione);
  ```

#### 2.3 Cache layer per query frequenti
**Azioni**:
- [ ] Implementare `@lru_cache` con TTL per dashboard stats
- [ ] Cache vendor list (statica)
- [ ] Cache anagrafica lookup (refresh ogni 5 min)

**Verifica Fase 2**:
- [ ] Dashboard carica in <500ms (prima ~2s)
- [ ] Dettaglio ordine carica in <200ms
- [ ] Nessuna regressione su CRUD ordini

---

### FASE 3: Backend Services Refactoring (5 giorni)

#### 3.1 Decomposizione ordini.py (1307 LOC → 4 moduli)
**Nuova struttura**:
```
services/orders/
├── __init__.py
├── queries.py          # OrdiniRepository queries
├── commands.py         # create, update, delete, confirm
├── fulfillment.py      # evasione, tracciati generation
└── validators.py       # validazione business rules
```

**Mapping funzioni**:
| Funzione attuale | Nuovo modulo |
|------------------|--------------|
| `get_ordini()`, `get_ordine_detail()` | `queries.py` |
| `crea_ordine()`, `update_ordine()` | `commands.py` |
| `conferma_riga()`, `conferma_tutte()` | `commands.py` |
| `genera_tracciato()` | `fulfillment.py` |
| `valida_ordine()` | `validators.py` |

#### 3.2 Decomposizione tracciati.py (965 LOC → 3 moduli)
**Nuova struttura**:
```
services/export/
├── __init__.py
├── formatters/
│   ├── to_t.py         # Formattazione testata EDI
│   └── to_d.py         # Formattazione dettaglio EDI
├── generator.py        # Generazione file tracciato
└── validators.py       # Validazione schema EDI
```

#### 3.3 Decomposizione supervisione.py (857 LOC → 3 moduli)
**Nuova struttura**:
```
services/supervision/
├── __init__.py
├── anomaly_detector.py  # Rilevamento anomalie
├── ml_patterns.py       # Pattern matching ML
└── workflow.py          # Approval state machine
```

**Verifica Fase 3**:
- [ ] Tutti gli endpoint API funzionano identicamente
- [ ] Upload → estrazione → conferma → tracciato OK
- [ ] Supervisione anomalie funziona
- [ ] ML pattern matching funziona

---

### FASE 4: Frontend Modernizzazione (5 giorni)

#### 4.1 Installare dipendenze moderne
```bash
npm install @tanstack/react-query zustand react-hook-form zod date-fns
```

#### 4.2 Implementare Context API
**File da creare**:
```
src/context/
├── AuthContext.jsx      # user, login, logout
├── UIContext.jsx        # activeTab, modals, notifications
└── index.js
```

**Migrare da props a context**:
- `currentUser` → `AuthContext`
- `activePage`, `onPageChange` → `UIContext`

#### 4.3 Implementare React Query per data fetching
**File da modificare**:
- `api.js` → aggiungere hooks `useOrdini()`, `useOrdine()`, `useAnomalies()`

**Benefici**:
- Caching automatico
- Retry su errore
- Deduplicazione richieste
- Loading/error states automatici

#### 4.4 Decomposizione OrdineDetailPage.jsx (1462 LOC → 5 componenti)
**Nuova struttura**:
```
src/pages/OrdineDetail/
├── index.jsx            # Container principale (~200 LOC)
├── OrdineHeader.jsx     # Testata + stato + azioni
├── RigheTable.jsx       # Tabella righe con editing
├── RigaEditForm.jsx     # Form modifica riga (react-hook-form)
├── AnomalieTab.jsx      # Tab anomalie
└── hooks/
    └── useOrdineDetail.js  # Custom hook per logica
```

#### 4.5 Decomposizione DatabasePage.jsx (1236 LOC → 4 componenti)
**Nuova struttura**:
```
src/pages/Database/
├── index.jsx            # Container (~150 LOC)
├── OrdiniTab.jsx        # Tab ordini + filtri
├── AnomalieTab.jsx      # Tab anomalie (shared?)
├── FilterBar.jsx        # Barra filtri
└── BatchActions.jsx     # Azioni batch
```

**Verifica Fase 4**:
- [ ] Login/logout funziona
- [ ] Navigazione tra pagine OK
- [ ] CRUD ordini da frontend OK
- [ ] Filtri e batch actions OK
- [ ] No regressioni UI

---

### FASE 5: Testing e Documentazione (2 giorni)

#### 5.1 Backend tests
- [ ] Test unitari per repository
- [ ] Test integrazione per API endpoints critici
- [ ] Test estrazione PDF per ogni vendor

#### 5.2 Frontend tests (opzionale)
- [ ] Test componenti critici con React Testing Library

#### 5.3 Documentazione
- [ ] Aggiornare `CLAUDE.md` con nuova struttura
- [ ] Documentare nuove API se cambiate
- [ ] Changelog v6.2 → v7.0

**Verifica Finale**:
- [ ] Tutti i test passano
- [ ] Performance migliorata (misurare)
- [ ] Nessuna regressione funzionale

---

## Nuova Struttura Progetto (Target v7.0)

### Backend
```
backend/app/
├── main.py
├── config.py
├── models.py
├── persistence/              # NEW - Database layer
│   ├── __init__.py
│   ├── connection.py
│   └── repositories/
│       ├── ordini.py
│       ├── anomalie.py
│       └── ...
├── services/
│   ├── orders/               # NEW - Da ordini.py
│   │   ├── queries.py
│   │   ├── commands.py
│   │   └── fulfillment.py
│   ├── export/               # NEW - Da tracciati.py
│   │   ├── formatters/
│   │   └── generator.py
│   ├── supervision/          # NEW - Da supervisione.py
│   │   ├── anomaly_detector.py
│   │   └── workflow.py
│   ├── extraction/           # NEW - Unificato
│   │   ├── base.py
│   │   └── vendors/
│   ├── lookup.py             # Mantenuto
│   └── anagrafica.py         # Mantenuto
├── routers/                  # Mantenuti, aggiornati import
├── auth/                     # Mantenuto
└── utils/                    # NEW - Package organizzato
    ├── dates.py
    ├── quantities.py
    └── ...
```

### Frontend
```
frontend/src/
├── api.js                    # + React Query hooks
├── App.jsx
├── main.jsx
├── context/                  # NEW
│   ├── AuthContext.jsx
│   └── UIContext.jsx
├── hooks/                    # Espanso
│   ├── useOrdini.js
│   └── useSessionTracking.js
├── pages/                    # NEW - Pagine spostate
│   ├── Database/
│   │   ├── index.jsx
│   │   ├── OrdiniTab.jsx
│   │   └── FilterBar.jsx
│   ├── OrdineDetail/
│   │   ├── index.jsx
│   │   ├── RigheTable.jsx
│   │   └── RigaEditForm.jsx
│   ├── Upload/
│   ├── Settings/
│   └── ...
├── components/               # Mantenuto
├── common/                   # Mantenuto
└── layout/                   # Mantenuto
```

---

## Timeline Stimata

| Fase | Durata | Dipendenze |
|------|--------|------------|
| Fase 0: Preparazione | 1 giorno | - |
| Fase 1: Pulizia | 2 giorni | Fase 0 |
| Fase 2: Database | 3 giorni | Fase 1 |
| Fase 3: Backend Services | 5 giorni | Fase 2 |
| Fase 4: Frontend | 5 giorni | Fase 1 (può essere parallela a Fase 3) |
| Fase 5: Testing | 2 giorni | Fase 3, 4 |

**Totale**: ~18 giorni lavorativi (3-4 settimane)

---

## Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Regressione API | Media | Alto | Test dopo ogni fase, rollback branch |
| Performance peggiorata | Bassa | Alto | Benchmark prima/dopo |
| Breaking change frontend | Media | Medio | Verifica manuale UI dopo Fase 4 |
| Conflitti merge | Media | Basso | Commit frequenti, rebase regolare |

---

## Metriche di Successo

| Metrica | Prima | Target |
|---------|-------|--------|
| File >500 LOC backend | 6 | 0 |
| File >500 LOC frontend | 7 | 0 |
| Query per dashboard | 8+ | 1-2 |
| useState per pagina | 20-25 | 5-8 |
| Duplicazione extractors | 50% | 0% |
| Database layers | 2 | 1 |

---

## Note Implementative

### Retrocompatibilità API
Durante il refactoring, mantenere gli endpoint API identici. Refactoring interno non deve cambiare contratto API.

### Import Aliases
Usare import alias per facilitare transizione:
```python
# services/ordini.py (deprecated)
from .orders import *  # Re-export per retrocompatibilità
```

### Feature Flags (opzionale)
Se necessario, usare feature flag per attivare nuova implementazione gradualmente:
```python
if config.USE_NEW_ORDERS_SERVICE:
    from .orders import get_ordine
else:
    from .ordini_legacy import get_ordine
```

---

## Prerequisiti Prima del Refactoring

> **IMPORTANTE**: Prima di iniziare il refactoring, risolvere tutti i bug esistenti per ridurre la complessità.

### Bug da risolvere prima:
- [ ] (elencare bug noti qui)

### Quando iniziare:
- Tutti i bug critici risolti
- Sistema stabile in produzione
- Tempo disponibile per focus completo
