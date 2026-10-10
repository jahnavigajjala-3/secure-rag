import { Navigate, Outlet, RouterProvider, createBrowserRouter } from 'react-router-dom';
import { useAuth } from '../features/auth/auth-context';
import AppShell from '../components/layout/AppShell';

// Public Pages
import LandingPage from '../pages/public/LandingPage';
import LoginPage from '../pages/public/LoginPage';
import RegisterPage from '../pages/public/RegisterPage';

// Dashboards (Existing files)
import AdminDashboardPage from '../pages/admin/AdminDashboardPage';
import EmployeeDashboardPage from '../pages/employee/EmployeeDashboardPage';
import DocumentsPage from '../pages/admin/DocumentsPage';
import AskAIPage from '../pages/employee/AskAIPage';
import MyDocumentsPage from '../pages/employee/MyDocumentsPage';
import EmployeesPage from '../pages/admin/EmployeesPage';
import RolesPage from '../pages/admin/RolesPage';
function PageLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
      Loading session…
    </div>
  );
}

function PublicRoute() {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <PageLoader />;

  if (isAuthenticated && user) {
    const role = user.role?.toLowerCase();
    const destination = role === 'admin' ? '/admin/dashboard' : '/employee/dashboard';
    return <Navigate to={destination} replace />;
  }

  return <Outlet />;
}

function RoleProtectedRoute({ allowedRole }: { allowedRole?: 'admin' | 'employee' }) {
  const { user, isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <PageLoader />;

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  const userRole = user.role?.toLowerCase();

  if (allowedRole && userRole !== allowedRole.toLowerCase()) {
    const fallbackDestination = userRole === 'admin' ? '/admin/dashboard' : '/employee/dashboard';
    return <Navigate to={fallbackDestination} replace />;
  }

  return (
    <AppShell user={user}>
      <Outlet />
    </AppShell>
  );
}

const router = createBrowserRouter([
  {
    element: <PublicRoute />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
    ],
  },
  {
    path: '/admin',
    element: <RoleProtectedRoute allowedRole="admin" />,
    children: [
      { path: 'dashboard', element: <AdminDashboardPage /> },
      { path: 'documents', element: <DocumentsPage /> },
      { path: 'employees', element: <EmployeesPage /> },
      { path: 'roles', element: <RolesPage /> },
    ],
  },
  {
    path: '/employee',
    element: <RoleProtectedRoute allowedRole="employee" />,
    children: [
      { path: 'dashboard', element: <EmployeeDashboardPage /> },
      { path: 'ask-ai', element: <AskAIPage /> },
      { path: 'my-documents', element: <MyDocumentsPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}