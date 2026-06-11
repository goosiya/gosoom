// RN-Web 호환 Input 프리미티브 (AR16).
import { TextInput, StyleSheet } from 'react-native';

import { tokens } from './tokens';

export interface InputProps {
  value: string;
  onChangeText: (text: string) => void;
  /** 플레이스홀더 (한국어, NFR2) */
  placeholder?: string;
  /** 비밀번호 등 가림 입력 */
  secureTextEntry?: boolean;
  /** 키보드 타입 — 이메일 등 */
  keyboardType?: 'default' | 'email-address' | 'numeric';
  editable?: boolean;
}

export function Input({
  value,
  onChangeText,
  placeholder,
  secureTextEntry = false,
  keyboardType = 'default',
  editable = true,
}: InputProps) {
  return (
    <TextInput
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor={tokens.colors.textDisabled}
      secureTextEntry={secureTextEntry}
      keyboardType={keyboardType}
      editable={editable}
      style={[styles.base, !editable && styles.disabled]}
    />
  );
}

const styles = StyleSheet.create({
  base: {
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    fontSize: tokens.fontSize.base,
    color: tokens.colors.text,
    backgroundColor: tokens.colors.background,
  },
  disabled: {
    backgroundColor: tokens.colors.backgroundSecondary,
    color: tokens.colors.textDisabled,
  },
});
