# =============================================================================
# TO_EXTRACTOR v7.0 - ESTRATTORI PACKAGE (DEPRECATO)
# =============================================================================
# DEPRECATO: Usare app.services.extraction invece
#
# Questo modulo è mantenuto per retrocompatibilità.
# Verrà rimosso nella versione 8.0.
# =============================================================================

import warnings

warnings.warn(
    "Il modulo app.extractors è deprecato. "
    "Usare app.services.extraction invece.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export dalla nuova posizione per retrocompatibilità
from ..services.extraction import (
    get_extractor,
    get_supported_vendors,
    EXTRACTORS,
    detect_vendor,
)

# Mantiene BaseExtractor e GenericExtractor per retrocompatibilità
from .base import BaseExtractor, GenericExtractor

# Classes legacy - wrapped per retrocompatibilità
from .angelini import AngeliniExtractor
from .bayer import BayerExtractor
from .chiesi import ChiesiExtractor
from .codifi import CodifiExtractor
from .menarini import MenariniExtractor
from .opella import OpellaExtractor


__all__ = [
    'BaseExtractor',
    'GenericExtractor',
    'AngeliniExtractor',
    'BayerExtractor',
    'ChiesiExtractor',
    'CodifiExtractor',
    'MenariniExtractor',
    'OpellaExtractor',
    'EXTRACTORS',
    'get_extractor',
    'get_supported_vendors',
    'detect_vendor',
]
