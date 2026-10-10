import { useState } from 'react';
import PageHeader from '../../components/layout/PageHeader';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { uploadDocument } from '../../api/client';
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export default function DocumentsPage() {
  const [file, setFile] = useState<File | null>(null);
  const [selectedRole, setSelectedRole] = useState<string>('employee');
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setMessage(null);

    try {
      await uploadDocument(file, [selectedRole]);
      setMessage({ type: 'success', text: `Document "${file.name}" uploaded and chunked successfully!` });
      setFile(null);
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || 'Failed to upload document.' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <PageHeader
        title="Document Management & Vault"
        description="Ingest PDFs or text documents into the pgvector knowledge base with role-based access control."
      />

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Upload New Document</CardTitle>
            <CardDescription>Select a file and restrict access by role.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Document File</label>
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">Minimum Permitted Role</label>
                <select
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="employee">Employee (General Access)</option>
                  <option value="admin">Admin Only</option>
                </select>
              </div>

              {message && (
                <div
                  className={`p-3 rounded-lg text-sm flex items-center gap-2 ${
                    message.type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'
                  }`}
                >
                  {message.type === 'success' ? <CheckCircle2 className="w-4 h-4 flex-shrink-0" /> : <AlertCircle className="w-4 h-4 flex-shrink-0" />}
                  <span>{message.text}</span>
                </div>
              )}

              <Button type="submit" disabled={!file || uploading} className="w-full">
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Ingesting & Vectorizing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload & Process
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">RBAC Ingestion Guidelines</CardTitle>
            <CardDescription>How SecureRAG processes your uploads</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600">
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <FileText className="w-5 h-5 text-indigo-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800 block">Automatic Chunking & Embeddings</strong>
                Files are cleaned, split into overlapping chunks, and converted into vectors.
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800 block">Strict SQL Filtering</strong>
                Retrieved chunks are filtered at the database level via `pgvector` and `document_roles`.
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}