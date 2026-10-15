import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Alert } from '../../components/ui/alert';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useAuth } from '../../features/auth/auth-context';
import { ApiError } from '../../api/client';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirm_password: '',
    account_type: 'employee',
    admin_access_key: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((previous) => ({ ...previous, [field]: value }));
  };

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!form.name.trim() || !form.email.trim() || !form.password || !form.confirm_password) {
      setError('Full name, email, password, and confirmation are required.');
      return;
    }

    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.');
      return;
    }

    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setIsSubmitting(true);

    try {
      await register({
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        confirm_password: form.confirm_password,
        account_type: form.account_type as 'employee' | 'admin',
        admin_access_key: form.admin_access_key || undefined,
      });
      navigate('/login', { replace: true });
    } catch (requestError) {
      const apiError = requestError as ApiError;
      setError(apiError.message || 'Unable to create your account.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Create an account</CardTitle>
          <CardDescription>Register as an employee, or as an admin if you have an invitation key.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            {error ? <Alert>{error}</Alert> : null}

            <div className="space-y-2">
              <Label htmlFor="name">Full name</Label>
              <Input
                id="name"
                value={form.name}
                onChange={(event) => handleChange('name', event.target.value)}
                placeholder="Alex Morgan"
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={form.email}
                onChange={(event) => handleChange('email', event.target.value)}
                placeholder="alex@company.com"
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(event) => handleChange('password', event.target.value)}
                  placeholder="••••••••"
                  disabled={isSubmitting}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={form.confirm_password}
                  onChange={(event) => handleChange('confirm_password', event.target.value)}
                  placeholder="••••••••"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            {/* Account type selector */}
            <div className="space-y-2">
              <Label>Account type</Label>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => handleChange('account_type', 'employee')}
                  disabled={isSubmitting}
                  className={`flex-1 rounded-lg border py-2 text-sm font-medium transition-colors ${
                    form.account_type === 'employee'
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Employee
                </button>
                <button
                  type="button"
                  onClick={() => handleChange('account_type', 'admin')}
                  disabled={isSubmitting}
                  className={`flex-1 rounded-lg border py-2 text-sm font-medium transition-colors ${
                    form.account_type === 'admin'
                      ? 'border-blue-600 bg-blue-50 text-blue-700'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  Admin
                </button>
              </div>
            </div>

            {/* Admin key — only shown when Admin is selected */}
            {form.account_type === 'admin' && (
              <div className="space-y-2">
                <Label htmlFor="admin_access_key">Admin invitation key</Label>
                <Input
                  id="admin_access_key"
                  value={form.admin_access_key}
                  onChange={(event) => handleChange('admin_access_key', event.target.value)}
                  placeholder="Enter your admin invitation key"
                  disabled={isSubmitting}
                />
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Creating account…' : 'Create account'}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-600">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-blue-700 hover:text-blue-800">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
