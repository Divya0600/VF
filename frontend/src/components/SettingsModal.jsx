// src/components/SettingsModal.jsx
import React, { useState, useEffect } from 'react';
import { X, Folder, Save } from 'lucide-react';

const SettingsModal = ({ onClose }) => {
  const [outputDir, setOutputDir] = useState("");
  
  // Load saved settings on mount
  useEffect(() => {
    const savedOutputDir = localStorage.getItem('outputDirectory') || "%APPDATA%\\Anonymate\\output";
    setOutputDir(savedOutputDir);
  }, []);
  
  const handleFolderSelect = () => {
    // Simple input field approach, no dialog
    // Will be replaced with Electron dialog in desktop version
  };
  
  const saveSettings = () => {
    // Save to localStorage for persistence
    localStorage.setItem('outputDirectory', outputDir);
    onClose();
  };
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Settings</h2>
          <button className="p-2 rounded-full hover:bg-gray-100" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Output Directory
            </label>
            <div className="flex">
              <input
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-600"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
              />
            </div>
          </div>
        </div>
        
        <div className="mt-6 flex justify-end">
          <button
            className="mr-3 px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="px-4 py-2 bg-purple-600 text-white rounded-lg flex items-center hover:bg-purple-700"
            onClick={saveSettings}
          >
            <Save size={18} className="mr-1" />
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsModal;