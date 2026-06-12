import { Link } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { tokens } from '@gosoom/ui';

import { useAuth } from '@/features/auth';

export default function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isPending, setIsPending] = useState(false);

  const canSubmit = email.trim() !== '' && password !== '' && !isPending;

  const handleLogin = async () => {
    if (!canSubmit) return;
    setErrorMessage('');
    setIsPending(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : '로그인에 실패했습니다.');
    } finally {
      setIsPending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <View style={styles.card}>
          <Text style={styles.brand}>meetgo</Text>
          <Text style={styles.title}>로그인</Text>

          <View style={styles.field}>
            <Text style={styles.label}>이메일</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="example@email.com"
              placeholderTextColor={tokens.colors.textSecondary}
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
              textContentType="emailAddress"
              autoComplete="email"
              returnKeyType="next"
              editable={!isPending}
            />
          </View>

          <View style={styles.field}>
            <Text style={styles.label}>비밀번호</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="••••••••"
              placeholderTextColor={tokens.colors.textSecondary}
              secureTextEntry
              textContentType="password"
              autoComplete="current-password"
              returnKeyType="done"
              editable={!isPending}
              onSubmitEditing={handleLogin}
            />
          </View>

          {errorMessage ? (
            <Text style={styles.error}>{errorMessage}</Text>
          ) : null}

          <TouchableOpacity
            style={[styles.button, !canSubmit && styles.buttonDisabled]}
            onPress={handleLogin}
            disabled={!canSubmit}
            accessibilityRole="button">
            <Text style={styles.buttonText}>
              {isPending ? '로그인 중…' : '로그인'}
            </Text>
          </TouchableOpacity>

          <View style={styles.footer}>
            <Text style={styles.footerText}>계정이 없으신가요? </Text>
            <Link href="/(auth)/signup" style={styles.link}>
              회원가입
            </Link>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.backgroundSecondary },
  container: { flex: 1, justifyContent: 'center', paddingHorizontal: tokens.spacing.lg },
  card: {
    backgroundColor: tokens.colors.background,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.xxl,
    gap: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
  brand: {
    fontSize: 24,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.primary,
    textAlign: 'center',
    marginBottom: tokens.spacing.xs,
  },
  title: {
    fontSize: tokens.fontSize.lg,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
    textAlign: 'center',
    marginBottom: tokens.spacing.sm,
  },
  field: { gap: tokens.spacing.xs },
  label: {
    fontSize: tokens.fontSize.sm,
    fontWeight: tokens.fontWeight.medium,
    color: tokens.colors.text,
  },
  input: {
    height: 44,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.md,
    fontSize: tokens.fontSize.base,
    color: tokens.colors.text,
    backgroundColor: tokens.colors.background,
  },
  error: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.danger,
  },
  button: {
    height: 48,
    backgroundColor: tokens.colors.primary,
    borderRadius: tokens.radius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: tokens.spacing.xs,
  },
  buttonDisabled: { backgroundColor: tokens.colors.primaryDisabled },
  buttonText: {
    color: tokens.colors.textOnPrimary,
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
  },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: tokens.spacing.xs },
  footerText: { fontSize: tokens.fontSize.sm, color: tokens.colors.textSecondary },
  link: { fontSize: tokens.fontSize.sm, color: tokens.colors.primary, fontWeight: tokens.fontWeight.medium },
});
