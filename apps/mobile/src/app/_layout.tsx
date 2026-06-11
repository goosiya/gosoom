import '../global.css';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { setStorageBackend } from '@gosoom/api-client';
import { Slot, useRouter, useSegments } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import React, { useEffect, useRef, useState } from 'react';

import { AuthProvider, hydrateMobileStorage, mobileStorageBackend, useAuth } from '@/features/auth';

// 1. storage backend 동기 등록 — 렌더 전 최우선 실행
setStorageBackend(mobileStorageBackend);

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

/** 인증 상태에 따른 화면 분기 가드 (AC5, AC6). auth 확정 후 SplashScreen 해제. */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const segments = useSegments();
  const splashHiddenRef = useRef(false);

  useEffect(() => {
    if (isLoading) return;

    // auth 상태 확정 후 1회만 스플래시 해제 — hydration 직후 흰 화면 방지 (P5)
    if (!splashHiddenRef.current) {
      splashHiddenRef.current = true;
      SplashScreen.hideAsync();
    }

    const inAuthGroup = segments[0] === '(auth)';

    if (!user) {
      // 미인증 → 로그인 화면으로
      if (!inAuthGroup) {
        router.replace('/(auth)/login');
      }
    } else {
      // 인증됨 → 역할별 그룹으로 (AC6)
      if (inAuthGroup) {
        if (user.role === 'customer') {
          router.replace('/(customer)/requests');
        } else {
          router.replace('/(pro)/feed');
        }
      }
    }
  }, [user, isLoading, segments, router]);

  if (isLoading) return null;
  return <>{children}</>;
}

export default function RootLayout() {
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    // 2. SecureStore → 메모리 캐시 복원 (비동기). 성공·실패 모두 isHydrated=true (P1)
    // SplashScreen.hideAsync()는 AuthGate에서 auth 확정 후 호출됨 (P5)
    hydrateMobileStorage().finally(() => {
      setIsHydrated(true);
    });
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider isHydrated={isHydrated}>
        <AuthGate>
          <Slot />
        </AuthGate>
      </AuthProvider>
    </QueryClientProvider>
  );
}
