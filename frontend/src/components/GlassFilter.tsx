export function GlassFilter() {
  return (
    <svg className="hidden">
      <defs>
        <filter
          id="radio-glass"
          x="0%"
          y="0%"
          width="100%"
          height="100%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.45 0.45"
            numOctaves="2"
            seed="1"
            result="turbulence"
          />
          <feGaussianBlur in="turbulence" stdDeviation="1.5" result="blurredNoise" />
          <feDisplacementMap
            in="SourceGraphic"
            in2="blurredNoise"
            scale="10"
            xChannelSelector="R"
            yChannelSelector="B"
            result="displaced"
          />
          <feComposite in="displaced" in2="displaced" operator="over" />
        </filter>
      </defs>
    </svg>
  )
}
