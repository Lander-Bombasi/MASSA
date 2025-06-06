import React from 'react';
import './Numpad.css';

const Numpad = ({ 
  onClick, 
  onClear, 
  onDetect, 
  onRecord, 
  onTare,
  onTransaction,
  disabled,
  mode
}) => {
  const buttons = [
    '1', '2', '3',
    '4', '5', '6',
    '7', '8', '9',
    '.', '0', 'Clear'
  ];

  return (
    <div className="numpad-container">
      <div className="numpad-grid">
        {buttons.map((value) => (
          <button
            key={value}
            className={`numpad-btn ${value === 'Clear' ? 'clear-btn' : ''}`}
            onClick={() => value === 'Clear' ? onClear() : onClick(value)}
            disabled={disabled}
          >
            {value === 'Clear' ? '⌫' : value}
          </button>
        ))}
      </div>
      
      <div className="action-buttons">
        <button className="action-btn detect-btn" onClick={onDetect} disabled={disabled}>
          {mode === 'price' ? 'Detect' : 'Re-Detect'}
        </button>
        <button 
          className={`action-btn ${mode === 'price' ? 'record-btn' : 'confirm-btn'}`}
          onClick={mode === 'price' ? onRecord : onTransaction}
          disabled={disabled}
        >
          {mode === 'price' ? 'Record' : 'Confirm'}
        </button>
        <button className="action-btn tare-btn" onClick={onTare} disabled={disabled}>
          Tare
        </button>
        <button 
          className="action-btn transaction-btn" 
          onClick={onTransaction}
          disabled={disabled}
        >
          {mode === 'price' ? 'Complete Sale' : 'Finish'}
        </button>
      </div>
    </div>
  );
};

export default Numpad;