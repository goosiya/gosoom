// React Native StyleSheet용 브랜드 디자인 토큰.
// CSS 변수 미사용 (RN은 CSS 파싱 불가) — StyleSheet.create() 에서만 참조.
export const tokens = {
  colors: {
    primary: '#1360F5',
    primaryPressed: '#0F4FCC',
    primaryDisabled: '#94A3B8',
    background: '#FFFFFF',
    backgroundSecondary: '#F8FAFC',
    border: '#E2E8F0',
    text: '#0F172A',
    textSecondary: '#64748B',
    textDisabled: '#94A3B8',
    textOnPrimary: '#FFFFFF',
    danger: '#DC2626',
    success: '#16A34A',
  },
  radius: {
    sm: 6,
    md: 8,
    lg: 12,
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
  },
  fontSize: {
    sm: 14,
    base: 16,
    lg: 18,
  },
  fontWeight: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
  },
} as const;
