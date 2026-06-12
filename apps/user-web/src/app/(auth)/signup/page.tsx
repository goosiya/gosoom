"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useSignup, type SignupRequestRole } from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<SignupRequestRole>("customer");

  const signup = useSignup<Error>({
    mutation: {
      onSuccess: () => {
        router.replace("/login?registered=1");
      },
    },
  });

  const canSubmit =
    email.trim() !== "" &&
    password !== "" &&
    displayName.trim() !== "" &&
    !signup.isPending;

  const handleSubmit = () => {
    if (!canSubmit) return;
    signup.mutate({ data: { email, password, displayName, role } });
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-muted p-6">
      <Card className="w-full max-w-sm shadow-sm">
        <CardHeader className="space-y-1 pb-4">
          <div className="text-center mb-2">
            <span className="text-2xl font-bold text-primary tracking-tight">meetgo</span>
          </div>
          <CardTitle className="text-xl text-center">회원가입</CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label htmlFor="displayName">표시명</Label>
              <Input
                id="displayName"
                name="displayName"
                autoComplete="name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="홍길동"
                disabled={signup.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">이메일</Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="example@email.com"
                disabled={signup.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">비밀번호</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="8자 이상"
                disabled={signup.isPending}
              />
            </div>

            {/* 역할 선택 */}
            <div className="space-y-2">
              <Label>가입 유형</Label>
              <div className="grid grid-cols-2 gap-3">
                <label
                  className={`flex items-center justify-center gap-2 rounded-md border p-3 cursor-pointer text-sm transition-colors ${
                    role === "customer"
                      ? "border-primary bg-primary/5 text-primary font-medium"
                      : "border-border hover:bg-muted text-muted-foreground"
                  } ${signup.isPending ? "pointer-events-none opacity-50" : ""}`}
                >
                  <input
                    type="radio"
                    name="role"
                    value="customer"
                    checked={role === "customer"}
                    onChange={() => setRole("customer")}
                    className="sr-only"
                  />
                  고객
                </label>
                <label
                  className={`flex items-center justify-center gap-2 rounded-md border p-3 cursor-pointer text-sm transition-colors ${
                    role === "pro"
                      ? "border-primary bg-primary/5 text-primary font-medium"
                      : "border-border hover:bg-muted text-muted-foreground"
                  } ${signup.isPending ? "pointer-events-none opacity-50" : ""}`}
                >
                  <input
                    type="radio"
                    name="role"
                    value="pro"
                    checked={role === "pro"}
                    onChange={() => setRole("pro")}
                    className="sr-only"
                  />
                  고수
                </label>
              </div>
            </div>

            {signup.error && (
              <p className="text-sm text-destructive" role="alert">
                {signup.error.message}
              </p>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={!canSubmit}
            >
              {signup.isPending ? "가입 중…" : "가입하기"}
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            이미 계정이 있으신가요?{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              로그인
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
