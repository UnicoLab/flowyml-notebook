import { useState, useEffect } from 'react';

let _cached = null;

export function useFlowyMLAvailability() {
  const [flowymlAvailable, setFlowymlAvailable] = useState(_cached ?? false);
  const [loading, setLoading] = useState(_cached === null);

  useEffect(() => {
    if (_cached !== null) return;
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        _cached = !!data.flowyml_available;
        setFlowymlAvailable(_cached);
      })
      .catch(() => {
        _cached = false;
        setFlowymlAvailable(false);
      })
      .finally(() => setLoading(false));
  }, []);

  return { flowymlAvailable, loading };
}
