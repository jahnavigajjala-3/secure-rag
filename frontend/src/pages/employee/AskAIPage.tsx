import { useState } from 'react';
import PageHeader from '../../components/layout/PageHeader';
import { queryRAG } from '../../api/client';
import { Send, Bot, User, FileText, Loader2, Sparkles } from 'lucide-react';

export interface SourceCitation {
  document_id: string;
  document_name?: string;
  filename?: string;
  page?: number;
  chunk_index?: number;
  chunk_id: string;
  relevance_score?: number;
  text?: string;
  distance?: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceCitation[];
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  sources?: SourceCitation[];
}

export default function AskAIPage() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userText = query.trim();
    setQuery('');
    setError(null);

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: userText,
    };

    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const response = await queryRAG(userText);
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err: any) {
      setError(err.message || 'An error occurred while querying SecureRAG.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      <PageHeader
        title="Ask AI"
        description="Query your secure organizational knowledge base backed by pgvector RBAC."
      />

      {/* Chat History Box */}
      <div className="min-h-[400px] max-h-[600px] overflow-y-auto space-y-4 p-4 bg-white rounded-xl border border-slate-200 shadow-sm">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center text-slate-400 space-y-2">
            <Sparkles className="w-8 h-8 text-indigo-400" />
            <p className="text-sm font-medium">Ask a question about your documents to get started.</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.sender === 'ai' && (
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 text-indigo-600">
                  <Bot className="w-5 h-5" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-2xl p-4 text-sm ${
                  msg.sender === 'user'
                    ? 'bg-indigo-600 text-white rounded-br-none'
                    : 'bg-slate-100 text-slate-900 rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>

                {/* Sources / Citations */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-200/80 space-y-2">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Citations & Sources
                    </p>
                    <div className="grid gap-2">
                      {msg.sources.map((src, idx) => (
                        <div
                          key={idx}
                          className="bg-white p-2.5 rounded border border-slate-200 text-xs text-slate-700 space-y-1 shadow-xs"
                        >
                          <div className="flex items-center gap-1.5 font-medium text-indigo-600">
                            <FileText className="w-3.5 h-3.5" />
                            <span>
                              Document ID: {src.document_id || src.document_name || 'unknown'}
                              {src.chunk_index != null ? ` (Chunk ${src.chunk_index})` : ''}
                            </span>
                          </div>
                          <p className="text-slate-600 line-clamp-2">{src.text || src.filename || 'No source text available.'}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-900 flex items-center justify-center flex-shrink-0 text-white">
                  <User className="w-5 h-5" />
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-3 text-slate-500 text-sm py-2">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
            <span>Searching authorized chunks and generating response...</span>
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg">
          {error}
        </div>
      )}

      {/* Query Input Form */}
      <form onSubmit={handleSendMessage} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything about your authorized documents..."
          className="flex-1 px-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent shadow-xs"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 cursor-pointer transition-colors"
        >
          Send <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}