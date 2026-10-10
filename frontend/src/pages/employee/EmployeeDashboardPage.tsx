import { Link } from 'react-router-dom';
import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { useAuth } from '../../features/auth/auth-context';
import { MessageSquare, FileText, ArrowRight } from 'lucide-react';

export default function EmployeeDashboardPage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Your SecureRAG workspace."
      />

      <div className="grid gap-6 md:grid-cols-2">
        {/* Account Info Card */}
        <Card>
          <CardHeader>
            <CardDescription>Current account</CardDescription>
            <CardTitle className="text-xl font-bold text-slate-900">
              {user?.email ?? 'vvreddygajjala6@gmail.com'}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>
              <strong className="text-slate-800">Role:</strong> {user?.role ?? 'employee'}
            </p>
            <p className="text-xs text-slate-500 pt-2">
              SecureRAG access is controlled by the backend based on your assigned roles and permissions.
            </p>
          </CardContent>
        </Card>

        {/* Quick Actions Card */}
        <Card>
          <CardHeader>
            <CardDescription>Quick actions</CardDescription>
            <CardTitle className="text-lg font-semibold text-slate-900">Start</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link
              to="/employee/ask-ai"
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-indigo-500 hover:bg-indigo-50/50 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <MessageSquare className="w-5 h-5 text-indigo-600" />
                <span className="font-medium text-slate-800 group-hover:text-indigo-600">
                  Ask AI
                </span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600" />
            </Link>

            <Link
              to="/employee/my-documents"
              className="flex items-center justify-between p-3 rounded-lg border border-slate-200 hover:border-indigo-500 hover:bg-indigo-50/50 transition-colors group"
            >
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-indigo-600" />
                <span className="font-medium text-slate-800 group-hover:text-indigo-600">
                  My Documents
                </span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600" />
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}