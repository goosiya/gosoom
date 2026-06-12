import { Link, useRouter } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { tokens } from '@gosoom/ui';

import { useAuth } from '@/features/auth';

type Role = 'customer' | 'pro';

export default function SignupScreen() {
  const { signup } = useAuth();
  const router = useRouter();
  const [role, setRole] = useState<Role>('customer');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [isPending, setIsPending] = useState(false);

  const canSubmit =
    displayName.trim() !== '' &&
    email.trim() !== '' &&
    password !== '' &&
    !isPending;

  const handleSignup = async () => {
    if (!canSubmit) return;
    setErrorMessage('');
    setIsPending(true);
    try {
      await signup(email.trim(), password, displayName.trim(), role);
      router.replace('/(auth)/login');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : '가입에 실패했습니다.');
    } finally {
      setIsPending(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled">
          <View style={styles.card}>
            <Text style={styles.brand}>meetgo</Text>
            <Text style={styles.title}>회원가입</Text>

            {/* 역할 선택 */}
            <View style={styles.field}>
              <Text style={styles.label}>역할</Text>
              <View style={styles.roleRow}>
                {(['customer', 'pro'] as Role[]).map((r) => (
                  <TouchableOpacity
                    key={r}
                    style={[styles.roleBtn, role === r && styles.roleBtnActive]}
                    onPress={() => setRole(r)}
                    accessibilityRole="button">
                    <Text style={[styles.roleBtnText, role === r && styles.roleBtnTextActive]}>
                      {r === 'customer' ? '고객' : '고수'}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>표시명</Text>
              <TextInput
                style={styles.input}
                value={displayName}
                onChangeText={setDisplayName}
                placeholder="홍길동"
                placeholderTextColor={tokens.colors.textSecondary}
                autoCapitalize="words"
                autoCorrect={false}
                textContentType="name"
                autoComplete="name"
                returnKeyType="next"
                editable={!isPending}
              />
            </View>

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
                textContentType="newPassword"
                autoComplete="new-password"
                returnKeyType="done"
                editable={!isPending}
                onSubmitEditing={handleSignup}
              />
            </View>

            {errorMessage ? (
              <Text style={styles.error}>{errorMessage}</Text>
            ) : null}

            <TouchableOpacity
              style={[styles.button, !canSubmit && styles.buttonDisabled]}
              onPress={handleSignup}
              disabled={!canSubmit}
              accessibilityRole="button">
              <Text style={styles.buttonText}>
                {isPending ? '가입 중…' : '가입하기'}
              </Text>
            </TouchableOpacity>

            <View style={styles.footer}>
              <Text style={styles.footerText}>이미 계정이 있으신가요? </Text>
              <Link href="/(auth)/login" style={styles.link}>
                로그인
              </Link>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.backgroundSecondary },
  flex: { flex: 1 },
  container: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: tokens.spacing.lg, paddingVertical: tokens.spacing.xxl },
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
  roleRow: { flexDirection: 'row', gap: tokens.spacing.sm },
  roleBtn: {
    flex: 1,
    height: 44,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  roleBtnActive: {
    borderColor: tokens.colors.primary,
    backgroundColor: tokens.colors.primary + '0D', // 5% 투명도
  },
  roleBtnText: {
    fontSize: tokens.fontSize.base,
    color: tokens.colors.textSecondary,
  },
  roleBtnTextActive: {
    color: tokens.colors.primary,
    fontWeight: tokens.fontWeight.semibold,
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
