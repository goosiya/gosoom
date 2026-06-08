"use client";

// 회원가입 화면(AC2/AC3) — 역할(customer|pro)·표시명·이메일·비밀번호 입력 → useSignup.
// 성공 시 자동 로그인하지 않고 /login으로 이동(결정 #7). 입력은 @gosoom/ui 재사용.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useSignup, type SignupRequestRole } from "@gosoom/api-client";
import { Button, Input } from "@gosoom/ui";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<SignupRequestRole>("customer");

  // TError=Error: 인터셉터가 한국어 message를 가진 Error를 throw → error.message로 노출(AC3).
  const signup = useSignup<Error>({
    mutation: {
      onSuccess: () => {
        // 가입과 로그인 경계를 명확히(결정 #7) — 성공 메시지와 함께 로그인 화면으로.
        router.replace("/login?registered=1");
      },
    },
  });

  // 클라이언트 최소 검증만(빈 값 비활성) — 상세 검증은 백엔드 422 신뢰(중복 로직 금지).
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
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 p-6 dark:bg-black">
      <div className="w-full max-w-sm space-y-5">
        <h1 className="text-2xl font-semibold text-black dark:text-zinc-50">
          회원가입
        </h1>

        <div className="space-y-3">
          <Input
            value={displayName}
            onChangeText={setDisplayName}
            placeholder="표시명"
            editable={!signup.isPending}
          />
          <Input
            value={email}
            onChangeText={setEmail}
            placeholder="이메일"
            keyboardType="email-address"
            editable={!signup.isPending}
          />
          <Input
            value={password}
            onChangeText={setPassword}
            placeholder="비밀번호 (8자 이상)"
            secureTextEntry
            editable={!signup.isPending}
          />
        </div>

        {/* 역할 선택 — @gosoom/ui에 선택 프리미티브가 없어 네이티브 라디오로 구현(user-web 전용). */}
        <fieldset className="flex gap-6" disabled={signup.isPending}>
          <legend className="mb-2 text-sm text-zinc-600 dark:text-zinc-400">
            가입 유형
          </legend>
          <label className="flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
            <input
              type="radio"
              name="role"
              value="customer"
              checked={role === "customer"}
              onChange={() => setRole("customer")}
            />
            고객
          </label>
          <label className="flex items-center gap-2 text-zinc-800 dark:text-zinc-200">
            <input
              type="radio"
              name="role"
              value="pro"
              checked={role === "pro"}
              onChange={() => setRole("pro")}
            />
            고수
          </label>
        </fieldset>

        {signup.error && (
          <p className="text-sm text-red-600" role="alert">
            {signup.error.message}
          </p>
        )}

        <Button
          label={signup.isPending ? "가입 중…" : "가입하기"}
          onPress={handleSubmit}
          disabled={!canSubmit}
        />

        <p className="text-center text-sm text-zinc-600 dark:text-zinc-400">
          이미 계정이 있으신가요?{" "}
          <Link href="/login" className="text-blue-600 underline">
            로그인
          </Link>
        </p>
      </div>
    </main>
  );
}
