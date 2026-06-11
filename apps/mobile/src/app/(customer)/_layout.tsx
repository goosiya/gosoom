import { useAuth } from '@/features/auth';
import { Redirect, Stack } from 'expo-router';

/** 고객 보호 레이아웃 — 미인증 또는 역할 불일치 시 로그인으로 리다이렉트. */
export default function CustomerLayout() {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  if (!user || user.role !== 'customer') {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="requests/index" />
      <Stack.Screen name="requests/new" options={{ title: '새 요청 만들기', headerShown: true }} />
      <Stack.Screen name="requests/[id]" options={{ title: '요청 상세', headerShown: true }} />
      <Stack.Screen name="chat/index" options={{ title: '채팅 목록', headerShown: true }} />
      <Stack.Screen name="chat/[id]" options={{ title: '채팅', headerShown: true }} />
    </Stack>
  );
}
