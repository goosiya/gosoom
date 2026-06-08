"use client";

// 로그인 화면(AC2/AC3) — useLogin → 토큰 저장(access=메모리, refresh=localStorage) → 홈 이동.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { setAccessToken, setRefreshToken, useLogin } from "@gosoom/api-client";
import { Button, Input } from "@gosoom/ui";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // 가입 직후 진입 시 성공 안내(결정 #7 — 가입→/login).
  const justRegistered = searchParams.get("registered") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin<Error>({
    mutation: {
      onSuccess: (tokens) => {
        // access=메모리, refresh=localStorage(AR10/결정 #4).
        setAccessToken(tokens.accessToken);
        setRefreshToken(tokens.refreshToken);
        router.replace("/");
      },
    },
  });

  const canSubmit = email.trim() !== "" && password !== "" && !login.isPending;

  const handleSubmit = () => {
    if (!canSubmit) return;
    login.mutate({ data: { email, password } });
  };

  return (
    <div className="w-full max-w-sm space-y-5">
      <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
        로그인
      </h1>

      {justRegistered && (
        <p className="text-sm text-green-600" role="status">
          가입이 완료되었습니다. 로그인해 주세요.
        </p>
      )}

      <div className="space-y-3">
        <Input
          value={email}
          onChangeText={setEmail}
          placeholder="이메일"
          keyboardType="email-address"
          editable={!login.isPending}
        />
        <Input
          value={password}
          onChangeText={setPassword}
          placeholder="비밀번호"
          secureTextEntry
          editable={!login.isPending}
        />
      </div>

      {login.error && (
        <p className="text-sm text-red-600" role="alert">
          {login.error.message}
        </p>
      )}

      <Button
        label={login.isPending ? "로그인 중…" : "로그인"}
        onPress={handleSubmit}
        disabled={!canSubmit}
      />

      <p className="text-center text-sm text-zinc-600 dark:text-zinc-400">
        계정이 없으신가요?{" "}
        <Link href="/signup" className="text-blue-600 underline">
          회원가입
        </Link>
      </p>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 p-6 dark:bg-black">
      {/* useSearchParams는 Suspense 경계가 필요(Next App Router 프리렌더 규약). */}
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
