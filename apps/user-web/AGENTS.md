<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# user-web 디자인 시스템

## 컴포넌트 라이브러리

**shadcn/ui** (v4.11.0)를 사용한다. `@gosoom/ui`는 user-web 페이지에서 직접 사용하지 않는다(`@gosoom/ui`는 mobile 전용).

### 설치된 shadcn 컴포넌트

```
src/components/ui/
  button, input, card (CardHeader/CardContent/CardTitle),
  badge, label, textarea, select, separator
```

임포트 경로: `@/components/ui/<name>`

### 추가 컴포넌트

- `src/components/AppHeader.tsx` — 전역 sticky 헤더 (h-14). 역할별 네비게이션, 로그아웃 버튼 포함.
  - `/login`, `/signup` 경로에서는 `null` 반환 (인증 페이지는 자체 전체화면 레이아웃).
  - 고객: 내 요청 / 채팅
  - 고수: 요청 피드 / 내 견적 / 카테고리 / 채팅

## 브랜드 컬러

- Primary: `#1360F5` → CSS 변수 `--primary: oklch(0.506 0.236 264.4)`
- Tailwind 클래스: `bg-primary`, `text-primary`, `border-primary`, `bg-primary/5`

## 페이지 레이아웃 패턴

```tsx
// 기본 페이지 래퍼
<div className="max-w-screen-lg mx-auto p-6">

// 인증 페이지 (AppHeader 없음, 전체화면 중앙 정렬)
<div className="bg-muted min-h-screen flex items-center justify-center">
  <Card className="w-full max-w-md">

// 채팅 상세 (AppHeader h-14 보정 필수)
<div className="h-[calc(100vh-3.5rem)] flex flex-col">
```

## 컴포넌트 사용 패턴

### @gosoom/ui → shadcn 교체 규칙

| 기존 (@gosoom/ui) | 변경 (shadcn/ui) |
|---|---|
| `Button` from `@gosoom/ui` | `Button` from `@/components/ui/button` |
| `Input` from `@gosoom/ui` | `Input` from `@/components/ui/input` |
| `onPress={fn}` | `onClick={fn}` |
| `label="텍스트"` | children으로 직접 전달 |
| `onChangeText={(v)=>set(v)}` | `onChange={(e)=>set(e.target.value)}` |
| `keyboardType="email-address"` | `type="email"` |
| `secureTextEntry` | `type="password"` |

### 상태 배지 패턴

```tsx
import { Badge } from "@/components/ui/badge";

// 요청 상태
const STATUS_VARIANTS = {
  open: "default",      // 파란색 (primary)
  matched: "secondary",
  completed: "outline",
  cancelled: "destructive",
};
<Badge variant={STATUS_VARIANTS[status]}>{status}</Badge>
```

### 카드 목록 패턴

```tsx
<Card className="hover:border-primary transition-colors cursor-pointer">
  <CardContent className="p-4">
    ...
  </CardContent>
</Card>
```

### 폼 패턴

```tsx
<Card>
  <CardHeader><CardTitle>제목</CardTitle></CardHeader>
  <CardContent className="space-y-4">
    <div className="space-y-2">
      <Label htmlFor="field">레이블</Label>
      <Input id="field" ... />
    </div>
    <Button className="w-full">제출</Button>
  </CardContent>
</Card>
```

### Select 패턴 (shadcn)

```tsx
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

<Select onValueChange={(v) => setValue(v)}>
  <SelectTrigger><SelectValue placeholder="선택" /></SelectTrigger>
  <SelectContent>
    <SelectItem value="a">옵션 A</SelectItem>
  </SelectContent>
</Select>
```

## 채팅 메시지 스타일

```tsx
// 내 메시지
"bg-primary text-primary-foreground rounded-br-sm"

// 상대 메시지
"bg-muted text-foreground rounded-bl-sm"
```

## 에러/로딩 상태

```tsx
// 에러 텍스트
<p className="text-sm text-destructive">{error.message}</p>

// 로딩 스켈레톤
<div className="animate-pulse bg-muted rounded h-20" />
```
