"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { setAccessToken, setRefreshToken, useLogin } from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const justRegistered = searchParams.get("registered") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin<Error>({
    mutation: {
      onSuccess: (tokens) => {
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
    <Card className="w-full max-w-sm shadow-sm">
      <CardHeader className="space-y-1 pb-4">
        <div className="text-center mb-2">
          <span className="text-2xl font-bold text-primary tracking-tight">gosoom</span>
        </div>
        <CardTitle className="text-xl text-center">로그인</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {justRegistered && (
          <p className="text-sm text-green-600 text-center bg-green-50 rounded-md py-2 px-3" role="status">
            가입이 완료되었습니다. 로그인해 주세요.
          </p>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label htmlFor="email">이메일</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="example@email.com"
              disabled={login.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">비밀번호</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={login.isPending}
            />
          </div>

          {login.error && (
            <p className="text-sm text-destructive" role="alert">
              {login.error.message}
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            disabled={!canSubmit}
          >
            {login.isPending ? "로그인 중…" : "로그인"}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          계정이 없으신가요?{" "}
          <Link href="/signup" className="text-primary hover:underline font-medium">
            회원가입
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-muted p-6">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
