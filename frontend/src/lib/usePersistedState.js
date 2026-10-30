import { useEffect, useState } from "react";

export function loadPersisted(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function savePersisted(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // localStorage를 못 쓰는 환경(프라이빗 모드 등)이면 그냥 이번 세션 동안만 유지된다
  }
}

export function usePersistedState(key, initialValue) {
  const [state, setState] = useState(() => loadPersisted(key, initialValue));

  useEffect(() => {
    savePersisted(key, state);
  }, [key, state]);

  return [state, setState];
}
