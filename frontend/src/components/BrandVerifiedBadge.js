/**
 * Brand Verified Badge Component
 * A sleek, metallic gold "B" integrated with a checkmark
 * Displayed next to verified brand partner usernames
 */
export default function BrandVerifiedBadge({ size = "md", className = "" }) {
  // Size mappings
  const sizeMap = {
    xs: { width: 14, height: 14 },
    sm: { width: 18, height: 18 },
    md: { width: 22, height: 22 },
    lg: { width: 28, height: 28 },
    xl: { width: 36, height: 36 }
  };

  const { width, height } = sizeMap[size] || sizeMap.md;

  return (
    <svg
      data-testid="brand-verified-badge"
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`inline-block ${className}`}
      style={{ verticalAlign: 'middle' }}
      aria-label="Brand Verified"
      role="img"
    >
      {/* Gradient definitions for metallic gold effect */}
      <defs>
        <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F7E98E" />
          <stop offset="25%" stopColor="#D4AF37" />
          <stop offset="50%" stopColor="#FFD700" />
          <stop offset="75%" stopColor="#D4AF37" />
          <stop offset="100%" stopColor="#C5A028" />
        </linearGradient>
        <linearGradient id="goldHighlight" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#FFF8DC" />
          <stop offset="100%" stopColor="#D4AF37" />
        </linearGradient>
        <filter id="goldShadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0.5" stdDeviation="0.5" floodColor="#B8860B" floodOpacity="0.4"/>
        </filter>
      </defs>
      
      {/* Background circle with subtle shadow */}
      <circle
        cx="12"
        cy="12"
        r="10"
        fill="url(#goldGradient)"
        filter="url(#goldShadow)"
      />
      
      {/* Inner highlight ring for metallic depth */}
      <circle
        cx="12"
        cy="12"
        r="8.5"
        fill="none"
        stroke="url(#goldHighlight)"
        strokeWidth="0.5"
        opacity="0.6"
      />
      
      {/* Letter B - stylized */}
      <path
        d="M8 6.5V17.5H11.5C13.5 17.5 15 16.5 15 15C15 13.8 14.2 13 13 12.8V12.7C13.8 12.5 14.5 11.7 14.5 10.5C14.5 9 13.2 8 11.2 8H8V6.5ZM10 9.5H11C11.8 9.5 12.3 9.9 12.3 10.6C12.3 11.3 11.8 11.7 11 11.7H10V9.5ZM10 13.1H11.2C12.1 13.1 12.7 13.6 12.7 14.4C12.7 15.2 12.1 15.7 11.2 15.7H10V13.1Z"
        fill="#1A1A1A"
      />
      
      {/* Checkmark integrated at bottom-right */}
      <circle cx="17.5" cy="17.5" r="5" fill="#1A1A1A" />
      <circle cx="17.5" cy="17.5" r="4" fill="url(#goldGradient)" />
      <path
        d="M15.5 17.5L16.8 18.8L19.5 16"
        stroke="#1A1A1A"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
