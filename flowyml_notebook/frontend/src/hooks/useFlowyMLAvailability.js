import { useState, useEffect } from 'react';

let _cached = null;
let _cachedAt = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function useFlowyMLAvailability() {
  const [flowymlAvailable, setFlowymlAvailable] = useState(_cached ?? false);
  const [loading, setLoading] = useState(_cached === null || Date.now() - _cachedAt > CACHE_TTL);

  useEffect(() => {
    // Re-check if cache has expired or never been set
    if (_cached !== null && Date.now() - _cachedAt < CACHE_TTL) return;
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        _cached = !!data.flowyml_available;
        _cachedAt = Date.now();
        setFlowymlAvailable(_cached);
      })
      .catch(() => {
        _cached = false;
        _cachedAt = Date.now();
        setFlowymlAvailable(false);
      })
      .finally(() => setLoading(false));
  }, []);

  return { flowymlAvailable, loading };
}
