import type { SelectOption } from '@/components/ui/Field';

export const roleOptions: readonly SelectOption[] = [
  { value: 'user', label: 'User' },
  { value: 'manager', label: 'Manager' },
  { value: 'admin', label: 'Admin' },
];
