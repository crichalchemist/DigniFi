/**
 * Form 101 Preview Component
 *
 * Allows users to generate and preview their Official Form 101.
 */

import { useState } from 'react';
import { api } from '../api/client';
import { Button } from './common';

interface Form101PreviewProps {
  sessionId: number;
}

export function Form101Preview({ sessionId }: Form101PreviewProps) {
  const [generating, setGenerating] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const response = await api.forms.generateForm101({ session_id: sessionId });
      
      // In a real deployment, this would be a signed S3 URL or a backend proxy URL.
      // For MVP, we'll assume the backend provides a serving URL.
      // If the backend returns a local path, we might need to adjust.
      // For now, we'll use the path provided.
      if (response.form.pdf_file_path) {
        setPdfUrl(response.form.pdf_file_path);
      } else {
        setError('Form generated but no file path returned.');
      }
    } catch (err) {
      setError('Failed to generate form. Please try again.');
      console.error(err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="border rounded-md p-6 bg-white shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Form 101 Preview</h3>
        <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">
          Official Form 101
        </span>
      </div>
      
      <p className="mb-6 text-gray-600">
        Based on the information you've provided, we can generate your Voluntary Petition for Individuals Filing for Bankruptcy. 
        You can preview this form to see how your information will appear to the court.
      </p>
      
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {!pdfUrl ? (
        <div className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-300 rounded-md bg-gray-50">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <div className="mt-4">
            <Button onClick={handleGenerate} disabled={generating} variant="primary">
              {generating ? 'Generating PDF...' : 'Generate Form 101 Preview'}
            </Button>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            This may take a few moments.
          </p>
        </div>
      ) : (
        <div className="bg-green-50 p-4 rounded-md border border-green-200">
          <div className="flex items-center mb-3">
            <svg className="h-5 w-5 text-green-500 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h4 className="text-sm font-medium text-green-800">Form generated successfully!</h4>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-green-700">Official Form 101.pdf</span>
            <a 
              href={pdfUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-green-700 bg-green-100 hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download PDF
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
