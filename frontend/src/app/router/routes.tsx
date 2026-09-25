/**
 * Route table shared by the browser router (App) and the memory router (tests).
 * The globe is the root route. Admin pages and the globe are code split so the
 * auth pages never load MapLibre.
 */
import { lazy, type ComponentType, type ReactElement } from 'react';
import type { RouteObject } from 'react-router';

import { AdminShell } from '@/app/shell/AdminShell';
import { AppShell } from '@/app/shell/AppShell';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { RequestAccountPage } from '@/features/auth/RequestAccountPage';
import { SetPasswordPage } from '@/features/auth/SetPasswordPage';

import AdminSessionGate from './AdminSessionGate';
import { NotFoundPage } from '../NotFoundPage';
import { RedirectWithQuery, RequireAdmin, RequireAuth } from './guards';

const GlobePage = lazy(() => import('@/features/globe/GlobePage'));
const AdminOverviewPage = lazy(() => import('@/features/admin/AdminOverviewPage'));
const AdminRequestsPage = lazy(() => import('@/features/admin/AdminRequestsPage'));
const AdminUsersPage = lazy(() => import('@/features/admin/AdminUsersPage'));
const AdminAuditPage = lazy(() => import('@/features/admin/AdminAuditPage'));
const AdminSourcesPage = lazy(() => import('@/features/admin/AdminSourcesPage'));
const AdminLlmPage = lazy(() => import('@/features/admin/AdminLlmPage'));
const TotpSettingsPage = lazy(() => import('@/features/auth/TotpSettingsPage'));
const SocialPage = lazy(() => import('@/features/trackers/SocialPage'));
const TeamsPage = lazy(() => import('@/features/teams/TeamsPage'));
const AccountPage = lazy(() => import('@/features/account/AccountPage'));
const SettingsPage = lazy(() => import('@/features/account/SettingsPage'));
const EconomyPage = lazy(() => import('@/features/economy/EconomyPage'));
const CyberIntelligencePage = lazy(() => import('@/features/cyber/CyberPage'));
const SavedResearchPage = lazy(() => import('@/features/reports/SavedResearchPage'));
const SavedUpdatesPage = lazy(() => import('@/features/reports/SavedUpdatesPage'));
const SavedAssessmentsPage = lazy(() => import('@/features/reports/SavedAssessmentsPage'));
const ResearchPage = lazy(() => import('@/features/research/ResearchPage'));
const ReportJobsPage = lazy(() => import('@/features/report-jobs/ReportJobsPage'));
const ReportJobPage = lazy(() => import('@/features/report-jobs/ReportJobPage'));
const PhotoResearchPage = lazy(() => import('@/features/research/PhotoResearchPage'));
const RecurringResearchPage = lazy(() => import('@/features/reports/RecurringResearchPage'));
const SourcesPage = lazy(() => import('@/features/sources/SourcesPage'));
const AnnotationMonitorsPage = lazy(() => import('@/features/reports/AnnotationMonitorsPage'));
const AnnotationMonitorPage = lazy(() => import('@/features/reports/AnnotationMonitorPage'));
const AnnotationTransitionPage = lazy(() => import('@/features/reports/AnnotationTransitionPage'));
const ReportPage = lazy(() => import('@/features/reports/ReportPage'));
const TrackersPage = lazy(() => import('@/features/trackers/TrackersPage'));
const ConflictPage = lazy(() => import('@/features/trackers/ConflictPage'));
const HazardPage = lazy(() => import('@/features/trackers/HazardPage'));
const AviationPage = lazy(() => import('@/features/trackers/AviationPage'));
const MaritimePage = lazy(() =>
  import('@/features/trackers/ModulePages').then((m) => ({ default: m.MaritimePage })),
);
const SpacePage = lazy(() =>
  import('@/features/trackers/ModulePages').then((m) => ({ default: m.SpacePage })),
);
const FiguresPage = lazy(() => import('@/features/trackers/FiguresPage'));
const UkrainePage = lazy(() => import('@/features/ukraine/UkrainePage'));
const DirectionPage = lazy(() => import('@/features/direction/DirectionPage'));
const WarningPage = lazy(() => import('@/features/warning/WarningPage'));
const PlanPage = lazy(() => import('@/features/direction/PlanPage'));
const WatchesPage = lazy(() => import('@/features/watches/WatchesPage'));
// Development previews render fixtures only. Each import lives inside the DEV branch,
// so production builds fold the branch away and never emit the preview chunks.
function devPage(load: () => Promise<{ default: ComponentType }>): ReactElement {
  const Page = lazy(load);
  return <Page />;
}

const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [
      { path: '/brand/capture', element: devPage(() => import('@/app/dev/BrandCapturePage')) },
      { path: '/dev/cyber-preview', element: devPage(() => import('@/app/dev/CyberPreviewPage')) },
      { path: '/dev/pages-preview', element: devPage(() => import('@/app/dev/PagesPreviewPage')) },
      {
        path: '/dev/figures-preview',
        element: devPage(() => import('@/app/dev/FiguresPreviewPage')),
      },
      {
        path: '/dev/ukraine-preview',
        element: devPage(() => import('@/app/dev/UkrainePreviewPage')),
      },
      { path: '/dev/admin-preview', element: devPage(() => import('@/app/dev/AdminPreviewPage')) },
      {
        path: '/dev/economy-preview',
        element: devPage(() => import('@/app/dev/EconomyPreviewPage')),
      },
      {
        path: '/dev/navigation-preview',
        element: devPage(() => import('@/app/dev/NavigationPreviewPage')),
      },
      {
        path: '/dev/report-preview',
        element: devPage(() => import('@/app/dev/ReportPreviewPage')),
      },
    ]
  : [];

export const routes: RouteObject[] = [
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/request-account', element: <RequestAccountPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
      { path: '/set-password', element: <SetPasswordPage /> },
    ],
  },
  { path: '/sources', element: <RedirectWithQuery to="/admin/catalogue" /> },
  { path: '/activate', element: <RedirectWithQuery to="/set-password" /> },
  { path: '/reset-password', element: <RedirectWithQuery to="/set-password" /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <GlobePage /> },
          { path: 'research', element: <ResearchPage /> },
          { path: 'research/jobs', element: <ReportJobsPage /> },
          { path: 'research/jobs/:id', element: <ReportJobPage /> },
          { path: 'geolocation', element: <PhotoResearchPage /> },
          { path: 'research/photo', element: <RedirectWithQuery to="/geolocation" /> },
          { path: 'subscriptions', element: <RecurringResearchPage /> },
          { path: 'research/recurring', element: <RedirectWithQuery to="/subscriptions" /> },
          { path: 'research/saved', element: <SavedResearchPage /> },
          { path: 'subscriptions/saved', element: <SavedUpdatesPage /> },
          { path: 'geolocation/saved', element: <SavedAssessmentsPage /> },
          // Each section keeps its own saved reports; this link still opens one.
          { path: 'reports', element: <RedirectWithQuery to="/research/saved" /> },
          { path: 'reports/:id', element: <ReportPage /> },
          { path: 'annotation-monitors', element: <AnnotationMonitorsPage /> },
          { path: 'annotation-monitors/:monitorId', element: <AnnotationMonitorPage /> },
          {
            path: 'annotation-monitors/:monitorId/transitions/:transitionId',
            element: <AnnotationTransitionPage />,
          },
          { path: 'trackers', element: <TrackersPage /> },
          { path: 'trackers/conflicts/:id', element: <ConflictPage /> },
          { path: 'trackers/disasters/:hazard', element: <HazardPage /> },
          { path: 'trackers/aviation', element: <AviationPage /> },
          { path: 'trackers/maritime', element: <MaritimePage /> },
          { path: 'trackers/space', element: <SpacePage /> },
          // The tracker board now lives inside the single cyber workspace.
          { path: 'trackers/cyber', element: <RedirectWithQuery to="/cyber" /> },
          { path: 'trackers/figures', element: <FiguresPage /> },
          { path: 'conflicts/ukraine', element: <UkrainePage /> },
          { path: 'trackers/social', element: <SocialPage /> },
          { path: 'direction', element: <DirectionPage /> },
          { path: 'direction/plans/:id', element: <PlanPage /> },
          { path: 'warning', element: <WarningPage /> },
          { path: 'watches', element: <WatchesPage /> },
          { path: 'teams', element: <TeamsPage /> },
          { path: 'account', element: <AccountPage /> },
          { path: 'settings', element: <SettingsPage /> },
          { path: 'economy', element: <EconomyPage /> },
          { path: 'cyber', element: <CyberIntelligencePage /> },
          { path: 'account/security', element: <TotpSettingsPage /> },
        ],
      },
      {
        path: 'admin',
        element: <RequireAdmin />,
        children: [
          {
            element: <AdminSessionGate />,
            children: [
              {
                element: <AdminShell />,
                children: [
                  { index: true, element: <AdminOverviewPage /> },
                  { path: 'requests', element: <AdminRequestsPage /> },
                  { path: 'users', element: <AdminUsersPage /> },
                  { path: 'teams', element: <TeamsPage /> },
                  { path: 'audit', element: <AdminAuditPage /> },
                  { path: 'sources', element: <AdminSourcesPage /> },
                  { path: 'catalogue', element: <SourcesPage /> },
                  { path: 'llm', element: <AdminLlmPage /> },
                  { path: 'security', element: <TotpSettingsPage /> },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
  ...devRoutes,
  { path: '*', element: <NotFoundPage /> },
];
