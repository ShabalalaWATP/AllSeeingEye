/** Shared steps for alert rule form tests. */
import type { BoundFunctions, queries } from '@testing-library/react';
import type { UserEvent } from '@testing-library/user-event';

type Scope = BoundFunctions<typeof queries>;

/** Opens the country checklist and ticks one country by name. */
export async function chooseCountry(user: UserEvent, form: Scope, name: string) {
  await user.click(form.getByText('Choose countries'));
  const startsWithName = (accessible: string) => accessible.startsWith(name);
  await user.click(await form.findByRole('checkbox', { name: startsWithName }));
}

/** The smallest valid rule: a name and an explicit worldwide scope. */
export async function fillWorldwideRule(user: UserEvent, form: Scope, name: string) {
  await user.type(form.getByLabelText('Alert rule name'), name);
  await user.selectOptions(form.getByLabelText('Location scope'), 'worldwide');
}
