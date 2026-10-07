import { useState } from "react";
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { MotionConfig } from "motion/react";

import { createQueryClient } from "./api/queries";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { ToastProvider } from "./components/common/Toast";
import { AppShell } from "./components/layout/AppShell";
import { IndexingPage } from "./pages/IndexingPage";
import { LoginPage } from "./pages/LoginPage";
import { PlatformsPage } from "./pages/PlatformsPage";
import { RootRedirect } from "./pages/RootRedirect";
import { SearchPage } from "./pages/SearchPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { ThemeProvider } from "./hooks/useTheme";

function NotFound() {
  return (
    <div className="py-16 text-center">
      <h2 className="text-lg font-semibold">Page not found</h2>
      <Link to="/search" className="mt-2 inline-block text-blue-800 hover:underline dark:text-blue-300">
        Go to search
      </Link>
    </div>
  );
}

export function AppRoutes() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <RootRedirect />
            </RequireAuth>
          }
        />
        <Route
          path="/onboarding"
          element={
            <RequireAuth>
              <OnboardingPage />
            </RequireAuth>
          }
        />
        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/search" element={<SearchPage />} />
          <Route path="/platforms" element={<PlatformsPage />} />
          <Route path="/indexing" element={<IndexingPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export function Providers({ client, children }: { client: QueryClient; children: React.ReactNode }) {
  return (
    <QueryClientProvider client={client}>
      {/* Animations follow the OS "reduce motion" setting. */}
      <MotionConfig reducedMotion="user">
        <ThemeProvider>
          <ToastProvider>
            <AuthProvider>{children}</AuthProvider>
          </ToastProvider>
        </ThemeProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}

export default function App() {
  const [client] = useState(createQueryClient);

  return (
    <BrowserRouter>
      <Providers client={client}>
        <AppRoutes />
      </Providers>
    </BrowserRouter>
  );
}
