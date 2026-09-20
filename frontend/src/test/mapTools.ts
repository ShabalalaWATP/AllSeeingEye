import { screen, within } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';

/** Follow the same favourite-or-chooser path as a map user. */
export async function openMapTool(user: UserEvent, label: string) {
  const tools = await screen.findByRole('group', { name: 'Map tools' });
  const favourite = within(tools).queryByRole('button', { name: label });
  if (favourite) {
    await user.click(favourite);
    return;
  }
  await user.click(within(tools).getByRole('button', { name: 'Tools' }));
  const chooser = screen.getByRole('region', { name: 'Tools' });
  await user.click(within(chooser).getByRole('button', { name: label }));
}
