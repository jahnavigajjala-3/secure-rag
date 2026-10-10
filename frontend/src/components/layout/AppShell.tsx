import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/auth-context';

export default function AppShell({ user, children }: { user: any; children: React.ReactNode }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = (e: React.MouseEvent) => {
    e.preventDefault();
    logout();
    navigate('/login', { replace: true });
  };

  const isAdmin = user?.role?.toLowerCase() === 'admin';

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-white border-r border-slate-200 p-4 flex flex-col justify-between">
        <div className="space-y-6">
          <div className="font-bold text-lg text-indigo-600 px-2">SecureRAG</div>
          
          <nav className="space-y-1">
            {isAdmin ? (
              <>
                <NavLink
                  to="/admin/dashboard"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/admin/employees"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  Employees
                </NavLink>
                <NavLink
                  to="/admin/roles"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  Roles
                </NavLink>
                <NavLink
                  to="/admin/documents"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  Documents
                </NavLink>
              </>
            ) : (
              <>
                <NavLink
                  to="/employee/dashboard"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/employee/ask-ai"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  Ask AI
                </NavLink>
                <NavLink
                  to="/employee/my-documents"
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive ? 'bg-indigo-50 text-indigo-600' : 'text-slate-600 hover:bg-slate-100'
                    }`
                  }
                >
                  My Documents
                </NavLink>
              </>
            )}
          </nav>
        </div>

        {/* User Footer */}
        <div className="border-t border-slate-200 pt-4">
          <div className="text-sm font-medium text-slate-800 px-2 truncate">
            {user?.email}
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="mt-2 w-full text-left px-2 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Page Area */}
      <main className="flex-1 overflow-y-auto p-8">
        {children}
      </main>
    </div>
  );
}