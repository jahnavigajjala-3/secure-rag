import { useEffect, useState } from 'react';
import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent } from '../../components/ui/card';
import { api } from '../../api/client';
import { Search, Users, ShieldCheck, UserCheck, UserX, RefreshCw } from 'lucide-react';

interface RoleBadge {
  id: string;
  name: string;
}

interface Employee {
  id: string;
  username: string;
  full_name: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string | null;
  roles: RoleBadge[];
}

function rolePillClass(name: string): string {
  if (name === 'admin') return 'bg-purple-100 text-purple-700 border border-purple-200';
  if (name === 'employee') return 'bg-blue-100 text-blue-700 border border-blue-200';
  return 'bg-slate-100 text-slate-600 border border-slate-200';
}

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<Employee[]>('/api/users');
      setEmployees(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load employees.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchEmployees();
  }, []);

  const filtered = employees.filter((e) => {
    const q = search.toLowerCase();
    return (
      (e.full_name ?? '').toLowerCase().includes(q) ||
      (e.email ?? '').toLowerCase().includes(q) ||
      e.username.toLowerCase().includes(q) ||
      e.roles.some((r) => r.name.toLowerCase().includes(q))
    );
  });

  const adminCount = employees.filter((e) => e.roles.some((r) => r.name === 'admin')).length;
  const activeCount = employees.filter((e) => e.is_active).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Employees"
        description="View and manage all user accounts in your SecureRAG environment."
      />

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { icon: Users, label: 'Total users', value: employees.length, color: 'text-indigo-600 bg-indigo-50' },
          { icon: UserCheck, label: 'Active', value: activeCount, color: 'text-green-600 bg-green-50' },
          { icon: UserX, label: 'Inactive', value: employees.length - activeCount, color: 'text-red-500 bg-red-50' },
          { icon: ShieldCheck, label: 'Admins', value: adminCount, color: 'text-purple-600 bg-purple-50' },
        ].map(({ icon: Icon, label, value, color }) => (
          <Card key={label}>
            <CardContent className="flex items-center gap-3 py-4">
              <div className={`p-2 rounded-lg ${color}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs text-slate-500">{label}</p>
                <p className="text-xl font-semibold text-slate-800">{value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table card */}
      <Card>
        <CardContent className="p-0">
          {/* Toolbar */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-100">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by name, email or role…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-400"
              />
            </div>
            <button
              onClick={() => void fetchEmployees()}
              disabled={loading}
              className="p-2 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Error state */}
          {error && (
            <div className="px-4 py-3 text-sm text-red-600 bg-red-50 border-b border-red-100">
              {error}
            </div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div className="divide-y divide-slate-100">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 px-4 py-3 animate-pulse">
                  <div className="w-9 h-9 rounded-full bg-slate-200" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3.5 bg-slate-200 rounded w-40" />
                    <div className="h-3 bg-slate-100 rounded w-56" />
                  </div>
                  <div className="h-5 bg-slate-200 rounded w-16" />
                  <div className="h-5 bg-slate-200 rounded w-20" />
                </div>
              ))}
            </div>
          )}

          {/* Table */}
          {!loading && (
            <>
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
                  <Users className="w-8 h-8" />
                  <p className="text-sm">{search ? 'No users match your search.' : 'No users found.'}</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-slate-50 border-b border-slate-100 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        <th className="px-4 py-3">User</th>
                        <th className="px-4 py-3">Email</th>
                        <th className="px-4 py-3">Roles</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Joined</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filtered.map((emp) => {
                        const initials = (emp.full_name ?? emp.username)
                          .split(' ')
                          .map((w) => w[0])
                          .join('')
                          .toUpperCase()
                          .slice(0, 2);

                        const joinedDate = emp.created_at
                          ? new Date(emp.created_at).toLocaleDateString('en-IN', {
                              day: '2-digit',
                              month: 'short',
                              year: 'numeric',
                            })
                          : '—';

                        return (
                          <tr key={emp.id} className="hover:bg-slate-50 transition-colors">
                            {/* Avatar + name */}
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-semibold text-xs flex-shrink-0">
                                  {initials}
                                </div>
                                <div>
                                  <p className="font-medium text-slate-800">
                                    {emp.full_name ?? emp.username}
                                  </p>
                                  <p className="text-xs text-slate-400">@{emp.username}</p>
                                </div>
                              </div>
                            </td>

                            {/* Email */}
                            <td className="px-4 py-3 text-slate-600">
                              {emp.email ?? '—'}
                            </td>

                            {/* Roles */}
                            <td className="px-4 py-3">
                              <div className="flex flex-wrap gap-1">
                                {emp.roles.length === 0 ? (
                                  <span className="text-slate-400 text-xs">No roles</span>
                                ) : (
                                  emp.roles.map((r) => (
                                    <span
                                      key={r.id}
                                      className={`px-2 py-0.5 rounded-full text-xs font-medium ${rolePillClass(r.name)}`}
                                    >
                                      {r.name}
                                    </span>
                                  ))
                                )}
                              </div>
                            </td>

                            {/* Status */}
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                                  emp.is_active
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-red-100 text-red-600'
                                }`}
                              >
                                <span
                                  className={`w-1.5 h-1.5 rounded-full ${
                                    emp.is_active ? 'bg-green-500' : 'bg-red-400'
                                  }`}
                                />
                                {emp.is_active ? 'Active' : 'Inactive'}
                              </span>
                            </td>

                            {/* Joined */}
                            <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                              {joinedDate}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Footer count */}
              {filtered.length > 0 && (
                <div className="px-4 py-2 border-t border-slate-100 text-xs text-slate-400">
                  Showing {filtered.length} of {employees.length} user{employees.length !== 1 ? 's' : ''}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
