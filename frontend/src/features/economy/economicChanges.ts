import type { EconomyRegion, EconomySeries } from '@/lib/api/economy';
import { formatEconomicValue, latestObservation } from './economyPresentation';

export interface AnnualChange {
  value: number;
  unit: 'percentage points' | '%';
  from: string;
  to: string;
}

/** Compare adjacent observed years only. Missing years must not become annual change. */
export function annualChange(series: EconomySeries): AnnualChange | null {
  const latest = latestObservation(series);
  if (series.frequency !== 'annual' || !latest || !/^\d{4}$/.test(latest.date)) return null;
  const previous = series.points.find((point) => point.date === String(Number(latest.date) - 1));
  if (previous?.value == null || latest.value === null) return null;
  const difference = latest.value - previous.value;
  if (!Number.isFinite(difference)) return null;
  if (/%|percent/i.test(series.unit))
    return { value: difference, unit: 'percentage points', from: previous.date, to: latest.date };
  // Relative change from a negative or zero amount is easy to misread, so omit it.
  if (previous.value <= 0 || latest.value < 0) return null;
  const relative = (difference / previous.value) * 100;
  if (!Number.isFinite(relative)) return null;
  return {
    value: relative,
    unit: '%',
    from: previous.date,
    to: latest.date,
  };
}

export function formatAnnualChange(change: AnnualChange): string {
  const value = new Intl.NumberFormat('en-GB', {
    maximumFractionDigits: 2,
    signDisplay: 'exceptZero',
  }).format(change.value);
  return `${value}${change.unit === '%' ? '%' : ' pp'} vs ${change.from}`;
}

export function observationAge(date: string, currentYear = new Date().getUTCFullYear()): string {
  if (!/^\d{4}$/.test(date)) return '';
  const age = currentYear - Number(date);
  return age > 2 ? `${age} years old` : '';
}

export interface EconomicInsight {
  title: string;
  text: string;
  series: EconomySeries;
}

export function countryInsights(region: EconomyRegion): EconomicInsight[] {
  const result: EconomicInsight[] = [];
  const find = (id: string) => region.series.find((series) => series.id === id);
  const growth = find('growth');
  const growthPoint = growth && latestObservation(growth);
  if (growth && growthPoint && growthPoint.value !== null) {
    const state =
      growthPoint.value < 0 ? 'contracted' : growthPoint.value > 0 ? 'expanded' : 'was unchanged';
    const change = annualChange(growth);
    result.push({
      title: 'Real economic activity',
      text: `Output ${state} in ${growthPoint.date}, with inflation-adjusted annual growth of ${formatEconomicValue(growthPoint.value, growth.unit)}.${change ? ` The growth rate changed by ${formatAnnualChange(change)}.` : ' Comparable preceding-year growth is unavailable.'}`,
      series: growth,
    });
  }
  const inflation = find('inflation');
  const inflationPoint = inflation && latestObservation(inflation);
  if (inflation && inflationPoint && inflationPoint.value !== null) {
    const change = annualChange(inflation);
    const direction =
      inflationPoint.value < 0
        ? 'Consumer prices fell on average over the year.'
        : inflationPoint.value > 0
          ? 'Consumer prices still rose on average over the year.'
          : 'Average consumer prices were unchanged over the year.';
    result.push({
      title: 'Household price pressure',
      text: `Inflation was ${formatEconomicValue(inflationPoint.value, inflation.unit)} in ${inflationPoint.date}. ${direction}${change ? ` The rate ${change.value < 0 ? 'eased' : change.value > 0 ? 'increased' : 'was unchanged'} (${formatAnnualChange(change)}).` : ''}`,
      series: inflation,
    });
  }
  const account = find('current_account');
  const accountPoint = account && latestObservation(account);
  if (account && accountPoint && accountPoint.value !== null) {
    result.push({
      title: 'External balance',
      text: `The current account recorded ${accountPoint.value > 0 ? 'a surplus' : accountPoint.value < 0 ? 'a deficit' : 'a balance'} of ${formatEconomicValue(Math.abs(accountPoint.value), account.unit)} of GDP in ${accountPoint.date}. This includes trade, income and transfers; it is not a standalone risk rating.`,
      series: account,
    });
  }
  const debt = find('government_debt');
  const debtPoint = debt && latestObservation(debt);
  if (debt && debtPoint && debtPoint.value !== null) {
    result.push({
      title: 'Public finance scope',
      text: `Reported central government debt was ${formatEconomicValue(debtPoint.value, debt.unit)} of GDP in ${debtPoint.date}. It may exclude other government bodies, so cross-country debt comparisons require care.`,
      series: debt,
    });
  }
  return result;
}
