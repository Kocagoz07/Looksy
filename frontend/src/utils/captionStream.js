import { formatApiErrorDetail } from "@/utils/apiError";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export async function fileToResizedBase64(file, maxSide = 768) {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = reject;
      i.src = url;
    });
    const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.85);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export async function streamCaptions(payload, { onDelta, onDone }) {
  const res = await fetch(`${BACKEND_URL}/api/ai/captions/generate`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(formatApiErrorDetail(body.detail));
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop();
    for (const raw of events) {
      if (!raw.startsWith("data: ")) continue;
      const ev = JSON.parse(raw.slice(6));
      if (ev.type === "delta") onDelta(ev.content);
      else if (ev.type === "done") onDone(ev);
      else if (ev.type === "error") throw new Error(ev.detail);
    }
  }
}
