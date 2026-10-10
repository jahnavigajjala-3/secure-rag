import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { useAuth } from '../../features/auth/auth-context';

export default function AdminDashboardPage() {
  const { user } = useAuth();

  return (
    <div>
      <PageHeader
        title="Admin dashboard"
        description="Operational overview for your SecureRAG environment."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Welcome', value: user?.email ?? 'admin' },
          { label: 'Access role', value: user?.role ?? 'admin' },
          { label: 'Employees', value: 'Ready', hint: 'Next phase' },
          { label: 'Documents', value: 'Ready', hint: 'Next phase' },
        ].map((item) => (
          <Card key={item.label}>
            <CardHeader className="pb-3">
              <CardDescription>{item.label}</CardDescription>
              <CardTitle className="text-2xl">{item.value}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-500">{item.hint ?? 'Backend data integration pending'}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
