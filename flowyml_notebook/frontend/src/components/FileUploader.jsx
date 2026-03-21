import React, { useState, useCallback, useRef } from 'react';
import { Upload, FileText, Loader2, CheckCircle, XCircle, FileSpreadsheet, Plus } from 'lucide-react';

export default function FileUploader({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const csvFiles = files.filter(f => f.name.endsWith('.csv') || f.name.endsWith('.tsv') || f.name.endsWith('.txt'));

    if (csvFiles.length > 0) {
      uploadFile(csvFiles[0]);
    } else {
      setError('Please drop a CSV file');
      setTimeout(() => setError(null), 3000);
    }
  }, []);

  const uploadFile = async (file) => {
    setUploading(true);
    setError(null);
    setLastResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload-csv', { method: 'POST', body: formData });
      const data = await res.json();

      if (data.error) {
        setError(data.error);
      } else {
        setLastResult(data);
        if (onUploadComplete) onUploadComplete(data);
      }
    } catch (err) {
      setError('Upload failed: ' + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files?.length > 0) {
      uploadFile(e.target.files[0]);
    }
  };

  return (
    <div className="file-uploader-wrapper">
      <div
        className={`file-upload-zone ${isDragging ? 'dragging' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.tsv,.txt"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        {uploading ? (
          <div className="upload-status">
            <Loader2 size={20} className="animate-spin" style={{ color: 'var(--accent-light)' }} />
            <span>Loading data...</span>
          </div>
        ) : lastResult ? (
          <div className="upload-status success">
            <CheckCircle size={18} style={{ color: 'var(--green)' }} />
            <div>
              <strong>{lastResult.variable_name}</strong>
              <span className="upload-detail">
                {lastResult.rows.toLocaleString()} rows × {lastResult.columns.length} cols
              </span>
            </div>
            <button className="upload-another" onClick={(e) => { e.stopPropagation(); setLastResult(null); }}>
              <Plus size={12} /> Load Another
            </button>
          </div>
        ) : (
          <div className="upload-prompt">
            <div className="upload-icon-circle">
              <FileSpreadsheet size={20} style={{ color: 'var(--accent-light)' }} />
            </div>
            <span className="upload-main-text">
              {isDragging ? 'Drop CSV here' : 'Drop CSV file or click to browse'}
            </span>
            <span className="upload-sub-text">
              Automatically loaded as a pandas DataFrame
            </span>
          </div>
        )}

        {error && (
          <div className="upload-error">
            <XCircle size={12} />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
