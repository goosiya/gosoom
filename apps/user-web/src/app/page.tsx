"use client";

// 공개 메인 랜딩 페이지(`/`). 미인증 방문자에게 노출되며, 로그인/회원가입으로 연결.
// 이미 인증된 사용자는 대시보드(/dashboard)로 리다이렉트.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useSyncExternalStore } from "react";
import {
  Check,
  ClipboardList,
  MessageSquare,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
} from "lucide-react";

import { isAuthenticated } from "@gosoom/api-client";

import { Button } from "@/components/ui/button";

// AuthGuard와 동일한 외부 스토어 구독 패턴 — 토큰 스토어는 변경 이벤트를 발행하지 않음.
const subscribe = () => () => {};
const getServerSnapshot = () => false;

const FEATURES = [
  {
    icon: Search,
    title: "원하는 서비스를 요청",
    description: "필요한 일을 등록하면 가까운 고수들이 확인합니다.",
  },
  {
    icon: ClipboardList,
    title: "맞춤 견적 비교",
    description: "여러 고수의 견적을 한눈에 비교하고 선택하세요.",
  },
  {
    icon: MessageSquare,
    title: "실시간 채팅",
    description: "수락한 견적의 고수와 바로 대화하며 일정을 조율하세요.",
  },
  {
    icon: ShieldCheck,
    title: "검증된 고수",
    description: "카테고리별 전문 고수가 안전하게 서비스를 제공합니다.",
  },
];

const ROLES = [
  {
    badge: "고객이라면",
    title: "원하는 서비스를 손쉽게 찾아보세요",
    points: [
      "몇 번의 클릭으로 서비스 요청 등록",
      "받은 견적을 비교하고 합리적으로 선택",
      "채팅으로 세부 사항을 직접 조율",
    ],
  },
  {
    badge: "고수라면",
    title: "내 전문성으로 새로운 고객을 만나세요",
    points: [
      "관심 카테고리의 요청을 실시간 피드로 확인",
      "맞춤 견적을 제안하고 매칭 성사",
      "고객과 직접 소통하며 신뢰 구축",
    ],
  },
];

export default function LandingPage() {
  const router = useRouter();
  const authorized = useSyncExternalStore(
    subscribe,
    isAuthenticated,
    getServerSnapshot,
  );

  useEffect(() => {
    if (authorized) {
      router.replace("/dashboard");
    }
  }, [authorized, router]);

  // 인증된 사용자는 대시보드로 이동 중 — 랜딩 콘텐츠 깜빡임 방지.
  if (authorized) return null;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* 상단 네비게이션 */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-screen-lg items-center justify-between px-4 sm:px-6">
          <Link href="/" className="text-xl font-bold tracking-tight text-primary">
            meetgo
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm">
              <Link href="/login">로그인</Link>
            </Button>
            <Button asChild size="sm">
              <Link href="/signup">회원가입</Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* 히어로 섹션 — isolate로 독립 스택 컨텍스트(음수 z가 조상 배경 뒤로 숨는 것 방지) */}
        <section className="relative isolate overflow-hidden">
          {/* 장식용 배경 — 점 격자 패턴 + 브랜드 컬러 블롭 + 그라데이션 */}
          <div aria-hidden className="pointer-events-none absolute inset-0 z-0">
            <div className="absolute inset-0 bg-gradient-to-b from-primary/10 via-background to-background" />
            {/* SVG 점 격자 — 중앙에서 바깥으로 페이드(마스크)되어 은은한 텍스처 */}
            <svg
              className="absolute inset-0 h-full w-full text-primary/40 [mask-image:radial-gradient(ellipse_60%_60%_at_50%_40%,black,transparent)] [-webkit-mask-image:radial-gradient(ellipse_60%_60%_at_50%_40%,black,transparent)]"
              aria-hidden
            >
              <defs>
                <pattern
                  id="hero-dots"
                  width="22"
                  height="22"
                  patternUnits="userSpaceOnUse"
                >
                  <circle cx="1.5" cy="1.5" r="1.5" fill="currentColor" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill="url(#hero-dots)" />
            </svg>
            <div className="absolute -right-20 -top-24 h-80 w-80 rounded-full bg-primary/25 blur-3xl" />
            <div className="absolute -left-24 top-40 h-72 w-72 rounded-full bg-primary/20 blur-3xl" />
          </div>

          <div className="relative z-10 mx-auto max-w-screen-lg px-4 py-16 sm:px-6 sm:py-20 lg:py-28">
            <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-8">
              {/* 좌: 텍스트 */}
              <div className="text-center lg:text-left">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-4 py-1.5 text-sm font-medium text-primary">
                  <Sparkles className="h-3.5 w-3.5" />
                  고객·고수 서비스 매칭 플랫폼
                </span>
                <h1 className="mt-6 text-4xl font-bold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
                  필요한 서비스,
                  <br className="hidden sm:block" />{" "}
                  <span className="text-primary">meetgo</span>에서 연결하세요
                </h1>
                <p className="mx-auto mt-6 max-w-xl text-base text-muted-foreground sm:text-lg lg:mx-0">
                  요청을 등록하면 검증된 고수들의 맞춤 견적을 받아볼 수 있어요.
                  비교하고, 채팅하고, 바로 시작하세요.
                </p>
                <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start">
                  <Button asChild size="lg" className="w-full sm:w-auto">
                    <Link href="/signup">무료로 시작하기</Link>
                  </Button>
                  <Button asChild size="lg" variant="outline" className="w-full sm:w-auto">
                    <Link href="/login">로그인</Link>
                  </Button>
                </div>
                <div className="mt-8 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-muted-foreground lg:justify-start">
                  {["검증된 고수", "무료 견적", "실시간 채팅"].map((item) => (
                    <span key={item} className="flex items-center gap-1.5">
                      <Check className="h-4 w-4 text-primary" />
                      {item}
                    </span>
                  ))}
                </div>
              </div>

              {/* 우: 앱 미리보기 비주얼 */}
              <div className="relative mx-auto w-full max-w-md lg:max-w-none">
                {/* 뒤 장식 글로우 */}
                <div
                  aria-hidden
                  className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-tr from-primary/20 via-primary/5 to-transparent blur-2xl"
                />

                {/* 메인 요청 카드 */}
                <div className="rounded-2xl border border-border bg-background p-5 shadow-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                        <Sparkles className="h-5 w-5" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-foreground">이사·청소 도움</p>
                        <p className="text-xs text-muted-foreground">서울 강남구 · 오늘</p>
                      </div>
                    </div>
                    <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                      모집중
                    </span>
                  </div>

                  <div className="mt-4 space-y-2">
                    <div className="h-2.5 w-full rounded-full bg-muted" />
                    <div className="h-2.5 w-2/3 rounded-full bg-muted" />
                  </div>

                  {/* 도착한 견적 미리보기 */}
                  <div className="mt-4 rounded-xl border border-primary/20 bg-primary/5 p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
                          김
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-foreground">김고수 고수</p>
                          <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                            <Star className="h-3 w-3 fill-primary text-primary" />
                            4.9 · 후기 128
                          </span>
                        </div>
                      </div>
                      <p className="text-sm font-bold text-primary">120,000원</p>
                    </div>
                  </div>
                </div>

                {/* 플로팅 채팅 버블 */}
                <div className="absolute -bottom-5 -left-4 flex items-center gap-2 rounded-2xl border border-border bg-background px-3 py-2 shadow-lg sm:-left-6">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <MessageSquare className="h-4 w-4" />
                  </span>
                  <span className="text-xs font-medium text-foreground">
                    “내일 오전 가능해요!”
                  </span>
                </div>

                {/* 플로팅 매칭 배지 */}
                <div className="absolute -right-2 -top-4 rounded-full bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground shadow-lg sm:-right-4">
                  매칭 완료 🎉
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 기능 소개 섹션 */}
        <section className="border-t border-border bg-muted/30">
          <div className="mx-auto max-w-screen-lg px-4 py-16 sm:px-6 sm:py-20">
            <div className="mx-auto max-w-2xl text-center">
              <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                이렇게 이용해요
              </h2>
              <p className="mt-3 text-sm text-muted-foreground sm:text-base">
                복잡한 과정 없이, 요청부터 매칭까지 한 곳에서.
              </p>
            </div>
            <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map((feature) => {
                const Icon = feature.icon;
                return (
                  <div
                    key={feature.title}
                    className="rounded-xl border border-border bg-background p-6 transition-colors hover:border-primary"
                  >
                    <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 text-primary ring-1 ring-primary/10">
                      <Icon className="h-5 w-5" />
                    </div>
                    <h3 className="mt-4 text-base font-semibold text-foreground">
                      {feature.title}
                    </h3>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {feature.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 역할 소개 섹션 */}
        <section className="mx-auto max-w-screen-lg px-4 py-16 sm:px-6 sm:py-20">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {ROLES.map((role) => (
              <div
                key={role.badge}
                className="flex flex-col rounded-2xl border border-border bg-background p-8"
              >
                <span className="self-start rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                  {role.badge}
                </span>
                <h3 className="mt-4 text-xl font-bold text-foreground sm:text-2xl">
                  {role.title}
                </h3>
                <ul className="mt-6 space-y-3">
                  {role.points.map((point) => (
                    <li key={point} className="flex items-start gap-3 text-sm text-muted-foreground">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        {/* 마무리 CTA 섹션 */}
        <section className="border-t border-border bg-primary">
          <div className="mx-auto max-w-screen-lg px-4 py-16 text-center sm:px-6 sm:py-20">
            <h2 className="text-2xl font-bold tracking-tight text-primary-foreground sm:text-3xl">
              지금 meetgo와 함께 시작하세요
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm text-primary-foreground/80 sm:text-base">
              고객도 고수도, 단 몇 분이면 충분합니다.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button asChild size="lg" variant="secondary" className="w-full sm:w-auto">
                <Link href="/signup">회원가입</Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="outline"
                className="w-full border-primary-foreground/30 bg-transparent text-primary-foreground hover:bg-primary-foreground/10 hover:text-primary-foreground sm:w-auto"
              >
                <Link href="/login">로그인</Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* 푸터 */}
      <footer className="border-t border-border bg-background">
        <div className="mx-auto flex max-w-screen-lg flex-col items-center justify-between gap-2 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:px-6">
          <span className="font-bold text-primary">meetgo</span>
          <span>© 2026 meetgo. 고객·고수 서비스 매칭 플랫폼.</span>
        </div>
      </footer>
    </div>
  );
}
