/** Resolve research route chunks before timing interactions across feature boundaries. */
export async function preloadResearchRoutes(): Promise<void> {
  await Promise.all([
    import('@/features/reports/SavedResearchPage'),
    import('@/features/reports/ReportPage'),
  ]);
}
