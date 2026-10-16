const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const picUrl = (p) => (!p ? undefined : p.startsWith("http") ? p : `${BACKEND_URL}${p}`);
export const imageUrl = (imageId) => `${BACKEND_URL}/api/images/${imageId}`;

export const timeAgo = (iso) => {
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  const units = [[86400 * 7, "w"], [86400, "d"], [3600, "h"], [60, "m"]];
  for (const [sec, label] of units) if (s >= sec) return `${Math.floor(s / sec)}${label}`;
  return `${s}s`;
};
