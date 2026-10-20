import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

interface DatasetWarningsProps {
  warnings: string[];
  isError?: boolean;
}

export const DatasetWarnings: React.FC<DatasetWarningsProps> = ({ warnings, isError = false }) => {
  if (!warnings || warnings.length === 0) return null;

  return (
    <div className={`notice-box ${isError ? 'error' : ''}`} role="alert">
      <div className="notice-icon">
        {isError ? <AlertTriangle size={20} /> : <Info size={20} />}
      </div>
      <div className="notice-content">
        <strong>{isError ? 'Dataset Ingestion Alert' : 'Dataset Notice'}</strong>
        {warnings.length === 1 ? (
          <p>{warnings[0]}</p>
        ) : (
          <ul className="notice-list">
            {warnings.map((warn, index) => (
              <li key={index}>{warn}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
