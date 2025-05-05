import React, { useState } from 'react';
import { X, ChevronLeft, ChevronRight, Loader, AlertCircle, FileText } from 'lucide-react';
import './PdfViewer.css';

// A simple PDF preview component that uses an iframe to display PDFs
// This avoids the complexities of setting up pdf.js workers
const PdfPreviewComponent = ({ showModal, template, onClose, onUseTemplate }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  if (!showModal) return null;

  // Determine if we have a PDF to show
  const isPdfTemplate = template?.type === 'pdf';
  const pdfUrl = isPdfTemplate ? `/api/forms/preview?formType=${template.id}` : null;

  // Handle iframe load events
  const handleIframeLoad = () => {
    setLoading(false);
  };

  const handleIframeError = () => {
    setError('Failed to load PDF. Please try again.');
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h3 className="text-xl font-semibold text-gray-800">
            Form Preview: {template?.name}
          </h3>
          <button 
            className="p-2 rounded-full hover:bg-gray-100"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="flex-1 p-6 overflow-auto">
          {isPdfTemplate && pdfUrl ? (
            <div className="bg-gray-100 rounded-lg p-4 flex flex-col items-center min-h-[60vh]">
              {loading && (
                <div className="flex items-center justify-center h-32">
                  <Loader size={36} className="text-blue-600 animate-spin" />
                  <span className="ml-2 text-gray-600">Loading PDF...</span>
                </div>
              )}
              
              {error && (
                <div className="bg-red-50 p-4 rounded-lg border border-red-100 text-center w-full">
                  <AlertCircle size={36} className="mx-auto text-red-500 mb-4" />
                  <p className="text-red-700">{error}</p>
                </div>
              )}
              
              <iframe
                src={pdfUrl}
                className={`w-full ${loading ? 'hidden' : 'block'}`}
                style={{ height: '70vh' }}
                title={`Preview of ${template?.name}`}
                onLoad={handleIframeLoad}
                onError={handleIframeError}
              />
            </div>
          ) : (
            <div className="bg-gray-100 rounded-lg p-8 flex items-center justify-center min-h-[60vh]">
              <div className="text-center">
                <FileText size={64} className="mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Preview not available for {template?.name}</p>
                <p className="text-sm text-gray-500">{template?.type.toUpperCase()} Template</p>
              </div>
            </div>
          )}
        </div>
        
        <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
          <button 
            className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            onClick={onClose}
          >
            Close Preview
          </button>
          {template && (
            <button 
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              onClick={() => {
                onClose();
                onUseTemplate(template);
              }}
            >
              Use This Template
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PdfPreviewComponent;