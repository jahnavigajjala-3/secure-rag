import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { useEffect, useState } from 'react';

export default function MyDocumentsPage() {
  const [docs, setDocs] = useState<Array<{ id: string; filename: string; status: string }>>([]);

  useEffect(() => {
    let ignore = false;

    const load = async () => {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'}/api/documents/my`, {
          headers: { 'Accept': 'application/json' },
          credentials: 'same-origin',
        });
        if (!ignore && res.ok) {
          const data = await res.json();
          setDocs(data || []);
        }
      } catch {
        // ignore network errors for placeholder
      }
    };

    void load();
    return () => { ignore = true; };
  }, []);

  return (
    <div>
      <PageHeader title="My Documents" description="Documents you have access to." />

      <div className="grid gap-4">
        {docs.length === 0 ? (
          <Card>
            <CardContent className="text-sm text-slate-600">You have no documents yet.</CardContent>
          </Card>
        ) : (
          docs.map((d) => (
            <Card key={d.id}>
              <CardHeader>
                <CardDescription>{d.filename}</CardDescription>
                <CardTitle className="text-base">{d.status}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-slate-600">ID: {d.id}</CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
