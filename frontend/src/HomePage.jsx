// src/HomePage.jsx
import React, { useState } from 'react';
import Nav from './components/Nav';
import FormFillerApp from './components/FormFillerApp';
import SettingsModal from './components/SettingsModal';
import ProfileModal from './components/ProfileModal';

const HomePage = () => {
  const [showSettings, setShowSettings] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showProfile, setShowProfile] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Nav 
        onOpenSettings={() => setShowSettings(true)}
        onOpenHelp={() => setShowHelp(true)}
        onOpenProfile={() => setShowProfile(true)}
      />
      
      <main className="flex-1 p-4">
        <FormFillerApp />
      </main>

      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
      
      {showProfile && (
        <ProfileModal onClose={() => setShowProfile(false)} />
      )}
      
      {showHelp && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold mb-4">Help & Documentation</h2>
            <p className="mb-4">
              Anonymate AI helps you fill forms with data from CSV files.
            </p>
            <ul className="list-disc pl-5 mb-4">
              <li>Select a template</li>
              <li>Upload your CSV data</li>
              <li>Generate filled forms</li>
            </ul>
            <button
              className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              onClick={() => setShowHelp(false)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default HomePage;