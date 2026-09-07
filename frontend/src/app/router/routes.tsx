/**
 * Route table shared by the browser router (App) and the memory router (tests).
 * The globe is the root route. Admin pages and the globe are code split so the
 * auth pages never load MapLibre.
 */
import { lazy } from 'react';
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
const ReportsPage = lazy(() => import('@/features/reports/ReportsPage'));
const ResearchPage = lazy(() => import('@/features/research/ResearchPage'));
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
const CyberPage = lazy(() =>
  import('@/features/trackers/ModulePages').then((m) => ({ default: m.CyberPage })),
);
const DirectionPage = lazy(() => import('@/features/direction/DirectionPage'));
const WarningPage = lazy(() => import('@/features/warning/WarningPage'));
const PlanPage = lazy(() => import('@/features/direction/PlanPage'));
const BrandCapturePage = lazy(() => import('@/app/dev/BrandCapturePage'));

const devRoutes: RouteObject[] = import.meta.env.DEV
  ? [{ path: '/brand/capture', element: <BrandCapturePage /> }]
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
          { path: 'sources', element: <SourcesPage /> },
          { path: 'reports', element: <ReportsPage /> },
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
          { path: 'trackers/cyber', element: <CyberPage /> },
          { path: 'trackers/social', element: <SocialPage /> },
          { path: 'direction', element: <DirectionPage /> },
          { path: 'direction/plans/:id', element: <PlanPage /> },
          { path: 'warning', element: <WarningPage /> },
          { path: 'teams', element: <TeamsPage /> },
          { path: 'account', element: <AccountPage /> },
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
