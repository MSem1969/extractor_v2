// =============================================================================
// SUPERVISIONE PAGE - MODERNIZZATA v7.0
// =============================================================================
// Pagina supervisione ML con pattern recognition, workflow di approvazione
// Machine Learning per espositori ANGELINI e listino CODIFI v7.0
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { supervisioneApi } from '../api';
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from '../common';

// =============================================================================
// MODALE CORREZIONE LISTINO
// =============================================================================
const CorrezioneLisinoModal = ({ isOpen, onClose, supervisione, operatore, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detail, setDetail] = useState(null);
  const [formData, setFormData] = useState({
    prezzo_netto: '',
    prezzo_pubblico: '',
    sconto_1: '',
    sconto_2: '',
    sconto_3: '',
    sconto_4: '',
    aliquota_iva: '',
    applica_a_listino: false,
    note: '',
  });

  // Carica dettagli e suggerimenti quando si apre
  useEffect(() => {
    if (isOpen && supervisione?.id_supervisione) {
      setLoadingDetail(true);
      supervisioneApi.getListinoDetail(supervisione.id_supervisione)
        .then(res => {
          setDetail(res);
          // Pre-popola form con valori correnti o suggeriti
          const riga = res.riga_corrente || {};
          const suggerimenti = res.suggerimenti || {};
          setFormData({
            prezzo_netto: suggerimenti.prezzo_netto || riga.prezzo_netto || '',
            prezzo_pubblico: suggerimenti.prezzo_pubblico || riga.prezzo_pubblico || '',
            sconto_1: suggerimenti.sconto_1 || riga.sconto_1 || '',
            sconto_2: suggerimenti.sconto_2 || riga.sconto_2 || '',
            sconto_3: suggerimenti.sconto_3 || riga.sconto_3 || '',
            sconto_4: suggerimenti.sconto_4 || riga.sconto_4 || '',
            aliquota_iva: suggerimenti.aliquota_iva || riga.aliquota_iva || '10',
            applica_a_listino: false,
            note: '',
          });
        })
        .catch(err => console.error('Errore caricamento dettaglio listino:', err))
        .finally(() => setLoadingDetail(false));
    }
  }, [isOpen, supervisione]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const payload = {
        operatore,
        prezzo_netto: formData.prezzo_netto ? parseFloat(formData.prezzo_netto) : null,
        prezzo_pubblico: formData.prezzo_pubblico ? parseFloat(formData.prezzo_pubblico) : null,
        sconto_1: formData.sconto_1 ? parseFloat(formData.sconto_1) : null,
        sconto_2: formData.sconto_2 ? parseFloat(formData.sconto_2) : null,
        sconto_3: formData.sconto_3 ? parseFloat(formData.sconto_3) : null,
        sconto_4: formData.sconto_4 ? parseFloat(formData.sconto_4) : null,
        aliquota_iva: formData.aliquota_iva ? parseFloat(formData.aliquota_iva) : null,
        applica_a_listino: formData.applica_a_listino,
        note: formData.note || null,
      };

      await supervisioneApi.correggiListino(supervisione.id_supervisione, payload);
      onSuccess?.();
      onClose();
    } catch (err) {
      alert('Errore correzione: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const riga = detail?.riga_corrente || {};
  const suggerimenti = detail?.suggerimenti || {};
  const hasSuggerimenti = Object.keys(suggerimenti).length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">Correzione Listino</h3>
          <p className="text-sm text-slate-600 mt-1">
            AIC: <code className="bg-slate-100 px-2 py-0.5 rounded">{supervisione?.codice_aic}</code>
            {supervisione?.descrizione_prodotto && ` - ${supervisione.descrizione_prodotto}`}
          </p>
        </div>

        {loadingDetail ? (
          <div className="p-8 text-center">
            <Loading text="Caricamento dettagli..." />
          </div>
        ) : (
          <div className="p-6">
            {/* Suggerimenti pattern */}
            {hasSuggerimenti && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-blue-600">Suggerimento Pattern</span>
                  <StatusBadge status="info" size="xs" label={`${suggerimenti.count_utilizzi || 0} utilizzi`} />
                </div>
                <p className="text-sm text-blue-800">
                  Questo prodotto è stato corretto in precedenza. I valori suggeriti sono pre-compilati.
                </p>
              </div>
            )}

            {/* Valori correnti dalla riga */}
            {riga.id_dettaglio && (
              <div className="mb-6 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <h4 className="text-sm font-medium text-slate-700 mb-2">Valori Correnti Riga</h4>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <p><span className="text-slate-500">Prezzo Netto:</span> {riga.prezzo_netto || '-'}</p>
                  <p><span className="text-slate-500">Prezzo Pubblico:</span> {riga.prezzo_pubblico || '-'}</p>
                  <p><span className="text-slate-500">IVA:</span> {riga.aliquota_iva || '-'}%</p>
                  <p><span className="text-slate-500">Sconto 1:</span> {riga.sconto_1 || '0'}%</p>
                  <p><span className="text-slate-500">Sconto 2:</span> {riga.sconto_2 || '0'}%</p>
                  <p><span className="text-slate-500">Sconto 3:</span> {riga.sconto_3 || '0'}%</p>
                </div>
              </div>
            )}

            {/* Form correzione */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Prezzo Netto</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.prezzo_netto}
                  onChange={(e) => handleChange('prezzo_netto', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Prezzo Pubblico</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.prezzo_pubblico}
                  onChange={(e) => handleChange('prezzo_pubblico', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Aliquota IVA %</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.aliquota_iva}
                  onChange={(e) => handleChange('aliquota_iva', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="10"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 1 %</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.sconto_1}
                  onChange={(e) => handleChange('sconto_1', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 2 %</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.sconto_2}
                  onChange={(e) => handleChange('sconto_2', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 3 %</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.sconto_3}
                  onChange={(e) => handleChange('sconto_3', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 4 %</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.sconto_4}
                  onChange={(e) => handleChange('sconto_4', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="0"
                />
              </div>
              <div className="flex items-center pt-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.applica_a_listino}
                    onChange={(e) => handleChange('applica_a_listino', e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">Aggiungi al listino vendor</span>
                </label>
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">Note</label>
              <textarea
                value={formData.note}
                onChange={(e) => handleChange('note', e.target.value)}
                rows={2}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Note opzionali..."
              />
            </div>
          </div>
        )}

        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Annulla
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={loading}>
            Salva Correzione
          </Button>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// MODALE ARCHIVIAZIONE LISTINO
// =============================================================================
const ArchiviazioneListinoModal = ({ isOpen, onClose, supervisione, operatore, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [note, setNote] = useState('');

  const motiviPredefiniti = [
    'Prodotto non in listino vendor',
    'AIC errato o non valido',
    'Prodotto fuori produzione',
    'Prodotto di altro vendor',
    'Errore estrazione PDF',
    'Altro (specificare nelle note)',
  ];

  const handleSubmit = async () => {
    if (!motivo || motivo.trim().length < 5) {
      alert('Inserire un motivo valido (minimo 5 caratteri)');
      return;
    }

    setLoading(true);
    try {
      await supervisioneApi.archiviaListino(supervisione.id_supervisione, {
        operatore,
        motivo,
        note: note || null,
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      alert('Errore archiviazione: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">Archivia Riga</h3>
          <p className="text-sm text-slate-600 mt-1">
            La riga verrà esclusa dal tracciato EDI.
          </p>
        </div>

        <div className="p-6">
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>AIC:</strong> {supervisione?.codice_aic}<br />
              <strong>Prodotto:</strong> {supervisione?.descrizione_prodotto || 'N/A'}
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-slate-700 mb-2">Motivo Archiviazione</label>
            <div className="space-y-2">
              {motiviPredefiniti.map((m) => (
                <label key={m} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="motivo"
                    checked={motivo === m}
                    onChange={() => setMotivo(m)}
                    className="w-4 h-4 border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-slate-700">{m}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Note Aggiuntive</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Dettagli aggiuntivi..."
            />
          </div>
        </div>

        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Annulla
          </Button>
          <Button variant="danger" onClick={handleSubmit} loading={loading}>
            Archivia Riga
          </Button>
        </div>
      </div>
    </div>
  );
};

/**
 * Componente SupervisionePage modernizzato v7.0
 *
 * LOGICA IMPLEMENTATIVA:
 * - Sistema ML per pattern recognition su anomalie espositori e listino
 * - Supporta due tipi di supervisione: ESPOSITORE (ANGELINI) e LISTINO (CODIFI)
 * - Workflow APPROVE/REJECT/MODIFY con conteggio approvazioni
 * - Promozione automatica a "criterio ordinario" dopo 5 approvazioni
 * - Gestione pattern signature e fasci scostamento
 * - Dashboard ML con stats apprendimento
 *
 * INTERRELAZIONI:
 * - API: supervisioneApi.getPending(), approva(), rifiuta()
 * - ML: pattern signature, soglia promozione, reset automatico
 * - Workflow: blocco ordini, sblocco automatico, audit trail
 * - Navigazione: supporto ritorno a ordine specifico
 */
const SupervisionePage = ({
  supervisioneId,
  returnToOrdine,
  currentUser,
  onReturnToOrdine,
  onNavigateToOrdine // v9.0: Per navigare al dettaglio ordine
}) => {
  const [supervisioni, setSupervisioni] = useState([]);
  const [groupedSupervisioni, setGroupedSupervisioni] = useState([]);
  const [criteri, setCriteri] = useState([]);
  const [storico, setStorico] = useState([]); // v9.0: Storico decisioni
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  const [viewMode, setViewMode] = useState('grouped'); // v8.0: 'grouped' | 'individual'
  const operatore = currentUser?.username || 'admin';
  const [processingAction, setProcessingAction] = useState(null);
  const [processingPattern, setProcessingPattern] = useState(null); // v8.0: per bulk operations

  // State per modali listino
  const [correzioneModal, setCorrezioneModal] = useState({ isOpen: false, supervisione: null });
  const [archiviazioneModal, setArchiviazioneModal] = useState({ isOpen: false, supervisione: null });

  // Carica dati supervisione
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pendingRes, groupedRes, criteriRes, statsRes, storicoRes] = await Promise.all([
        supervisioneApi.getPending(),
        supervisioneApi.getPendingGrouped(), // v8.0: Carica anche dati raggruppati
        supervisioneApi.getCriteriTutti(),
        supervisioneApi.getCriteriStats(),
        supervisioneApi.getStorico(50), // v9.0: Storico decisioni
      ]);

      setSupervisioni(pendingRes?.supervisioni || []);
      setGroupedSupervisioni(groupedRes?.groups || []); // v8.0
      setCriteri(criteriRes?.criteri || []);
      setStorico(storicoRes?.applicazioni || []); // v9.0
      setStats(statsRes || {
        totale_pattern: 0,
        pattern_ordinari: 0,
        approvazioni_totali: 0,
        pending: 0
      });
    } catch (err) {
      console.error('Errore caricamento supervisione:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Actions con ML pattern tracking
  const handleApprova = async (id, patternSignature) => {
    if (!window.confirm('Confermi approvazione? Questo contribuirà all\'apprendimento ML.')) return;
    
    setProcessingAction(id);
    try {
      if (returnToOrdine && onReturnToOrdine) {
        // Modalità ritorno a ordine specifico
        await supervisioneApi.approvaETorna(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } else {
        // Modalità normale con ricarico dati
        await supervisioneApi.approva(id, operatore);
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleRifiuta = async (id, patternSignature) => {
    const note = window.prompt('Motivo del rifiuto (obbligatorio):\n\n⚠️ ATTENZIONE: Un rifiuto resetterà l\'apprendimento ML per questo pattern.');
    if (!note || note.trim().length < 5) {
      alert('Motivo troppo breve. Minimo 5 caratteri.');
      return;
    }
    
    setProcessingAction(id);
    try {
      await supervisioneApi.rifiuta(id, operatore, note);
      
      if (returnToOrdine && onReturnToOrdine) {
        onReturnToOrdine(returnToOrdine);
      } else {
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleModifica = async (id, modifiche) => {
    setProcessingAction(id);
    try {
      await supervisioneApi.modifica(id, operatore, modifiche);
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  // v8.0: Approvazione bulk per pattern
  const handleApprovaBulk = async (patternSignature, totalCount) => {
    if (!window.confirm(
      `Confermi approvazione di ${totalCount} supervisioni con questo pattern?\n\n` +
      `Questo contribuirà all'apprendimento ML (+1 approvazione per il pattern).`
    )) return;

    setProcessingPattern(patternSignature);
    try {
      const result = await supervisioneApi.approvaBulk(patternSignature, operatore);
      alert(
        `Approvate ${result.approvate?.total || 0} supervisioni:\n` +
        `- Espositore: ${result.approvate?.espositore || 0}\n` +
        `- Listino: ${result.approvate?.listino || 0}\n` +
        `- Lookup: ${result.approvate?.lookup || 0}\n\n` +
        `Ordini sbloccati: ${result.approvate?.orders_affected?.length || 0}`
      );
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingPattern(null);
    }
  };

  // v8.0: Rifiuto bulk per pattern
  const handleRifiutaBulk = async (patternSignature, totalCount) => {
    const note = window.prompt(
      `Stai per rifiutare ${totalCount} supervisioni.\n\n` +
      `ATTENZIONE: Questo resetterà l'apprendimento ML per questo pattern.\n\n` +
      `Inserisci il motivo del rifiuto (obbligatorio):`
    );
    if (!note || note.trim().length < 5) {
      alert('Motivo troppo breve. Minimo 5 caratteri.');
      return;
    }

    setProcessingPattern(patternSignature);
    try {
      const result = await supervisioneApi.rifiutaBulk(patternSignature, operatore, note);
      alert(`Rifiutate ${result.rifiutate?.total || 0} supervisioni.`);
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingPattern(null);
    }
  };

  const handleLasciaSospeso = async (id) => {
    if (returnToOrdine && onReturnToOrdine) {
      try {
        await supervisioneApi.lasciaSospeso(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } catch (err) {
        alert('Errore: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleResetPattern = async (signature) => {
    if (!window.confirm(
      'RESET PATTERN ML\n\n' +
      'Vuoi azzerare il contatore approvazioni per questo pattern?\n\n' +
      'L\'apprendimento ripartirà da zero e il pattern non sarà più automatico.'
    )) return;

    try {
      await supervisioneApi.resetPattern(signature, operatore);
      loadData();
    } catch (err) {
      alert('Errore reset: ' + err.message);
    }
  };

  const handlePromuoviPattern = async (signature) => {
    if (!window.confirm(
      'PROMUOVI PATTERN\n\n' +
      'Vuoi rendere questo pattern automatico?\n\n' +
      'Le future anomalie con questo pattern verranno gestite automaticamente.'
    )) return;

    try {
      await supervisioneApi.promuoviPattern(signature, operatore);
      loadData();
    } catch (err) {
      alert('Errore promozione: ' + err.message);
    }
  };

  // Handler apertura modale correzione listino
  const handleOpenCorrezione = (supervisione) => {
    setCorrezioneModal({ isOpen: true, supervisione });
  };

  // Handler apertura modale archiviazione listino
  const handleOpenArchiviazione = (supervisione) => {
    setArchiviazioneModal({ isOpen: true, supervisione });
  };

  // Handler successo operazioni listino
  const handleListinoSuccess = () => {
    loadData();
    if (returnToOrdine && onReturnToOrdine) {
      onReturnToOrdine(returnToOrdine);
    }
  };

  // Utility per calcolare progress ML
  const getMLProgress = (approvazioni) => {
    const soglia = 5; // Soglia per promozione automatica
    return Math.min((approvazioni / soglia) * 100, 100);
  };

  // Utility per determinare urgenza anomalia
  const getAnomaliaUrgency = (anomalia) => {
    if (anomalia.livello === 'CRITICO') return 'high';
    if (anomalia.tipo_scostamento === 'ECCESSO' && anomalia.percentuale_scostamento > 50) return 'high';
    if (anomalia.tipo_scostamento === 'DIFETTO' && anomalia.percentuale_scostamento < -30) return 'medium';
    return 'low';
  };

  // Tabs per navigazione
  const pendingCount = supervisioni.filter(s => s.stato === 'PENDING' || s.stato === 'PENDING_REVIEW').length;
  const tabs = [
    {
      id: 'pending',
      label: 'Da Supervisionare',
      count: pendingCount,
      icon: '⏳',
      description: 'Anomalie che richiedono decisione manuale'
    },
    {
      id: 'patterns',
      label: 'Pattern ML',
      count: criteri.length,
      icon: '🧠',
      description: 'Pattern appresi dal sistema'
    },
    {
      id: 'storico',
      label: 'Storico',
      count: storico.length,
      icon: '📜',
      description: 'Decisioni precedenti (audit trail)'
    },
    {
      id: 'stats',
      label: 'Analytics',
      count: stats?.approvazioni_totali || 0,
      icon: '📊',
      description: 'Statistiche e metriche ML'
    }
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <Loading text="Caricamento sistema supervisione ML..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header con ritorno ordine */}
      {returnToOrdine && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
                🔗
              </div>
              <div>
                <p className="font-medium text-blue-900">Supervisione da Ordine #{returnToOrdine}</p>
                <p className="text-sm text-blue-700">Dopo l'azione tornerai automaticamente al dettaglio ordine</p>
              </div>
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => onReturnToOrdine?.(returnToOrdine)}
            >
              ← Torna all'Ordine
            </Button>
          </div>
        </div>
      )}

      {/* Stats ML Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              ⏳
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">In Attesa</p>
              <p className="text-xl font-bold text-slate-800">{supervisioni.filter(s => s.stato === 'PENDING' || s.stato === 'PENDING_REVIEW').length}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              🧠
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Pattern ML</p>
              <p className="text-xl font-bold text-slate-800">{stats?.totale_pattern || 0}</p>
              <p className="text-xs text-slate-500">{stats?.pattern_ordinari || 0} automatici</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              ✅
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Approvazioni</p>
              <p className="text-xl font-bold text-slate-800">{stats?.approvazioni_totali || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              🎯
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Efficienza ML</p>
              <p className="text-xl font-bold text-slate-800">
                {stats?.totale_pattern ? Math.round((stats.pattern_ordinari / stats.totale_pattern) * 100) : 0}%
              </p>
              <p className="text-xs text-slate-500">pattern automatici</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200">
        {/* Tabs */}
        <div className="border-b border-slate-200">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                <span className="bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full text-xs">
                  {tab.count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Da Supervisionare */}
        {activeTab === 'pending' && (
          <div>
            {/* Intestazione descrittiva */}
            <div className="px-6 py-4 bg-blue-50 border-b border-blue-200">
              <h3 className="text-sm font-medium text-blue-900 mb-1">Anomalie da Supervisionare</h3>
              <p className="text-xs text-blue-700">
                Queste anomalie richiedono una decisione manuale. Puoi approvare (il pattern viene appreso dal ML),
                rifiutare (reset apprendimento), o navigare all'ordine per verificare i dettagli prima di decidere.
              </p>
            </div>

            {/* v8.0: Toggle vista raggruppata/individuale */}
            <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600">Vista:</span>
                <button
                  onClick={() => setViewMode('grouped')}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    viewMode === 'grouped'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  Per Pattern ({groupedSupervisioni.length})
                </button>
                <button
                  onClick={() => setViewMode('individual')}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    viewMode === 'individual'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  Singole ({supervisioni.filter(s => s.stato === 'PENDING' || s.stato === 'PENDING_REVIEW').length})
                </button>
              </div>
              {viewMode === 'grouped' && (
                <p className="text-xs text-slate-500">
                  Approvando un pattern, risolvi tutte le supervisioni con quel pattern
                </p>
              )}
            </div>

            {/* v8.0: Vista raggruppata per pattern */}
            {viewMode === 'grouped' && (
              <div className="divide-y divide-slate-100">
                {groupedSupervisioni.length === 0 ? (
                  <div className="p-8 text-center">
                    <div className="text-4xl mb-3">🎉</div>
                    <h3 className="text-lg font-medium text-slate-800 mb-2">Nessuna supervisione in attesa</h3>
                    <p className="text-slate-600">Tutte le anomalie sono state gestite o risolte automaticamente dall'ML.</p>
                  </div>
                ) : (
                  groupedSupervisioni.map((group) => {
                    const isProcessing = processingPattern === group.pattern_signature;
                    const tipoLabel = {
                      'espositore': { bg: 'bg-purple-100', text: 'text-purple-700', label: 'ESPOSITORE' },
                      'listino': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'LISTINO' },
                      'lookup': { bg: 'bg-amber-100', text: 'text-amber-700', label: 'LOOKUP' },
                    }[group.tipo_supervisione] || { bg: 'bg-slate-100', text: 'text-slate-700', label: group.tipo_supervisione };
                    const mlProgress = (group.pattern_count || 0) * 20;

                    return (
                      <div
                        key={group.pattern_signature}
                        className={`p-6 ${isProcessing ? 'opacity-50' : ''}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-3 mb-2">
                              <span className={`px-2 py-0.5 text-xs rounded-full ${tipoLabel.bg} ${tipoLabel.text}`}>
                                {tipoLabel.label}
                              </span>
                              <span className="font-medium text-slate-800">{group.codice_anomalia}</span>
                              <VendorBadge vendor={group.vendor} size="xs" />
                              {group.pattern_ordinario && (
                                <span className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded-full">
                                  AUTOMATICO
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-slate-600 mb-2">
                              {group.pattern_descrizione || `Pattern: ${group.pattern_signature?.substring(0, 12)}...`}
                            </p>
                            <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                              <span><strong>{group.total_count}</strong> supervisioni</span>
                              <span><strong>{group.affected_order_ids?.length || 0}</strong> ordini</span>
                              <span className="truncate max-w-md" title={group.affected_orders_preview}>
                                Ordini: {group.affected_orders_preview || 'N/A'}
                              </span>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-3xl font-bold text-slate-800">{group.total_count}</div>
                            <div className="text-xs text-slate-500">supervisioni</div>
                          </div>
                        </div>

                        {/* ML Progress */}
                        <div className="mt-4 flex items-center gap-3">
                          <span className="text-xs text-slate-500">ML:</span>
                          <div className="flex-1 h-2 bg-slate-200 rounded-full max-w-xs">
                            <div
                              className={`h-full rounded-full transition-all ${
                                group.pattern_count >= 5 ? 'bg-emerald-500' : 'bg-orange-400'
                              }`}
                              style={{ width: `${Math.min(mlProgress, 100)}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-600">{group.pattern_count || 0}/5</span>
                        </div>

                        {/* Actions */}
                        <div className="mt-4 flex items-center gap-3 flex-wrap">
                          {/* v9.0: Link al primo ordine per verificare */}
                          {group.affected_order_ids?.length > 0 && onNavigateToOrdine && (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => onNavigateToOrdine(group.affected_order_ids[0])}
                            >
                              Verifica Ordine
                            </Button>
                          )}
                          <Button
                            variant="success"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleApprovaBulk(group.pattern_signature, group.total_count)}
                            disabled={isProcessing}
                          >
                            Approva Tutti ({group.total_count})
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleRifiutaBulk(group.pattern_signature, group.total_count)}
                            disabled={isProcessing}
                          >
                            Rifiuta Tutti
                          </Button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Vista individuale (originale) */}
            {viewMode === 'individual' && (
              <div className="divide-y divide-slate-100">
            {supervisioni.filter(s => s.stato === 'PENDING' || s.stato === 'PENDING_REVIEW').length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-4xl mb-3">🎉</div>
                <h3 className="text-lg font-medium text-slate-800 mb-2">Nessuna supervisione in attesa</h3>
                <p className="text-slate-600">Tutte le anomalie sono state gestite o risolte automaticamente dall'ML.</p>
              </div>
            ) : (
              supervisioni.filter(s => s.stato === 'PENDING_REVIEW' || s.stato === 'PENDING').map((sup) => {
                const urgency = getAnomaliaUrgency(sup);
                const mlProgress = getMLProgress(sup.pattern_approvazioni || sup.count_pattern || 0);
                const isProcessing = processingAction === sup.id_supervisione;
                const isListino = sup.tipo_supervisione === 'listino' || sup.codice_anomalia?.startsWith('LST-');
                const isLookup = sup.tipo_supervisione === 'lookup' || sup.codice_anomalia?.startsWith('LKP-');
                const vendorDisplay = isListino ? (sup.vendor || 'CODIFI') : (sup.vendor || 'ANGELINI');

                return (
                  <div
                    key={`${isListino ? 'lst' : isLookup ? 'lkp' : 'esp'}-${sup.id_supervisione}`}
                    className={`p-6 ${
                      urgency === 'high' ? 'bg-red-50 border-l-4 border-red-500' :
                      urgency === 'medium' ? 'bg-amber-50 border-l-4 border-amber-500' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        {/* Header con titolo e badges */}
                        <div className="flex items-center gap-3 mb-2">
                          <h4 className="font-medium text-slate-800">
                            Ordine #{sup.numero_ordine} - {sup.ragione_sociale}
                          </h4>
                          <VendorBadge vendor={vendorDisplay} size="xs" />
                          {isListino ? (
                            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                              LISTINO
                            </span>
                          ) : isLookup ? (
                            <span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded-full">
                              LOOKUP
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">
                              ESPOSITORE
                            </span>
                          )}
                          <StatusBadge
                            status={urgency === 'high' ? 'error' : urgency === 'medium' ? 'warning' : 'pending'}
                            size="xs"
                          />
                        </div>

                        {/* Info aggiuntive: ID, data, farmacia */}
                        <div className="flex flex-wrap gap-4 text-xs text-slate-500 mb-3">
                          <span>ID: {sup.id_testata}</span>
                          {sup.data_ordine && (
                            <span>Data: {new Date(sup.data_ordine).toLocaleDateString('it-IT')}</span>
                          )}
                          {sup.min_id && <span>MIN: {sup.min_id}</span>}
                          {sup.timestamp_creazione && (
                            <span>Creata: {new Date(sup.timestamp_creazione).toLocaleDateString('it-IT')}</span>
                          )}
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                          {isListino ? (
                            // Listino supervision details
                            <div className="space-y-1">
                              <p className="text-slate-600">
                                <strong>Anomalia:</strong> {sup.codice_anomalia}
                              </p>
                              <p className="text-slate-600">
                                <strong>Codice AIC:</strong> {sup.codice_aic || 'N/A'}
                              </p>
                              <p className="text-slate-600">
                                <strong>Prodotto:</strong> {sup.descrizione_prodotto || 'Non specificato'}
                              </p>
                              {sup.n_riga && (
                                <p className="text-slate-600">
                                  <strong>Riga:</strong> {sup.n_riga}
                                </p>
                              )}
                            </div>
                          ) : isLookup ? (
                            // Lookup supervision details
                            <div className="space-y-1">
                              <p className="text-slate-600">
                                <strong>Anomalia:</strong> {sup.codice_anomalia}
                              </p>
                              <p className="text-slate-600">
                                <strong>Farmacia estratta:</strong> {sup.ragione_sociale || 'N/A'}
                              </p>
                              {sup.piva && (
                                <p className="text-slate-600">
                                  <strong>P.IVA:</strong> {sup.piva}
                                </p>
                              )}
                              {sup.lookup_score !== undefined && (
                                <p className="text-slate-600">
                                  <strong>Score lookup:</strong> {sup.lookup_score}%
                                </p>
                              )}
                            </div>
                          ) : (
                            // Espositore supervision details
                            <div className="space-y-1">
                              <p className="text-slate-600">
                                <strong>Anomalia:</strong> {sup.codice_anomalia}
                              </p>
                              <p className="text-slate-600">
                                <strong>Espositore:</strong> {sup.codice_espositore || sup.espositore_codice}
                              </p>
                              <p className="text-slate-600">
                                <strong>Scostamento:</strong> {sup.percentuale_scostamento}%
                                ({sup.pezzi_trovati} vs {sup.pezzi_attesi} attesi)
                              </p>
                            </div>
                          )}

                          {/* ML Progress nella seconda colonna */}
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">ML:</span>
                            <div className="flex-1 h-2 bg-slate-200 rounded-full max-w-[120px]">
                              <div
                                className={`h-full rounded-full ${
                                  mlProgress >= 100 ? 'bg-emerald-500' : 'bg-orange-400'
                                }`}
                                style={{ width: `${Math.min(mlProgress, 100)}%` }}
                              />
                            </div>
                            <span className="text-xs text-slate-600">
                              {sup.pattern_approvazioni || sup.count_pattern || 0}/5
                            </span>
                          </div>
                        </div>

                        {(sup.descrizione_anomalia || sup.descrizione_espositore) && (
                          <div className="mt-3 p-3 bg-slate-100 rounded-lg border-l-2 border-slate-400">
                            <p className="text-sm text-slate-700 font-medium mb-1">Descrizione:</p>
                            <p className="text-sm text-slate-600">{sup.descrizione_anomalia || sup.descrizione_espositore}</p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Actions - Differenziate per tipo */}
                    <div className="flex items-center gap-3 flex-wrap">
                      {/* v9.0: Pulsante Vai all'Ordine - sempre visibile */}
                      {sup.id_testata && onNavigateToOrdine && (
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => onNavigateToOrdine(sup.id_testata)}
                        >
                          Vai all'Ordine
                        </Button>
                      )}

                      {isListino ? (
                        // Azioni specifiche listino
                        <>
                          <Button
                            variant="primary"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleOpenCorrezione(sup)}
                            disabled={isProcessing}
                          >
                            Correggi Prezzi
                          </Button>

                          <Button
                            variant="warning"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleOpenArchiviazione(sup)}
                            disabled={isProcessing}
                          >
                            Archivia Riga
                          </Button>

                          <Button
                            variant="success"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)}
                            disabled={isProcessing}
                          >
                            Approva
                          </Button>
                        </>
                      ) : isLookup ? (
                        // Azioni lookup
                        <>
                          <Button
                            variant="success"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)}
                            disabled={isProcessing}
                          >
                            Approva Farmacia
                          </Button>

                          <Button
                            variant="danger"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleRifiuta(sup.id_supervisione, sup.pattern_signature)}
                            disabled={isProcessing}
                          >
                            Rifiuta
                          </Button>
                        </>
                      ) : (
                        // Azioni espositore (originali)
                        <>
                          <Button
                            variant="success"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)}
                            disabled={isProcessing}
                          >
                            Approva (+1 ML)
                          </Button>

                          <Button
                            variant="danger"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleRifiuta(sup.id_supervisione, sup.pattern_signature)}
                            disabled={isProcessing}
                          >
                            Rifiuta (Reset ML)
                          </Button>

                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleModifica(sup.id_supervisione, {})}
                            disabled={isProcessing}
                          >
                            Modifica
                          </Button>
                        </>
                      )}

                      {returnToOrdine && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleLasciaSospeso(sup.id_supervisione)}
                          disabled={isProcessing}
                        >
                          Lascia Sospeso
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
          </div>
        )}

        {/* Tab Pattern ML */}
        {activeTab === 'patterns' && (
          <div className="p-6">
            {/* Header esplicativo */}
            <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
              <h3 className="text-lg font-semibold text-indigo-900 mb-2">Pattern Machine Learning</h3>
              <p className="text-sm text-indigo-700 mb-3">
                Il sistema apprende dai tuoi feedback. Ogni volta che approvi un'anomalia, il pattern accumula +1 approvazione.
              </p>
              <div className="flex gap-6 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
                  <span className="text-indigo-800"><strong>AUTOMATICO</strong> (5+ approvazioni): gestisce anomalie simili senza intervento</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-orange-400 rounded-full"></div>
                  <span className="text-indigo-800"><strong>IN APPRENDIMENTO</strong> (&lt;5): richiede ancora supervisione manuale</span>
                </div>
              </div>
            </div>

            {criteri.length === 0 ? (
              <div className="text-center py-12 bg-slate-50 rounded-lg">
                <div className="text-5xl mb-4">🧠</div>
                <h4 className="text-lg font-medium text-slate-700 mb-2">Nessun pattern ancora appreso</h4>
                <p className="text-sm text-slate-500">I pattern vengono creati automaticamente quando approvi anomalie.</p>
                <p className="text-sm text-slate-500 mt-1">Vai in "Da Supervisionare" e approva alcune anomalie per iniziare l'apprendimento.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {criteri.map((criterio) => {
                  const approvazioni = criterio.count_approvazioni || 0;
                  const progress = getMLProgress(approvazioni);
                  const isOrdinario = criterio.is_ordinario || approvazioni >= 5;
                  const isListino = criterio.tipo === 'listino';
                  const isLookup = criterio.tipo === 'lookup';
                  const mancanti = Math.max(0, 5 - approvazioni);

                  return (
                    <div
                      key={criterio.pattern_signature}
                      className={`p-5 border-2 rounded-xl ${
                        isOrdinario
                          ? 'border-emerald-300 bg-gradient-to-r from-emerald-50 to-green-50'
                          : 'border-orange-300 bg-gradient-to-r from-orange-50 to-amber-50'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          {/* Header con badge */}
                          <div className="flex items-center gap-3 mb-3">
                            <span className={`px-3 py-1 text-sm font-bold rounded-lg ${
                              isListino ? 'bg-blue-100 text-blue-800' :
                              isLookup ? 'bg-amber-100 text-amber-800' :
                              'bg-purple-100 text-purple-800'
                            }`}>
                              {isListino ? 'LISTINO' : isLookup ? 'LOOKUP' : 'ESPOSITORE'}
                            </span>
                            <span className="font-semibold text-slate-800">
                              {criterio.codice_anomalia || criterio.pattern_descrizione || 'Pattern'}
                            </span>
                            {isOrdinario ? (
                              <span className="px-3 py-1 text-sm font-bold bg-emerald-200 text-emerald-800 rounded-lg flex items-center gap-1">
                                ✓ AUTOMATICO
                              </span>
                            ) : (
                              <span className="px-3 py-1 text-sm font-medium bg-orange-200 text-orange-800 rounded-lg">
                                IN APPRENDIMENTO
                              </span>
                            )}
                          </div>

                          {/* Descrizione pattern */}
                          {criterio.pattern_descrizione && (
                            <p className="text-sm text-slate-600 mb-3 italic">
                              {criterio.pattern_descrizione}
                            </p>
                          )}

                          {/* Dettagli in griglia */}
                          <div className="grid grid-cols-3 gap-4 text-sm mb-4">
                            <div className="bg-white/60 p-2 rounded-lg">
                              <p className="text-xs text-slate-500 uppercase">Identificatore</p>
                              {isListino ? (
                                <p className="font-mono font-medium text-slate-800">AIC: {criterio.codice_aic || '-'}</p>
                              ) : isLookup ? (
                                <p className="font-mono font-medium text-slate-800">Lookup: {criterio.lookup_type || '-'}</p>
                              ) : (
                                <p className="font-mono font-medium text-slate-800">Esp: {criterio.codice_espositore || '-'}</p>
                              )}
                            </div>
                            <div className="bg-white/60 p-2 rounded-lg">
                              <p className="text-xs text-slate-500 uppercase">Vendor</p>
                              <p className="font-medium text-slate-800">{criterio.vendor || '-'}</p>
                            </div>
                            <div className="bg-white/60 p-2 rounded-lg">
                              <p className="text-xs text-slate-500 uppercase">
                                {isListino ? 'Sconto' : 'Fascia Scostamento'}
                              </p>
                              <p className="font-medium text-slate-800">
                                {criterio.fascia_scostamento || criterio.sconto || '-'}
                              </p>
                            </div>
                          </div>

                          {/* Progress bar prominente */}
                          <div className="bg-white/80 p-3 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium text-slate-700">
                                Approvazioni accumulate
                              </span>
                              <span className={`text-lg font-bold ${isOrdinario ? 'text-emerald-600' : 'text-orange-600'}`}>
                                {approvazioni}/5
                              </span>
                            </div>
                            <div className="h-4 bg-slate-200 rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all duration-500 ${
                                  isOrdinario ? 'bg-emerald-500' : 'bg-orange-400'
                                }`}
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                            {!isOrdinario && (
                              <p className="text-xs text-slate-500 mt-2">
                                Mancano <strong>{mancanti}</strong> approvazioni per diventare automatico
                              </p>
                            )}
                            {isOrdinario && criterio.data_promozione && (
                              <p className="text-xs text-emerald-600 mt-2">
                                Promosso ad automatico il {new Date(criterio.data_promozione).toLocaleDateString('it-IT')}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Azioni */}
                        <div className="ml-6 flex flex-col gap-3">
                          {!isOrdinario && (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handlePromuoviPattern(criterio.pattern_signature)}
                              className="whitespace-nowrap"
                            >
                              ⚡ Forza Automazione
                            </Button>
                          )}
                          {isOrdinario && (
                            <div className="text-center px-3 py-2 bg-emerald-100 rounded-lg">
                              <span className="text-xs text-emerald-700">Gestione automatica attiva</span>
                            </div>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleResetPattern(criterio.pattern_signature)}
                            className="text-red-600 hover:bg-red-50"
                          >
                            Reset Apprendimento
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Tab Storico - v9.0 */}
        {activeTab === 'storico' && (
          <div className="p-6">
            <div className="mb-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">Storico Decisioni</h3>
              <p className="text-slate-600 text-sm">
                Ultime decisioni prese sulle supervisioni. Utile per audit e verifica.
              </p>
            </div>

            {storico.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <div className="text-4xl mb-3">📜</div>
                <p>Nessuna decisione nello storico</p>
                <p className="text-sm mt-1">Le decisioni appariranno qui dopo l'approvazione/rifiuto</p>
              </div>
            ) : (
              <div className="space-y-3">
                {storico.map((item, idx) => (
                  <div
                    key={idx}
                    className={`p-4 border rounded-lg ${
                      item.azione === 'APPROVED' ? 'border-emerald-200 bg-emerald-50' :
                      item.azione === 'REJECTED' ? 'border-red-200 bg-red-50' :
                      'border-slate-200 bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          item.azione === 'APPROVED' ? 'bg-emerald-100 text-emerald-700' :
                          item.azione === 'REJECTED' ? 'bg-red-100 text-red-700' :
                          'bg-slate-100 text-slate-700'
                        }`}>
                          {item.azione === 'APPROVED' ? '✓ Approvato' :
                           item.azione === 'REJECTED' ? '✗ Rifiutato' :
                           item.azione}
                        </span>
                        <span className="text-sm font-medium text-slate-800">
                          Ordine #{item.numero_ordine || item.id_testata}
                        </span>
                        <VendorBadge vendor={item.vendor} size="xs" />
                      </div>
                      <div className="text-right text-xs text-slate-500">
                        <p>{item.operatore}</p>
                        <p>{item.timestamp ? new Date(item.timestamp).toLocaleString('it-IT') : '-'}</p>
                      </div>
                    </div>
                    {item.note && (
                      <p className="mt-2 text-sm text-slate-600 italic">"{item.note}"</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab Analytics */}
        {activeTab === 'stats' && (
          <div className="p-6">
            <div className="text-center py-8 text-slate-500">
              <div className="text-4xl mb-2">📊</div>
              <p>Analytics avanzate in sviluppo...</p>
              <p className="text-sm mt-1">Grafici performance ML, trend approvazioni, efficienza pattern</p>
            </div>
          </div>
        )}
      </div>

      {/* Modali Listino */}
      <CorrezioneLisinoModal
        isOpen={correzioneModal.isOpen}
        onClose={() => setCorrezioneModal({ isOpen: false, supervisione: null })}
        supervisione={correzioneModal.supervisione}
        operatore={operatore}
        onSuccess={handleListinoSuccess}
      />

      <ArchiviazioneListinoModal
        isOpen={archiviazioneModal.isOpen}
        onClose={() => setArchiviazioneModal({ isOpen: false, supervisione: null })}
        supervisione={archiviazioneModal.supervisione}
        operatore={operatore}
        onSuccess={handleListinoSuccess}
      />
    </div>
  );
};

export default SupervisionePage;
