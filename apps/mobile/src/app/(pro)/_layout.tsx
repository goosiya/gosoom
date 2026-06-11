import { useAuth } from '@/features/auth';
import { Redirect, Stack } from 'expo-router';

/** 고수 보호 레이아웃 — 미인증 또는 역할 불일치 시 로그인으로 리다이렉트. */
export default function ProLayout() {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  if (!user || user.role !== 'pro') {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="feed/index" />
      <Stack.Screen name="feed/[id]" options={{ title: '요청 상세', headerShown: true }} />
      <Stack.Screen name="categories/index" options={{ title: '카테고리 설정', headerShown: true }} />
      <Stack.Screen name="quotes/index" options={{ title: '내 견적', headerShown: true }} />
      <Stack.Screen name="chat/index" options={{ title: '채팅 목록', headerShown: true }} />
      <Stack.Screen name="chat/[id]" options={{ title: '채팅', headerShown: true }} />
    </Stack>
  );
}
