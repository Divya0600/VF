// src/components/ProfileModal.jsx
import React from 'react';
import { X, User } from 'lucide-react';

const ProfileModal = ({ onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Profile</h2>
          <button 
            className="p-2 rounded-full hover:bg-gray-100"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="flex flex-col items-center mb-6">
          <div className="w-20 h-20 bg-purple-100 rounded-full flex items-center justify-center mb-3">
            <User size={36} className="text-purple-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-800">Local User</h3>
          <p className="text-sm text-gray-500">Anonymate Desktop Edition</p>
        </div>
        
        <div className="bg-gray-50 p-4 rounded-lg mb-6">
          <h4 className="text-sm font-medium text-gray-700 mb-2">License Information</h4>
          <p className="text-sm text-gray-600">Desktop Edition</p>
          <p className="text-sm text-gray-600">Version 1.0.0</p>
        </div>
        
        <div className="text-center">
          <button
            className="px-4 py-2 border border-gray-300 text-gray-600 rounded-lg hover:bg-gray-50"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProfileModal;