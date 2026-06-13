"use client";

import { useRouter } from "next/navigation";
import { Suspense, useState } from "react";

import { setAccessToken, setRefreshToken, useLogin } from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function LoginForm() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useLogin<Error>({
    mutation: {
      onSuccess: (tokens) => {
        setAccessToken(tokens.accessToken);
        setRefreshToken(tokens.refreshToken);
        router.replace("/dashboard");
      },
    },
  });

  const canSubmit = email.trim() !== "" && password.trim() !== "" && !login.isPending;

  const handleSubmit = () => {
    if (!canSubmit) return;
    login.mutate({ data: { email, password } });
  };

  return (
    <Card className="w-full max-w-sm shadow-sm">
      <CardHeader className="space-y-1 pb-4">
        <div className="text-center mb-2">
          <span className="text-2xl font-bold text-primary tracking-tight">meetgo 관리자</span>
        </div>
        <CardTitle className="text-xl text-center">관리자 로그인</CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
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
              placeholder="admin@meetgo.com"
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
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
