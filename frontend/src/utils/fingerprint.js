/**
 * Device Fingerprinting Utility for Looksy
 * Collects browser/device characteristics for fraud detection
 */

const API = process.env.REACT_APP_BACKEND_URL;

// Generate a hash from a string (simple implementation)
const hashString = async (str) => {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 32);
};

// Get canvas fingerprint
const getCanvasFingerprint = async () => {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Draw some text and shapes
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('Looksy FP', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('Looksy FP', 4, 17);
    
    const dataUrl = canvas.toDataURL();
    return await hashString(dataUrl);
  } catch (e) {
    return 'canvas_error';
  }
};

// Get WebGL fingerprint
const getWebGLFingerprint = async () => {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    
    if (!gl) return 'no_webgl';
    
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    const vendor = debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : 'unknown';
    const renderer = debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : 'unknown';
    
    return await hashString(`${vendor}|${renderer}`);
  } catch (e) {
    return 'webgl_error';
  }
};

// Audio fingerprinting removed: creating an AudioContext without a user
// gesture is blocked by modern browsers, and ScriptProcessorNode is
// deprecated. Canvas + WebGL + hardware + screen + timezone still provide
// strong uniqueness for fraud detection.
const getAudioFingerprint = async () => 'audio_disabled';

// Get installed fonts (limited)
const getInstalledFonts = () => {
  const testFonts = [
    'Arial', 'Verdana', 'Times New Roman', 'Georgia', 'Trebuchet MS',
    'Helvetica', 'Impact', 'Comic Sans MS', 'Courier New', 'Lucida Console'
  ];
  
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const baseFont = 'monospace';
  const testString = 'mmmmmmmmmmlli';
  
  ctx.font = `72px ${baseFont}`;
  const baseWidth = ctx.measureText(testString).width;
  
  const detectedFonts = testFonts.filter(font => {
    ctx.font = `72px '${font}', ${baseFont}`;
    return ctx.measureText(testString).width !== baseWidth;
  });
  
  return detectedFonts.join(',');
};

// Collect all fingerprint data
export const collectFingerprint = async () => {
  const fingerprint = {
    user_agent: navigator.userAgent,
    screen_resolution: `${screen.width}x${screen.height}x${screen.colorDepth}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language || navigator.userLanguage,
    platform: navigator.platform,
    canvas_hash: await getCanvasFingerprint(),
    webgl_hash: await getWebGLFingerprint(),
    audio_hash: await getAudioFingerprint(),
    fonts: getInstalledFonts(),
  };
  
  return fingerprint;
};

// Send fingerprint to server
export const sendFingerprint = async () => {
  try {
    const fingerprint = await collectFingerprint();
    
    const response = await fetch(`${API}/api/security/fingerprint`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(fingerprint),
    });
    
    if (!response.ok) {
      console.warn('Fingerprint recording failed:', response.status);
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error sending fingerprint:', error);
    return null;
  }
};

// Check user's risk score
export const checkRiskScore = async () => {
  try {
    const response = await fetch(`${API}/api/security/my-risk-score`, {
      credentials: 'include',
    });
    
    if (!response.ok) return null;
    
    return await response.json();
  } catch (error) {
    console.error('Error checking risk score:', error);
    return null;
  }
};

export default {
  collectFingerprint,
  sendFingerprint,
  checkRiskScore,
};
