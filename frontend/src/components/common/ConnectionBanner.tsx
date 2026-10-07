import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { WifiOff } from "lucide-react";

import { getBackendHealth } from "../../api/endpoints";

function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);

  return online;
}

/** Shows a banner when the browser is offline or the backend does not answer. */
export function ConnectionBanner() {
  const online = useOnline();

  const health = useQuery({
    queryKey: ["backend-health"],
    queryFn: ({ signal }) => getBackendHealth(signal),
    refetchInterval: (query) => (query.state.status === "error" ? 5_000 : 30_000),
    retry: false,
    enabled: online,
  });

  const message = !online
    ? "You are offline. Search and indexing need a network connection."
    : health.isError
      ? "The CogniSeek server is not reachable. Retrying…"
      : null;

  if (!message) return null;

  return (
    <div
      role="alert"
      className="flex items-center gap-2 bg-amber-100 px-4 py-2 text-sm font-medium text-amber-950"
    >
      <WifiOff aria-hidden="true" className="h-4 w-4" />
      {message}
    </div>
  );
}
