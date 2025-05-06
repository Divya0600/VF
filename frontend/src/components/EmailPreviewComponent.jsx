import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle, Mail } from 'lucide-react';

const EmailPreviewComponent = ({ showModal, template, onClose, onUseTemplate }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emailData, setEmailData] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setEmailData(null);
    
    if (!showModal || !template?.id) return;
    
    // Fetch the email template content
    fetch(`/api/forms/preview-email?templateId=${template.id}&t=${Date.now()}`, {
      method: 'GET',
      cache: 'no-cache',
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to fetch email template: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setEmailData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading email template:", err);
        setError(`Failed to load email template: ${err.message}`);
        setLoading(false);
      });
  }, [template, showModal]);

  if (!showModal) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h3 className="text-xl font-semibold text-gray-800">
            Email Template Preview: {template?.name}
          </h3>
          <button 
            className="p-2 rounded-full hover:bg-gray-100"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="flex-1 p-6 overflow-auto">
          <div className="bg-gray-100 rounded-lg p-4 flex flex-col min-h-[60vh]">
            {loading && (
              <div className="flex items-center justify-center h-full w-full">
                <Loader size={36} className="text-blue-600 animate-spin" />
                <span className="ml-2 text-gray-600">Loading email template...</span>
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
                    // Force re-fetch
                    fetch(`/api/forms/preview-email?templateId=${template.id}&t=${Date.now()}`)
                      .then(response => response.json())
                      .then(data => {
                        setEmailData(data);
                        setLoading(false);
                      })
                      .catch(err => {
                        setError(`Failed to load email template: ${err.message}`);
                        setLoading(false);
                      });
                  }}
                >
                  Try Again
                </button>
              </div>
            )}
            
            {emailData && !loading && !error && (
              <div className="w-full bg-white rounded-lg border border-gray-200 overflow-hidden">
                <div className="bg-blue-50 p-4 border-b border-gray-200">
                  <div className="flex items-center mb-2">
                    <Mail size={20} className="text-blue-500 mr-2" />
                    <h4 className="text-lg font-medium text-gray-800">Subject:</h4>
                  </div>
                  <p className="text-gray-700 ml-7">{emailData.subject}</p>
                </div>
                
                <div className="p-4">
                  <div className="border-b border-gray-200 pb-2 mb-4">
                    <h4 className="text-lg font-medium text-gray-800">Email Body:</h4>
                  </div>
                  
                  {emailData.body.includes('<!DOCTYPE html>') || emailData.body.includes('<html') ? (
                    <iframe 
                      srcDoc={emailData.body}
                      title="Email Preview"
                      className="w-full min-h-[400px] border-0"
                      sandbox="allow-same-origin"
                    />
                  ) : (
                    <pre className="whitespace-pre-wrap bg-gray-50 p-4 rounded text-gray-700">
                      {emailData.body}
                    </pre>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
          <button 
            className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            onClick={onClose}
          >
            Close Preview
          </button>
          <button 
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            onClick={() => {
              onClose();
              onUseTemplate && onUseTemplate(template);
            }}
          >
            Use This Template
          </button>
        </div>
      </div>
    </div>
  );
};

export default EmailPreviewComponent;