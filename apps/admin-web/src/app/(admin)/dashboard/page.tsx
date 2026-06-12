import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SECTIONS = [
  {
    title: "계정관리",
    href: "/users",
    description: "고객 및 고수 계정 조회, 비활성화, 탈퇴 처리 (Epic 6.2)",
  },
  {
    title: "관리자관리",
    href: "/admins",
    description: "관리자 계정 생성 및 관리 (Epic 6.3)",
  },
  {
    title: "요청관리",
    href: "/requests",
    description: "전체 서비스 요청 조회 및 상태 관리 (Epic 6.4)",
  },
  {
    title: "채팅내역",
    href: "/chats",
    description: "매칭된 고객-고수 채팅 내역 열람 (Epic 6.5)",
  },
  {
    title: "카테고리관리",
    href: "/categories",
    description: "서비스 카테고리 추가, 수정, 삭제 (Epic 6.6)",
  },
];

export default function DashboardPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">관리자 콘솔에 오신 것을 환영합니다</h1>
        <p className="text-muted-foreground mt-1">meetgo 서비스 운영 및 관리 기능을 제공합니다.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {SECTIONS.map(({ title, href, description }) => (
          <Link key={title} href={href}>
            <Card className="hover:border-primary transition-colors cursor-pointer h-full">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">{title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
