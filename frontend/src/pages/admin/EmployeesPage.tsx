import PageHeader from '../../components/layout/PageHeader';
import { Card, CardContent } from '../../components/ui/card';

export default function EmployeesPage() {
  return (
    <div>
      <PageHeader title="Employees" description="Manage employee accounts." />
      <Card>
        <CardContent className="text-sm text-slate-600">Employee management UI coming soon.</CardContent>
      </Card>
    </div>
  );
}
