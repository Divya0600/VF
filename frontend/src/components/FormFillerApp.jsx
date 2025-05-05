import React, { useState, useEffect, useCallback } from 'react';
import { 
  AlertCircle, ArrowRight, CheckCircle, ChevronDown, ChevronLeft, ChevronRight,
  Download, Eye, File, FileText, Filter, Info, Search, X, Database, 
  Upload, Loader, RefreshCw, List, Grid, ArrowUpDown, Calendar
} from 'lucide-react';

const FormFillerApp = () => {
  // State declarations
  const [step, setStep] = useState(1);
  const [formTypes, setFormTypes] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedFormType, setSelectedFormType] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [csvFile, setCsvFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [formTypeDropdownOpen, setFormTypeDropdownOpen] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('list');
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState('name');
  const [sortDirection, setSortDirection] = useState('asc');
  const [filterOpen, setFilterOpen] = useState(false);
  const [processingResults, setProcessingResults] = useState(null);
  
  const templatesPerPage = 10;

  // Fetch form types and templates from backend
  useEffect(() => {
    const fetchFormTypes = async () => {
      try {
        setLoading(true);
        
        // In a real implementation, this would fetch from an API
        // For now, we'll use mock data
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock response data - this would come from your backend
        const formTypesList = [
          { id: 'all', name: 'All Forms' },
          { id: 'pdf', name: 'PDF Forms' },
          { id: 'tif', name: 'TIF Forms' },
          { id: 'email', name: 'Email Templates' }
        ];
        
        const templatesData = [
          { id: 'form1', name: 'Form Type 1', type: 'pdf', description: 'Contract partner change form', lastModified: '2025-02-10' },
          { id: 'form2', name: 'Vodafone Vollmacht Form', type: 'pdf', description: 'Power of attorney form', lastModified: '2025-03-18' },
          { id: 'form3', name: 'Vodafone Widerrufsformular', type: 'pdf', description: 'Cancellation form', lastModified: '2025-03-15' },
          { id: 'email1', name: 'Email Template 1', type: 'email', description: 'Standard email notification', lastModified: '2025-01-25' }
        ];
        
        setFormTypes(formTypesList);
        setTemplates(templatesData);
        setSelectedFormType('all');
        setLoading(false);
      } catch (err) {
        console.error('Error fetching form types:', err);
        setError('Failed to load form types and templates. Please try again.');
        setLoading(false);
      }
    };
    
    fetchFormTypes();
  }, []);

  // Filter, sort and paginate templates
  const filteredTemplates = templates.filter(template => {
    // Filter by form type
    const typeMatch = selectedFormType === 'all' || template.type === selectedFormType;
    
    // Filter by search query
    const query = searchQuery.toLowerCase();
    const nameMatch = template.name.toLowerCase().includes(query);
    const descriptionMatch = template.description.toLowerCase().includes(query);
    const idMatch = template.id.toLowerCase().includes(query);
    
    return typeMatch && (nameMatch || descriptionMatch || idMatch);
  });
  
  // Sort templates
  const sortedTemplates = [...filteredTemplates].sort((a, b) => {
    let comparison = 0;
    
    if (sortField === 'name') {
      comparison = a.name.localeCompare(b.name);
    } else if (sortField === 'type') {
      comparison = a.type.localeCompare(b.type);
    } else if (sortField === 'lastModified') {
      comparison = new Date(a.lastModified) - new Date(b.lastModified);
    }
    
    return sortDirection === 'asc' ? comparison : -comparison;
  });
  
  // Paginate templates
  const indexOfLastTemplate = currentPage * templatesPerPage;
  const indexOfFirstTemplate = indexOfLastTemplate - templatesPerPage;
  const currentTemplates = sortedTemplates.slice(indexOfFirstTemplate, indexOfLastTemplate);
  const totalPages = Math.ceil(sortedTemplates.length / templatesPerPage);

  // Handle sort toggle
  const toggleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Preview empty form template
  const previewTemplate = (template) => {
    setShowPreviewModal(true);
    setSelectedTemplate(template);
  };

  // Handle file upload
  const handleFileUpload = (event) => {
    setValidationError(null);
    
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        setValidationError('Please upload a valid CSV file');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setValidationError('File size exceeds 5MB limit');
        return;
      }
      
      setCsvFile(file);
      
      // Mock preview data - in a real app, you would parse the CSV here
      setPreviewData({
        headers: ['name', 'vorname', 'strasse', 'hausnummer', 'postleitzahl', 'ort', 'geburtsdatum'],
        rows: [
          ['Fischer', 'Simon', 'Bachstraße', '12', '10315', 'Berlin', '05.07.1985'],
          ['Müller', 'Anna', 'Hauptstr.', '45', '80331', 'München', '12.03.1990']
        ]
      });
    }
  };

  // Drag & drop handlers
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    setValidationError(null);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      
      if (file.type !== 'text/csv' && !file.name.endsWith('.csv')) {
        setValidationError('Please upload a valid CSV file');
        return;
      }
      
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        setValidationError('File size exceeds 5MB limit');
        return;
      }
      
      setCsvFile(file);
      
      // Mock preview data - in a real app, you would parse the CSV here
      setPreviewData({
        headers: ['name', 'vorname', 'strasse', 'hausnummer', 'postleitzahl', 'ort', 'geburtsdatum'],
        rows: [
          ['Fischer', 'Simon', 'Bachstraße', '12', '10315', 'Berlin', '05.07.1985'],
          ['Müller', 'Anna', 'Hauptstr.', '45', '80331', 'München', '12.03.1990']
        ]
      });
    }
  }, []);

  // Process form with backend
  const processForm = () => {
    setStep(3);
    setProcessing(true);
    
    // Simulate processing
    setTimeout(() => {
      setProcessing(false);
      setCompleted(true);
      setProcessingResults({
        batchId: 'batch_' + Date.now(),
        successCount: previewData.rows.length,
        successRate: '100%',
        files: previewData.rows.map((_, i) => ({
          name: `filled_${selectedTemplate.name}_${i+1}.${selectedTemplate.type}`,
          size: '117 KB',
          date: new Date().toLocaleDateString()
        }))
      });
    }, 2000);
  };

  // Download a processed form
  const downloadForm = (fileName) => {
    alert(`Downloading file: ${fileName}`);
    // In a real implementation, this would initiate a download from the backend
  };

  // Download all processed forms as zip
  const downloadAllForms = () => {
    alert(`Downloading all files for batch: ${processingResults.batchId}`);
    // In a real implementation, this would initiate a download from the backend
  };

  const resetForm = () => {
    setStep(1);
    setSelectedTemplate(null);
    setCsvFile(null);
    setCompleted(false);
    setPreviewData(null);
    setValidationError(null);
    setProcessingResults(null);
  };

  // Form Type Dropdown
  const renderFormTypeDropdown = () => (
    <div className="relative">
      <button 
        className="w-full flex items-center justify-between px-4 py-3 bg-white border border-gray-200 rounded-lg shadow-sm hover:border-gray-300 focus:outline-none"
        onClick={() => setFormTypeDropdownOpen(!formTypeDropdownOpen)}
      >
        {selectedFormType ? (
          <div className="flex items-center">
            <span className="ml-1 font-medium capitalize">
              {formTypes.find(type => type.id === selectedFormType)?.name || 'All Forms'}
            </span>
          </div>
        ) : (
          <span className="text-gray-500">Select form type</span>
        )}
        <ChevronDown size={18} className={`text-gray-500 transition-transform duration-200 ${formTypeDropdownOpen ? 'rotate-180' : ''}`} />
      </button>
      
      {formTypeDropdownOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
          {formTypes.map((type) => (
            <div 
              key={type.id}
              className={`flex items-center px-4 py-3 cursor-pointer hover:bg-gray-50 
                ${type.id === selectedFormType ? 'bg-blue-50' : ''}`}
              onClick={() => {
                setSelectedFormType(type.id);
                setFormTypeDropdownOpen(false);
                setCurrentPage(1);
              }}
            >
              <span className={`ml-1 ${type.id === selectedFormType ? 'font-medium text-blue-700' : 'text-gray-700'}`}>
                {type.name}
              </span>
              {type.id === selectedFormType && (
                <CheckCircle size={16} className="ml-auto text-blue-600" />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // Preview Modal
  const renderPreviewModal = () => {
    if (!showPreviewModal) return null;
    
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col">
          <div className="flex items-center justify-between p-6 border-b border-gray-100">
            <h3 className="text-xl font-semibold text-gray-800">
              Form Preview: {selectedTemplate?.name}
            </h3>
            <button 
              className="p-2 rounded-full hover:bg-gray-100"
              onClick={() => setShowPreviewModal(false)}
            >
              <X size={20} />
            </button>
          </div>
          
          <div className="flex-1 p-6 overflow-auto">
            <div className="bg-gray-100 rounded-lg p-8 flex items-center justify-center min-h-[60vh]">
              <div className="text-center">
                <FileText size={64} className="mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-2">Preview of {selectedTemplate?.name}</p>
                <p className="text-sm text-gray-500">{selectedTemplate?.type.toUpperCase()} Template</p>
              </div>
            </div>
          </div>
          
          <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
            <button 
              className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
              onClick={() => setShowPreviewModal(false)}
            >
              Close Preview
            </button>
            {selectedTemplate && (
              <button 
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                onClick={() => {
                  setShowPreviewModal(false);
                  setSelectedTemplate(selectedTemplate);
                  setStep(2);
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

  // STEP 1: Template Selection with Search and List View
  const renderTemplateSelection = () => (
    <div className="w-full">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <h2 className="text-2xl font-semibold text-gray-800">Select Template</h2>
        <div className="flex gap-3">
          {renderFormTypeDropdown()}
          <div className="flex">
            <button 
              className={`p-2 border ${viewMode === 'list' ? 'bg-blue-50 border-blue-200 text-blue-600' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'} rounded-l-lg`}
              onClick={() => setViewMode('list')}
            >
              <List size={20} />
            </button>
            <button 
              className={`p-2 border ${viewMode === 'grid' ? 'bg-blue-50 border-blue-200 text-blue-600' : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50'} rounded-r-lg border-l-0`}
              onClick={() => setViewMode('grid')}
            >
              <Grid size={20} />
            </button>
          </div>
        </div>
      </div>
      
      <div className="mb-6 flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search size={18} className="text-gray-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-10 pr-3 py-3 border border-gray-200 rounded-lg bg-white placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            placeholder="Search templates by name, ID or description..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
          />
        </div>
        <button 
          className="px-4 py-3 border border-gray-200 rounded-lg text-gray-600 flex items-center gap-2 hover:bg-gray-50"
          onClick={() => setFilterOpen(!filterOpen)}
        >
          <Filter size={18} />
          Filter
        </button>
      </div>
      
      {filterOpen && (
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium text-gray-700">Filters</h3>
            <button 
              className="text-gray-500 hover:text-gray-700"
              onClick={() => setFilterOpen(false)}
            >
              <X size={18} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select 
                className="w-full py-2 px-3 border border-gray-200 rounded-lg"
                value={selectedFormType}
                onChange={(e) => setSelectedFormType(e.target.value)}
              >
                {formTypes.map(type => (
                  <option key={type.id} value={type.id}>{type.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Last Modified</label>
              <select className="w-full py-2 px-3 border border-gray-200 rounded-lg">
                <option>Any time</option>
                <option>Last 7 days</option>
                <option>Last 30 days</option>
                <option>Last 90 days</option>
              </select>
            </div>
            <div className="flex items-end">
              <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Apply Filters
              </button>
            </div>
          </div>
        </div>
      )}
      
      {loading ? (
        <div className="py-16 text-center">
          <Loader size={36} className="mx-auto text-blue-600 animate-spin mb-4" />
          <p className="text-gray-600">Loading templates...</p>
        </div>
      ) : error ? (
        <div className="bg-red-50 p-6 rounded-xl border border-red-100 text-center">
          <AlertCircle size={36} className="mx-auto text-red-500 mb-4" />
          <p className="text-red-700 mb-2 font-medium">{error}</p>
          <button 
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 inline-flex items-center gap-1"
            onClick={() => window.location.reload()}
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      ) : filteredTemplates.length === 0 ? (
        <div className="bg-gray-50 p-6 rounded-xl border border-gray-100 text-center">
          <Info size={36} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-700 mb-2 font-medium">No templates found</p>
          <p className="text-gray-500">Try adjusting your search or filters.</p>
        </div>
      ) : viewMode === 'list' ? (
        // List View
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    <span className="flex items-center cursor-pointer" onClick={() => toggleSort('name')}>
                      Template
                      <ArrowUpDown size={14} className="ml-1" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    <span className="flex items-center cursor-pointer" onClick={() => toggleSort('type')}>
                      Type
                      <ArrowUpDown size={14} className="ml-1" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Description</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">
                    <span className="flex items-center cursor-pointer" onClick={() => toggleSort('lastModified')}>
                      Last Modified
                      <ArrowUpDown size={14} className="ml-1" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {currentTemplates.map((template) => (
                  <tr 
                    key={template.id} 
                    className={`hover:bg-gray-50 ${selectedTemplate?.id === template.id ? 'bg-blue-50' : ''}`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <File size={18} className={selectedTemplate?.id === template.id ? 'text-blue-500' : 'text-gray-400'} />
                        <div className="ml-3">
                          <div className={`font-medium ${selectedTemplate?.id === template.id ? 'text-blue-700' : 'text-gray-700'}`}>
                            {template.name}
                          </div>
                          <div className="text-xs text-gray-500">ID: {template.id}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <span className="px-2 py-1 text-xs font-medium rounded-full uppercase bg-gray-100 text-gray-700">
                        {template.type}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-sm text-gray-600 truncate max-w-xs">
                        {template.description}
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500 flex items-center">
                        <Calendar size={14} className="mr-1" />
                        {template.lastModified}
                      </div>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-2">
                        <button 
                          className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded"
                          onClick={(e) => {
                            e.stopPropagation();
                            previewTemplate(template);
                          }}
                        >
                          <Eye size={16} />
                        </button>
                        <button 
                          className="p-1.5 text-gray-500 hover:text-green-600 hover:bg-green-50 rounded"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedTemplate(template);
                            setStep(2);
                          }}
                        >
                          <ArrowRight size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        // Grid View
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          {currentTemplates.map((template) => (
            <div
              key={template.id}
              className={`p-5 rounded-xl transition-all cursor-pointer bg-white border-2 ${
                selectedTemplate?.id === template.id 
                  ? 'border-blue-500 shadow-md' 
                  : 'border-gray-100 shadow-sm hover:border-blue-200 hover:shadow'
              }`}
              onClick={() => setSelectedTemplate(template)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                  <div className={`p-2 rounded-lg ${
                    selectedTemplate?.id === template.id ? 'bg-blue-100' : 'bg-gray-100'
                  }`}>
                    <File size={20} className={
                      selectedTemplate?.id === template.id ? 'text-blue-600' : 'text-gray-500'
                    } />
                  </div>
                  <div className="ml-3">
                    <h3 className={`font-medium ${
                      selectedTemplate?.id === template.id ? 'text-blue-700' : 'text-gray-700'
                    }`}>
                      {template.name}
                    </h3>
                    <p className="text-xs text-gray-500">ID: {template.id}</p>
                  </div>
                </div>
                {selectedTemplate?.id === template.id && (
                  <CheckCircle className="text-blue-500" size={22} />
                )}
              </div>
              <p className="text-gray-600 text-sm line-clamp-2">{template.description}</p>
              
              <div className="mt-4 pt-4 border-t border-gray-100">
                <div className="flex justify-between items-center">
                  <div className="flex items-center text-xs">
                    <span className="px-2 py-1 text-xs font-medium rounded-full uppercase bg-gray-100 text-gray-700 mr-2">
                      {template.type}
                    </span>
                    <span className="text-gray-500 flex items-center">
                      <Calendar size={12} className="mr-1" />
                      {template.lastModified}
                    </span>
                  </div>
                  <div className="flex space-x-2">
                    <button 
                      className={`p-2 rounded-lg text-sm transition-colors ${
                        selectedTemplate?.id === template.id 
                          ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                          : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                      }`}
                      onClick={(e) => {
                        e.stopPropagation();
                        previewTemplate(template);
                      }}
                    >
                      <Eye size={16} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Pagination */}
      {filteredTemplates.length > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            Showing {indexOfFirstTemplate + 1} to {Math.min(indexOfLastTemplate, filteredTemplates.length)} of {filteredTemplates.length} templates
          </div>
          <div className="flex items-center space-x-2">
            <button 
              className="p-2 border border-gray-200 rounded text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            >
              <ChevronLeft size={18} />
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              // Logic to show pages around current page
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              
              return (
                <button
                  key={pageNum}
                  className={`w-10 h-10 flex items-center justify-center rounded ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white'
                      : 'border border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                  onClick={() => setCurrentPage(pageNum)}
                >
                  {pageNum}
                </button>
              );
            })}
            <button 
              className="p-2 border border-gray-200 rounded text-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}
      
      <div className="mt-8 flex justify-end">
        <button
          className="px-6 py-3 bg-blue-600 text-white rounded-lg flex items-center gap-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors hover:bg-blue-700"
          disabled={!selectedTemplate || loading}
          onClick={() => setStep(2)}
        >
          Continue <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );

  // STEP 2: CSV Upload
  const renderCsvUpload = () => (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-6 text-gray-800">Data Upload</h2>
      
      {!csvFile ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-100">
            <div className="flex items-center">
              <div className="w-10 h-10 rounded-lg bg-violet-100 flex items-center justify-center text-violet-600 mr-4">
                <Database size={20} />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Upload Data File</h3>
                <p className="text-sm text-gray-500 mt-1">Upload a CSV file with your form data</p>
              </div>
            </div>
          </div>
          
          <div 
            className={`p-12 border-2 border-dashed m-6 rounded-xl text-center cursor-pointer transition-all
              ${dragActive 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-200 hover:border-blue-300'}
              ${validationError ? 'border-red-300' : ''}`}
            onClick={() => document.getElementById('csv-upload').click()}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              id="csv-upload"
              className="hidden"
              accept=".csv"
              onChange={handleFileUpload}
            />
            <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4
              ${validationError ? 'bg-red-50 text-red-500' : 'bg-blue-50 text-blue-500'}`}>
              {validationError ? <AlertCircle size={28} /> : <Upload size={28} />}
            </div>
            
            {validationError ? (
              <div>
                <p className="text-lg font-medium text-red-600 mb-2">Upload Error</p>
                <p className="text-sm text-red-500 max-w-md mx-auto mb-4">{validationError}</p>
                <button className="px-5 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors inline-flex items-center gap-2">
                  <Upload size={16} />
                  Try Again
                </button>
              </div>
            ) : (
              <div>
                <p className="text-lg font-medium text-gray-700 mb-2">Upload CSV File</p>
                <p className="text-sm text-gray-500 max-w-md mx-auto">
                  Drag and drop your CSV file here, or click to browse your files
                </p>
                <div className="mt-6">
                  <button className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2">
                    <Upload size={16} />
                    Browse Files
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-600 mr-4">
                  <CheckCircle size={20} />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">File Uploaded</h3>
                  <p className="text-sm text-gray-500 mt-1">Your file has been uploaded successfully</p>
                </div>
              </div>
              <button 
                className="text-gray-400 hover:text-gray-600"
                onClick={() => {
                  setCsvFile(null);
                  setPreviewData(null);
                }}
              >
                <X size={20} />
              </button>
            </div>
          </div>
          
          <div className="p-6">
            <div className="flex items-center justify-between bg-green-50 p-4 rounded-lg border border-green-100">
              <div className="flex items-center">
                <FileText className="text-green-600 mr-3" size={24} />
                <div>
                  <p className="font-medium text-gray-800">{csvFile.name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {(csvFile.size / 1024).toFixed(2)} KB • CSV • {previewData?.rows.length} records
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="p-2 text-gray-500 hover:text-gray-700 bg-white rounded border border-gray-200">
                  <Info size={18} />
                </button>
                <button 
                  className="p-2 text-red-500 hover:text-red-700 bg-white rounded border border-gray-200"
                  onClick={() => {
                    setCsvFile(null);
                    setPreviewData(null);
                  }}
                >
                  <X size={18} />
                </button>
              </div>
            </div>
            
            {previewData && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="font-medium text-gray-800">Data Preview</h4>
                  <div className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600">
                    Showing {Math.min(5, previewData.rows.length)} of {previewData.rows.length} rows
                  </div>
                </div>
                
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        {previewData.headers.map((header, idx) => (
                          <th 
                            key={idx}
                            className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                          >
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {previewData.rows.slice(0, 5).map((row, rowIdx) => (
                        <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          {row.map((cell, cellIdx) => (
                            <td 
                              key={cellIdx}
                              className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap"
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div className="mt-8 flex justify-between">
        <button
          className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
          onClick={() => setStep(1)}
        >
          Back
        </button>
        <button
          className="px-6 py-3 bg-blue-600 text-white rounded-lg flex items-center gap-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors hover:bg-blue-700"
          disabled={!csvFile}
          onClick={processForm}
        >
          Process Forms <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );

  // STEP 3: Results
  const renderResults = () => (
    <div className="w-full">
      <h2 className="text-2xl font-semibold mb-6 text-gray-800">Results</h2>
      
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {processing ? (
          <div className="py-16 px-6 text-center">
            <div className="w-20 h-20 border-4 border-t-blue-600 border-blue-100 rounded-full animate-spin mx-auto mb-6"></div>
            <p className="text-xl font-medium text-gray-800 mb-2">Processing Forms</p>
            <p className="text-gray-500">
              Filling {previewData?.rows.length} forms with your data...
            </p>
            
            {/* Progress bar */}
            <div className="max-w-md mx-auto mt-8">
              <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-blue-600 rounded-full w-1/2 animate-pulse"></div>
              </div>
              <p className="text-right text-sm text-gray-500 mt-2">50% Complete</p>
            </div>
            
            <div className="max-w-md mx-auto mt-8 bg-blue-50 p-4 rounded-lg border border-blue-100">
              <div className="flex items-center">
                <Info size={20} className="text-blue-500 mr-3" />
                <p className="text-sm text-blue-700">This process may take a few moments depending on the number of forms</p>
              </div>
            </div>
          </div>
        ) : completed ? (
          <div>
            <div className="border-b border-gray-100 px-6 py-5">
              <div className="flex items-center">
                <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center text-green-600 mr-4">
                  <CheckCircle size={20} />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900">Processing Complete</h3>
                  <p className="text-sm text-gray-500 mt-1">All forms have been processed successfully</p>
                </div>
              </div>
            </div>
            
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-green-50 rounded-xl p-5 border border-green-100">
                  <h4 className="text-green-700 font-medium mb-3 flex items-center">
                    <CheckCircle size={18} className="mr-2" /> Success Rate
                  </h4>
                  <div className="text-3xl font-bold text-gray-800">
                    {processingResults?.successRate || '100%'}
                  </div>
                  <p className="text-gray-500 text-sm mt-1">
                    {processingResults?.successCount || previewData?.rows.length} of {previewData?.rows.length} records processed
                  </p>
                </div>
                
                <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
                  <h4 className="text-blue-700 font-medium mb-3 flex items-center">
                    <FileText size={18} className="mr-2" /> Forms Created
                  </h4>
                  <div className="text-3xl font-bold text-gray-800">
                    {processingResults?.successCount || previewData?.rows.length}
                  </div>
                  <p className="text-gray-500 text-sm mt-1">
                    {selectedTemplate?.type.toUpperCase()} documents
                  </p>
                </div>
                
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                  <h4 className="text-gray-700 font-medium mb-3 flex items-center">
                    <Database size={18} className="mr-2" /> Data Records
                  </h4>
                  <div className="text-3xl font-bold text-gray-800">{previewData?.rows.length}</div>
                  <p className="text-gray-500 text-sm mt-1">From {csvFile?.name}</p>
                </div>
              </div>
              
              <h4 className="font-medium text-gray-800 mb-4">Generated Files</h4>
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-4 px-2">
                  <div className="text-sm text-gray-600">Filename</div>
                  <div className="flex space-x-8">
                    <div className="text-sm text-gray-600 w-20 text-center">Size</div>
                    <div className="text-sm text-gray-600 w-20">Actions</div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  {(processingResults?.files || [...Array(previewData?.rows.length)].map((_, i) => ({
                    name: `filled_${selectedTemplate?.name}_${i+1}.${selectedTemplate?.type}`,
                    size: '117 KB',
                    date: new Date().toLocaleDateString()
                  }))).map((file, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-100">
                      <div className="flex items-center">
                        <FileText className="text-blue-500 mr-3" size={20} />
                        <div>
                          <p className="font-medium text-gray-800">{file.name}</p>
                          <p className="text-xs text-gray-500">Created: {file.date}</p>
                        </div>
                      </div>
                      <div className="flex space-x-8 items-center">
                        <div className="text-sm text-gray-600 w-20 text-center">{file.size}</div>
                        <div className="w-20">
                          <button 
                            className="p-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors"
                            onClick={() => downloadForm(file.name)}
                          >
                            <Download size={18} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="mt-4 text-center">
                  <button 
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors inline-flex items-center gap-2"
                    onClick={downloadAllForms}
                  >
                    <Download size={16} /> Download All Files
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
      
      <div className="mt-8 flex justify-center">
        <button
          className="px-6 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
          onClick={resetForm}
        >
          Start New Batch
        </button>
      </div>
    </div>
  );

  // Error component
  const renderError = () => (
    <div className="bg-red-50 p-6 rounded-xl border border-red-100 text-center">
      <AlertCircle size={36} className="mx-auto text-red-500 mb-4" />
      <p className="text-red-700 mb-4 font-medium">{error}</p>
      <button 
        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 inline-flex items-center gap-1"
        onClick={() => window.location.reload()}
      >
        <RefreshCw size={16} /> Retry
      </button>
    </div>
  );

  // Progress Steps
  const renderProgressSteps = () => (
    <div className="mb-8">
      <div className="max-w-lg mx-auto">
        {/* Progress bar */}
        <div className="relative pt-1 mb-2">
          <div className="flex h-2 overflow-hidden rounded-full bg-gray-200">
            <div
              className="flex flex-col justify-center rounded-full overflow-hidden bg-blue-600 shadow-md transition-all duration-500 ease-out"
              style={{ width: step === 1 ? '33%' : step === 2 ? '66%' : '100%' }}
            ></div>
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          {[
            { number: 1, label: 'Select Template' },
            { number: 2, label: 'Upload Data' }, 
            { number: 3, label: 'Results' }
          ].map((stepItem) => (
            <div key={stepItem.number} className="flex flex-col items-center">
              <div 
                className={`w-10 h-10 rounded-full flex items-center justify-center font-medium transition-colors
                  ${step >= stepItem.number 
                    ? 'bg-blue-600 text-white shadow-md' 
                    : 'bg-gray-100 text-gray-400 border border-gray-200'}`}
              >
                {step > stepItem.number ? <CheckCircle size={18} /> : stepItem.number}
              </div>
              <div className={`text-sm mt-2 ${step >= stepItem.number ? 'text-blue-600 font-medium' : 'text-gray-500'}`}>
                {stepItem.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // Main App Render
  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">PDF Form Filler</h1>
            <div className="flex space-x-4">
              <button className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50 flex items-center gap-2">
                <Info size={18} /> Help
              </button>
            </div>
          </div>
        </header>
        
        {error ? renderError() : (
          <>
            {renderProgressSteps()}
            
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 mb-8">
              {step === 1 && renderTemplateSelection()}
              {step === 2 && renderCsvUpload()}
              {step === 3 && renderResults()}
            </div>
          </>
        )}
      </div>
      
      {renderPreviewModal()}
    </div>
  );
};

export default FormFillerApp;