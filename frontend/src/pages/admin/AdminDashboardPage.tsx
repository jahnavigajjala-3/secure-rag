import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { useAuth } from '../../features/auth/auth-context';
import { api } from '../../api/client';
import { Users, FileText, ShieldCheck, UserCheck } from 'lucide-react';

interface Employee {
  id: string;
  is_active: boolean;
  roles: { id: string; name: string }[];
}

interface Document {
  id: string;
}

export default function AdminDashboardPage() {
  const { user } = useAuth();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [emps, docs] = await Promise.all([
          api.get<Employee[]>('/api/users'),
          api.get<Document[]>('/api/documents').catch(() => [] as Document[]),
        ]);
        setEmployees(emps);
        setDocuments(docs);
      } catch {
        // stats are best-effort; silently ignore failures
      } finally {
        setLoadingStats(false);
      }
    };
    void fetchStats();
  }, []);

  const activeCount = employees.filter((e) => e.is_active).length;
  const adminCount = employees.filter((e) => e.roles.some((r) => r.name === 'admin')).length;

  const stats = [
    {
      label: 'Signed-in as',
      value: user?.email ?? 'admin',
      hint: `Role: ${user?.role ?? 'admin'}`,
      icon: ShieldCheck,
      color: 'text-indigo-600 bg-indigo-50',
      to: null,
    },
    {
      label: 'Total users',
      value: loadingStats ? '…' : String(employees.length),
      hint: `${activeCount} active · ${adminCount} admin${adminCount !== 1 ? 's' : ''}`,
      icon: Users,
      color: 'text-blue-600 bg-blue-50',
      to: '/admin/employees',
    },
    {
      label: 'Active employees',
      value: loadingStats ? '…' : String(activeCount),
      hint: `${employees.length - activeCount} inactive`,
      icon: UserCheck,
      color: 'text-green-600 bg-green-50',
      to: '/admin/employees',
    },
    {
      label: 'Documents',
      value: loadingStats ? '…' : String(documents.length),
      hint: 'Total uploaded',
      icon: FileText,
      color: 'text-orange-600 bg-orange-50',
      to: '/admin/documents',
    },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin dashboard"
        description="Operational overview for your SecureRAG environment."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {stats.map((item) => {
          const Icon = item.icon;
          const content = (
            <Card key={item.label} className={item.to ? 'hover:shadow-md transition-shadow cursor-pointer' : ''}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardDescription>{item.label}</CardDescription>
                  <div className={`p-1.5 rounded-lg ${item.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                </div>
                <CardTitle className="text-2xl">{item.value}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-500">{item.hint}</p>
              </CardContent>
            </Card>
          );

          return item.to ? (
            <Link key={item.label} to={item.to} className="block">
              {content}
            </Link>
          ) : (
            <div key={item.label}>{content}</div>
          );
        })}
      </div>
    </div>
  );
}
