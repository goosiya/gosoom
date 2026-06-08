// RN-Web 호환 Button 프리미티브 (AR16).
// react-native 기본 컴포넌트로 작성 → 모바일은 그대로, 웹은 react-native-web 별칭으로 렌더.
// 이 프리미티브가 user-web과 mobile 양쪽에서 렌더되는 것이 Story 1.1의 검증 기준이다.
import { Pressable, Text, StyleSheet } from 'react-native';

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
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    backgroundColor: '#1d4ed8',
  },
  disabled: {
    backgroundColor: '#94a3b8',
  },
  label: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
  },
});
