import React, { useState, useEffect } from 'react';
import { X, Loader, AlertCircle, Mail, FileText, Calendar, User } from 'lucide-react';

const EmailPreviewComponent = ({ 
  showModal, 
  template, 
  isProcessed = false, 
  processedEmailInfo = null, 
  onClose, 
  onUseTemplate 
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [emailData, setEmailData] = useState(null);

  useEffect(() => {
    // Reset state when modal is opened/closed
    if (!showModal) {
      return;
    }
    
    setLoading(true);
    setError(null);
    setEmailData(null);
    
    // Determine which endpoint to use
    let url;
    if (isProcessed && processedEmailInfo) {
      // For processed emails
      url = `/api/forms/preview-processed-email?file=${encodeURIComponent(processedEmailInfo.name)}&batchId=${processedEmailInfo.batchId}&t=${Date.now()}`;
    } else if (template?.id) {
      // For template previews
      url = `/api/forms/preview-email?templateId=${template.id}&t=${Date.now()}`;
    } else {
      setError('Missing required information for preview');
      setLoading(false);
      return;
    }
    
    // Fetch the email content
    fetch(url, {
      method: 'GET',
      cache: 'no-cache',
    })
      .then(response => {
        if (!response.ok) {
          if (response.headers.get('content-type')?.includes('application/json')) {
            return response.json().then(data => {
              throw new Error(data.error || `Server error: ${response.status}`);
            });
          }
          throw new Error(`Server error: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        setEmailData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading email:", err);
        setError(`Failed to load email: ${err.message}`);
        setLoading(false);
      });
  }, [template, processedEmailInfo, showModal, isProcessed]);

  if (!showModal) return null;

  // Determine title based on what we're previewing
  const title = isProcessed 
    ? `Processed Email Preview: ${processedEmailInfo?.name}` 
    : `Email Template Preview: ${template?.name}`;

  // Fallback content if we can't load the actual content
  const renderFallbackContent = () => (
    <div className="w-full bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="bg-blue-50 p-4 border-b border-gray-200">
        <div className="flex items-center mb-2">
          <Mail size={20} className="text-blue-500 mr-2" />
          <h4 className="text-lg font-medium text-gray-800">Email Preview</h4>
        </div>
        <p className="text-gray-700 ml-7">
          {isProcessed ? processedEmailInfo?.name : template?.name}
        </p>
      </div>
      
      <div className="p-4">
        <div className="border-b border-gray-200 pb-2 mb-4">
          <h4 className="text-lg font-medium text-gray-800">Email Content:</h4>
        </div>
        
        <div className="p-8 text-center bg-gray-50 rounded-lg">
          <Mail size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600 mb-2">
            {isProcessed 
              ? "This email file can't be displayed." 
              : "This email template can't be displayed."}
          </p>
          <p className="text-gray-500 text-sm">
            You can download the file to view its contents.
          </p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h3 className="text-xl font-semibold text-gray-800">
            {title}
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
              <div className="flex flex-col items-center justify-center h-full w-full">
                <Loader size={36} className="text-blue-600 animate-spin mb-4" />
                <span className="text-gray-600">Loading email content...</span>
              </div>
            )}
            
            {error && (
              <div className="bg-red-50 p-4 rounded-lg border border-red-100 text-center w-full">
                <AlertCircle size={36} className="mx-auto text-red-500 mb-4" />
                <p className="text-red-700">{error}</p>
                
                <div className="mt-4 flex justify-center gap-2">
                  <button 
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
                    onClick={() => {
                      // Switch to fallback display
                      setError(null);
                    }}
                  >
                    Show Basic Info
                  </button>
                  
                  <button 
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                    onClick={() => {
                      // Retry loading
                      setLoading(true);
                      setError(null);
                      
                      let refreshUrl;
                      if (isProcessed && processedEmailInfo) {
                        refreshUrl = `/api/forms/preview-processed-email?file=${encodeURIComponent(processedEmailInfo.name)}&batchId=${processedEmailInfo.batchId}&t=${Date.now()}`;
                      } else if (template?.id) {
                        refreshUrl = `/api/forms/preview-email?templateId=${template.id}&t=${Date.now()}`;
                      }
                      
                      if (refreshUrl) {
                        fetch(refreshUrl, { method: 'GET', cache: 'no-cache' })
                          .then(response => response.json())
                          .then(data => {
                            setEmailData(data);
                            setLoading(false);
                          })
                          .catch(err => {
                            setError(`Failed to load email: ${err.message}`);
                            setLoading(false);
                          });
                      }
                    }}
                  >
                    Try Again
                  </button>
                </div>
              </div>
            )}
            
            {!loading && !error ? (emailData ? (
              <div className="w-full bg-white rounded-lg border border-gray-200 overflow-hidden">
                {/* Email header section with metadata */}
                <div className="bg-blue-50 p-4 border-b border-gray-200">
                  <div className="mb-3">
                    <div className="flex items-center mb-2">
                      <Mail size={18} className="text-blue-500 mr-2" />
                      <h4 className="text-lg font-medium text-gray-800">Subject:</h4>
                    </div>
                    <p className="text-gray-700 ml-7">{emailData.subject || "(No Subject)"}</p>
                  </div>
                  
                  {emailData.from && (
                    <div className="mb-2">
                      <div className="flex items-center mb-1">
                        <User size={16} className="text-gray-500 mr-2" />
                        <h5 className="text-sm font-medium text-gray-700">From:</h5>
                      </div>
                      <p className="text-sm text-gray-600 ml-7">{emailData.from}</p>
                    </div>
                  )}
                  
                  {emailData.to && (
                    <div className="mb-2">
                      <div className="flex items-center mb-1">
                        <User size={16} className="text-gray-500 mr-2" />
                        <h5 className="text-sm font-medium text-gray-700">To:</h5>
                      </div>
                      <p className="text-sm text-gray-600 ml-7">{emailData.to}</p>
                    </div>
                  )}
                  
                  {emailData.date && (
                    <div className="mb-2">
                      <div className="flex items-center mb-1">
                        <Calendar size={16} className="text-gray-500 mr-2" />
                        <h5 className="text-sm font-medium text-gray-700">Date:</h5>
                      </div>
                      <p className="text-sm text-gray-600 ml-7">{emailData.date}</p>
                    </div>
                  )}
                </div>
                
                {/* Email body section */}
                <div className="p-4">
                  <div className="border-b border-gray-200 pb-2 mb-4">
                    <h4 className="text-lg font-medium text-gray-800">Email Body:</h4>
                  </div>
                  
                  {emailData.body ? (
                    emailData.isHtml || emailData.body.includes('<!DOCTYPE html>') || emailData.body.includes('<html') ? (
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
                    )
                  ) : (
                    <div className="p-4 bg-gray-50 rounded text-center text-gray-500">
                      No body content available
                    </div>
                  )}
                </div>
                
                {/* Show attachments if available */}
                {emailData.attachments && emailData.attachments.length > 0 && (
                  <div className="border-t border-gray-200 p-4">
                    <h4 className="text-lg font-medium text-gray-800 mb-3">Attachments:</h4>
                    <div className="space-y-2">
                      {emailData.attachments.map((attachment, index) => (
                        <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded border border-gray-200">
                          <div className="flex items-center">
                            <div className="bg-blue-100 p-2 rounded text-blue-600 mr-3">
                              <FileText size={16} />
                            </div>
                            <span className="text-sm text-gray-700">{attachment.name}</span>
                          </div>
                          <span className="text-xs text-gray-500">{attachment.size}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : renderFallbackContent()) : null}
          </div>
        </div>
        
        <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
          <button 
            className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            onClick={onClose}
          >
            Close Preview
          </button>
          
          {isProcessed && (
            <button 
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-flex items-center gap-2"
              onClick={() => {
                if (processedEmailInfo?.batchId) {
                  // Create a download link
                  const url = `/api/forms/download?file=${encodeURIComponent(processedEmailInfo.name)}&batchId=${processedEmailInfo.batchId}&t=${Date.now()}`;
                  window.open(url, '_blank');
                }
              }}
            >
              <FileText size={16} /> Download Email
            </button>
          )}
          
          {!isProcessed && template && (
            <button 
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              onClick={() => {
                onClose();
                onUseTemplate && onUseTemplate(template);
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

export default EmailPreviewComponent;