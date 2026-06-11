import { useQueryClient } from '@tanstack/react-query';
import {
  clearTokens,
  getReadMeQueryKey,
  isAuthenticated,
  setAccessToken,
  setAuthFailureHandler,
  setRefreshToken,
  useLogin,
  useReadMe,
  useSignup,
} from '@gosoom/api-client';
import { router } from 'expo-router';
import React, { createContext, useContext, useEffect, useReducer } from 'react';

interface AuthUser {
  id: string;
  role: 'customer' | 'pro';
  displayName: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (
    email: string,
    password: string,
    displayName: string,
    role: 'customer' | 'pro',
  ) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: React.ReactNode;
  /** 루트 레이아웃에서 SecureStore 수화 완료 후 true로 전달. */
  isHydrated: boolean;
}

type AuthState = {
  user: AuthUser | null;
  isLoading: boolean;
  shouldFetchMe: boolean;
};

type AuthAction =
  | { type: 'HYDRATE_NO_TOKEN' }
  | { type: 'HYDRATE_HAS_TOKEN' }
  | { type: 'ME_SUCCESS'; user: AuthUser }
  | { type: 'ME_FAILURE' }
  | { type: 'LOGIN_TRIGGER' }
  | { type: 'LOGOUT' };

const initialState: AuthState = { user: null, isLoading: true, shouldFetchMe: false };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'HYDRATE_NO_TOKEN':
      return { ...state, isLoading: false };
    case 'HYDRATE_HAS_TOKEN':
      return { ...state, shouldFetchMe: true };
    case 'ME_SUCCESS':
      return { user: action.user, isLoading: false, shouldFetchMe: false };
    case 'ME_FAILURE':
      return { user: null, isLoading: false, shouldFetchMe: false };
    case 'LOGIN_TRIGGER':
      return { ...state, shouldFetchMe: true };
    case 'LOGOUT':
      return { user: null, isLoading: false, shouldFetchMe: false };
    default:
      return state;
  }
}

export function AuthProvider({ children, isHydrated }: AuthProviderProps) {
  const queryClient = useQueryClient();
  const [{ user, isLoading, shouldFetchMe }, dispatch] = useReducer(authReducer, initialState);

  // 수화 완료 시: 기존 세션 복원 여부 확인
  useEffect(() => {
    if (!isHydrated) return;
    if (isAuthenticated()) {
      dispatch({ type: 'HYDRATE_HAS_TOKEN' });
    } else {
      dispatch({ type: 'HYDRATE_NO_TOKEN' });
    }
  }, [isHydrated]);

  const { data: meData, isError: meIsError } = useReadMe({
    query: {
      queryKey: getReadMeQueryKey(),
      enabled: shouldFetchMe,
      retry: false,
    },
  });

  // /me 성공 → user 상태 갱신
  useEffect(() => {
    if (!meData) return;

    // userRole 유효성 검사 — 비표준 값이면 미인증으로 처리 (P4)
    const validRoles = ['customer', 'pro'] as const;
    const role = validRoles.includes(meData.userRole as 'customer' | 'pro')
      ? (meData.userRole as 'customer' | 'pro')
      : null;

    if (!role) {
      dispatch({ type: 'ME_FAILURE' });
      return;
    }

    dispatch({
      type: 'ME_SUCCESS',
      user: { id: meData.id, role, displayName: meData.displayName },
    });
  }, [meData]);

  // /me 실패(네트워크 오류 등) → 미인증으로 처리
  useEffect(() => {
    if (!meIsError || !shouldFetchMe) return;
    dispatch({ type: 'ME_FAILURE' });
  }, [meIsError, shouldFetchMe]);

  // refresh 실패 → 로그아웃 + 로그인 화면으로 이동 (인터셉터에서 호출)
  // 언마운트 시 no-op으로 교체 — stale 클로저 방지 (P6)
  useEffect(() => {
    setAuthFailureHandler(() => {
      dispatch({ type: 'ME_FAILURE' });
      router.replace('/(auth)/login');
    });
    return () => {
      setAuthFailureHandler(() => {});
    };
  }, []);

  const { mutateAsync: loginMutate } = useLogin();
  const { mutateAsync: signupMutate } = useSignup();

  const login = async (email: string, password: string): Promise<void> => {
    const tokens = await loginMutate({ data: { email, password } });
    setAccessToken(tokens.accessToken);
    setRefreshToken(tokens.refreshToken);
    // 이전 세션 /me 캐시 제거 — 재로그인 시 stale 데이터 트리거 방지 (P3)
    queryClient.resetQueries({ queryKey: getReadMeQueryKey() });
    dispatch({ type: 'LOGIN_TRIGGER' });
  };

  const signup = async (
    email: string,
    password: string,
    displayName: string,
    role: 'customer' | 'pro',
  ): Promise<void> => {
    await signupMutate({ data: { email, password, displayName, role } });
  };

  const logout = async (): Promise<void> => {
    clearTokens();
    // /me 캐시 제거 — 재로그인 시 이전 사용자 정보 노출 방지 (P3)
    queryClient.resetQueries({ queryKey: getReadMeQueryKey() });
    dispatch({ type: 'LOGOUT' });
    router.replace('/(auth)/login');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth는 AuthProvider 내부에서만 사용 가능합니다.');
  return ctx;
}
