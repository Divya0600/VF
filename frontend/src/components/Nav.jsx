// src/components/Nav.jsx
import React from 'react';
import { Settings, HelpCircle, User } from 'lucide-react';

const Nav = ({ onOpenSettings, onOpenHelp, onOpenProfile }) => {
  return (
    <nav className="bg-purple-900 text-white p-4 flex items-center justify-between">
      <div className="flex items-center">
        <h1 className="text-xl font-bold">Anonymate AI</h1>
      </div>
      <div className="flex items-center space-x-4">
        <button onClick={onOpenHelp} className="p-2 hover:bg-purple-800 rounded-full">
          <HelpCircle size={20} />
        </button>
        <button onClick={onOpenSettings} className="p-2 hover:bg-purple-800 rounded-full">
          <Settings size={20} />
        </button>
        <button onClick={onOpenProfile} className="p-2 hover:bg-purple-800 rounded-full">
          <User size={20} />
        </button>
      </div>
    </nav>
  );
};

export default Nav;