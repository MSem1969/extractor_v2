// =============================================================================
// TO_EXTRACTOR v7.0 - PDF MODAL COMPONENT
// =============================================================================

import React from 'react';

export default function PdfModal({ pdfFile, onClose }) {
  if (!pdfFile) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg w-full max-w-5xl h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">{pdfFile}</h3>
          <div className="flex gap-2">
            <a
              href={`/api/v1/upload/pdf/${encodeURIComponent(pdfFile)}`}
              download
              className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
            >
              Scarica
            </a>
            <button
              onClick={onClose}
              className="px-3 py-1 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 text-sm"
            >
              X Chiudi
            </button>
          </div>
        </div>
        <div className="flex-1 p-2">
          <iframe
            src={`/api/v1/upload/pdf/${encodeURIComponent(pdfFile)}`}
            className="w-full h-full rounded border"
            title="PDF Ordine"
          />
        </div>
      </div>
    </div>
  );
}
