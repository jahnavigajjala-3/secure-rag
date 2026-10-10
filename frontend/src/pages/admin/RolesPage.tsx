import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent } from '../../components/ui/card';

export default function RolesPage() {
  return (
    <div>
      <PageHeader title="Roles" description="Manage RBAC roles." />
      <Card>
        <CardContent className="text-sm text-slate-600">Role management UI coming soon.</CardContent>
      </Card>
    </div>
  );
}
