# =============================================================================
# TO_EXTRACTOR v7.0 - SERVICES/EXTRACTORS (DEPRECATO)
# =============================================================================
# DEPRECATO: Usare app.services.extraction invece
#
# Questo modulo è mantenuto per retrocompatibilità.
# Verrà rimosso nella versione 8.0.
# =============================================================================

import warnings

warnings.warn(
    "Il modulo app.services.extractors è deprecato. "
    "Usare app.services.extraction invece.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export dalla nuova posizione per retrocompatibilità
from ..extraction import (
    extract_angelini,
    extract_bayer,
    extract_chiesi,
    extract_codifi,
    extract_opella,
    extract_menarini,
    extract_doc_generici,
    extract_generic,
    get_extractor,
    EXTRACTORS,
)

__all__ = [
    'extract_angelini',
    'extract_bayer',
    'extract_chiesi',
    'extract_codifi',
    'extract_opella',
    'extract_menarini',
    'extract_doc_generici',
    'extract_generic',
    'get_extractor',
    'EXTRACTORS',
]
