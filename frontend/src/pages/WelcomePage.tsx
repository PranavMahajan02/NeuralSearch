import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { PlatformsPage } from "./PlatformsPage";

/** First visit (nothing indexed yet): explain the two steps, then the platform cards. */
export function WelcomePage() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-blue-200 bg-blue-50 p-5 dark:border-blue-900 dark:bg-blue-950">
        <h2 className="text-lg font-semibold">Welcome{user ? `, ${user.name}` : ""}</h2>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-800 dark:text-slate-200">
          <li>Connect at least one platform: a local folder, Google Drive or GitHub.</li>
          <li>
            Index it. Progress appears on the Indexing page; you can search as soon as files are indexed.
          </li>
        </ol>
        <Link
          to="/search"
          className="mt-3 inline-block text-sm font-semibold text-blue-800 hover:underline dark:text-blue-300"
        >
          Skip to search →
        </Link>
      </section>
      <PlatformsPage />
    </div>
  );
}
