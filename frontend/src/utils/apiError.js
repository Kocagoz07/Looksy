export function formatApiErrorDetail(detail, fallback = "Something went wrong. Please try again.") {
  if (detail == null) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg.replace(/^Value error, /, "") : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const apiErrorMessage = (err, fallback) =>
  formatApiErrorDetail(err?.response?.data?.detail, fallback || err?.message);
