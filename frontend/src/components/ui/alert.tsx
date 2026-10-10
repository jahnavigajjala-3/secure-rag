import * as React from 'react';

import { cn } from '../../lib/utils';

const Alert = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cn('rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700', className)}
      {...props}
    />
  ),
);
Alert.displayName = 'Alert';

export { Alert };
