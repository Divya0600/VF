import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle, FileText } from 'lucide-react';
import './PdfViewer.css';

const PdfPreviewComponent = ({ showModal, template, onClose, onUseTemplate }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pdfData, setPdfData] = useState(null);

  useEffect(() => {
    // Reset states when template changes
    setLoading(true);
    setError(null);
    setPdfData(null);
    
    if (!template?.id || !showModal) return;

    // Directly fetch the PDF file as blob
    fetch(`/api/forms/preview?formType=${template.id}&raw=true`, {
      method: 'GET',
      cache: 'no-cache', // Important: prevents caching
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to fetch PDF: ${response.status} ${response.statusText}`);
        }
        return response.blob();
      })
      .then(blob => {
        // Create a blob URL for the PDF
        const pdfBlobUrl = URL.createObjectURL(blob);
        setPdfData(pdfBlobUrl);
        setLoading(false);
        console.log("PDF loaded successfully as blob URL");
      })
      .catch(err => {
        console.error("Error loading PDF:", err);
        setError(`Failed to load PDF: ${err.message}`);
        setLoading(false);
      });
      
    // Cleanup function to revoke the blob URL
    return () => {
      if (pdfData) {
        URL.revokeObjectURL(pdfData);
      }
    };
  }, [template, showModal]);

  if (!showModal) return null;

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
          {template?.type === 'pdf' ? (
            <div className="bg-gray-100 rounded-lg p-4 flex flex-col items-center min-h-[60vh]">
              {loading && (
                <div className="flex items-center justify-center h-full w-full">
                  <Loader size={36} className="text-blue-600 animate-spin" />
                  <span className="ml-2 text-gray-600">Loading PDF...</span>
                </div>
              )}
              
              {error && (
                <div className="bg-red-50 p-4 rounded-lg border border-red-100 text-center w-full">
                  <AlertCircle size={36} className="mx-auto text-red-500 mb-4" />
                  <p className="text-red-700">{error}</p>
                  <button 
                    className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    onClick={() => {
                      setLoading(true);
                      setError(null);
                      // Force re-fetch the PDF
                      fetch(`/api/forms/preview?formType=${template.id}&raw=true&t=${Date.now()}`, {
                        method: 'GET',
                        cache: 'no-cache',
                      })
                        .then(response => response.blob())
                        .then(blob => {
                          const pdfBlobUrl = URL.createObjectURL(blob);
                          setPdfData(pdfBlobUrl);
                          setLoading(false);
                        })
                        .catch(err => {
                          setError(`Failed to load PDF: ${err.message}`);
                          setLoading(false);
                        });
                    }}
                  >
                    Try Again
                  </button>
                </div>
              )}
              
              {pdfData && !loading && !error && (
                <object
                  data={pdfData}
                  type="application/pdf"
                  className="w-full h-[70vh] border border-gray-200 rounded"
                >
                  <div className="flex flex-col items-center justify-center h-full bg-gray-50">
                    <p className="text-red-500">Unable to display PDF. Your browser might not support PDF viewing.</p>
                    <a 
                      href={pdfData} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    >
                      Download PDF
                    </a>
                  </div>
                </object>
              )}
            </div>
          ) : (
            <div className="bg-gray-100 rounded-lg p-8 flex items-center justify-center min-h-[60vh]">
              <div className="text-center">
                <FileText size={64} className="mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Preview not available for {template?.name}</p>
                <p className="text-sm text-gray-500">{template?.type?.toUpperCase()} Template</p>
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