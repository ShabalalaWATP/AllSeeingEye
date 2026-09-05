/**
 * Route table shared by the browser router (App) and the memory router (tests).
 * The globe is the root route. Admin pages and the globe are code split so the
 * auth pages never load MapLibre.
 */
import { lazy } from 'react';
import type { RouteObject } from 'react-router';

import { AppShell } from '@/app/shell/AppShell';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { RequestAccountPage } from '@/features/auth/RequestAccountPage';
import { SetPasswordPage } from '@/features/auth/SetPasswordPage';

import { NotFoundPage } from '../NotFoundPage';
import { RedirectWithQuery, RequireAdmin, RequireAuth } from './guards';

const GlobePage = lazy(() => import('@/features/globe/GlobePage'));
const AdminRequestsPage = lazy(() => import('@/features/admin/AdminRequestsPage'));
const AdminUsersPage = lazy(() => import('@/features/admin/AdminUsersPage'));
const AdminAuditPage = lazy(() => import('@/features/admin/AdminAuditPage'));
const AdminSourcesPage = lazy(() => import('@/features/admin/AdminSourcesPage'));
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
          {
            path: 'admin',
            element: <RequireAdmin />,
            children: [
              { path: 'requests', element: <AdminRequestsPage /> },
              { path: 'users', element: <AdminUsersPage /> },
              { path: 'audit', element: <AdminAuditPage /> },
              { path: 'sources', element: <AdminSourcesPage /> },
            ],
          },
        ],
      },
    ],
  },
  ...devRoutes,
  { path: '*', element: <NotFoundPage /> },
];
