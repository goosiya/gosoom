// RN-Web 호환 Button 프리미티브 (AR16).
// react-native 기본 컴포넌트로 작성 → 모바일은 그대로, 웹은 react-native-web 별칭으로 렌더.
import { Pressable, Text, StyleSheet } from 'react-native';

import { tokens } from './tokens';

export interface ButtonProps {
  /** 버튼 라벨 (한국어, NFR2) */
  label: string;
  onPress?: () => void;
  disabled?: boolean;
}

export function Button({ label, onPress, disabled = false }: ButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    backgroundColor: tokens.colors.primary,
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.xl,
    borderRadius: tokens.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  pressed: {
    backgroundColor: tokens.colors.primaryPressed,
  },
  disabled: {
    backgroundColor: tokens.colors.primaryDisabled,
  },
  label: {
    color: tokens.colors.textOnPrimary,
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
  },
});
