---
baseline_commit: efa9596
---

# Story 5.3: 모바일 고수 플로우

Status: done

## Story

As a 고수,
I want 모바일에서 활동 카테고리를 설정하고 요청 피드를 보며 견적을 제안·조회하기를,
so that 휴대폰으로 일감을 찾고 대응할 수 있다.

## Acceptance Criteria

1. **AC1 — 카테고리 설정 (FR9 재사용):** 로그인한 고수가 카테고리 설정 화면을 열면 `useGetProCategories()`로 현재 설정된 카테고리가 선택 상태로 표시되고, `useListCategories({ limit: 100 })`로 전체 카테고리가 선택 가능한 버튼 그리드로 표시된다. 저장 탭 시 `useSetProCategories().mutate({ data: { categoryIds } })`가 호출되고 성공 시 이전 화면으로 이동하며 캐시가 갱신된다.

2. **AC2 — 매칭 요청 피드 (FR10 재사용):** 고수가 피드 화면을 열면 `useListServiceRequestFeed()`로 고수의 카테고리에 매칭된 서비스 요청 목록이 표시된다. `status === 'matched'`인 요청은 비활성(dimmed) 스타일로 표시되고 탭 시 이동이 불가하여 견적 제안이 불가함을 인지할 수 있다(FR10 정합).

3. **AC3 — 견적 제안 (FR11 재사용):** 피드에서 `open` 상태 요청을 탭하면 요청 상세 + 견적 제안 폼 화면으로 이동한다. 가격(숫자)·메시지 입력 후 제안 탭 시 `useCreateServiceRequestQuote().mutate({ requestId, data: { price, message } })`가 호출된다. 이미 견적을 제출한 경우 백엔드 규칙(요청당 1견적)에 따라 거부되고 에러 메시지가 한국어로 표시된다(FR11 정합).

4. **AC4 — 내 견적 목록 (FR12 재사용):** 내 견적 목록 화면에서 `useListMyQuotes()`로 내 견적이 커서 페이지네이션으로 로드되고, 각 항목에 연결된 요청의 지역·상태 및 견적의 금액·상태 배지가 표시된다.

5. **AC5 — NativeWind + 공유 UI (NFR2):** 모든 화면이 NativeWind className과 `@gosoom/ui`의 `Button`·`Input`·`Card`·`tokens`로 렌더링되고, TanStack Query 로딩·에러 상태가 한국어로 표시된다.

## Tasks / Subtasks

> ⚡ **수동 설정 체크포인트:** Story 5.1의 `.env`(`EXPO_PUBLIC_API_URL`) 설정이 유지되어 있어야 한다. Expo Go 실기기 실행 시 LAN IP 또는 배포 Railway URL 필요 (localhost 불가).

- [x] Task 1 — 고수 레이아웃 & 내비게이션 업데이트 (AC1-AC4)
  - [x] 1.1: `apps/mobile/src/app/(pro)/_layout.tsx`의 Stack에 신규 스크린 등록:
    - `categories/index` (options: `{ title: '카테고리 설정', headerShown: true }`)
    - `feed/[id]` (options: `{ title: '요청 상세', headerShown: true }`)
    - `quotes/index` (options: `{ title: '내 견적', headerShown: true }`)
    - `feed/index` — headerShown: false 유지 (커스텀 헤더 사용)
  - [x] 1.2: `apps/mobile/.expo/types/router.d.ts`에 신규 라우트 타입 수동 추가 (Expo dev server 실행 전 typecheck 지원용):
    - `/(pro)/categories` (static)
    - `/(pro)/feed/[id]` (dynamic: `/(pro)/feed/${string}`)
    - `/(pro)/quotes` (static)

- [x] Task 2 — 피드 화면 구현 (AC2)
  - [x] 2.1: `apps/mobile/src/app/(pro)/feed/index.tsx` 플레이스홀더를 실제 구현으로 교체
  - [x] 2.2: `useListServiceRequestFeed({ cursor, limit: 20 })` 훅으로 피드 로드 + 커서 페이지네이션 (processedCursors ref 패턴)
  - [x] 2.3: `useListCategories({ limit: 100 })` 병렬 로드 — 피드 항목에서 `categoryId` → 카테고리명 표시용
  - [x] 2.4: 각 항목 표시: 카테고리명·지역·설명(50자 truncate)·상태 배지
  - [x] 2.5: `status === 'matched'` 항목은 `opacity: 0.4` dimmed 스타일, `onPress` 비활성화 (`'이미 매칭된 요청입니다'` 툴팁 또는 텍스트 표시)
  - [x] 2.6: `status === 'open'` 항목 탭 시 `router.push('/(pro)/feed/[id]' as href, { id })` 이동
  - [x] 2.7: 헤더 우측 버튼 2개: `내 견적`(→ `/(pro)/quotes`) + `카테고리`(→ `/(pro)/categories`)
  - [x] 2.8: 로딩 스켈레톤(3개 Card), 에러 상태, 빈 피드 상태("설정된 카테고리에 맞는 요청이 없습니다") 한국어로 표시
  - [x] 2.9: `SafeAreaView` + `FlatList` (onEndReached + ListFooterComponent 로딩 인디케이터)

- [x] Task 3 — 카테고리 설정 화면 구현 (AC1)
  - [x] 3.1: `apps/mobile/src/app/(pro)/categories/index.tsx` 신규 생성
  - [x] 3.2: `useGetProCategories()` + `useListCategories({ limit: 100 })` 병렬 로드
  - [x] 3.3: 전체 카테고리 버튼 그리드 표시; 현재 설정된 `categoryIds`로 초기 선택 상태 설정
    - `useEffect`로 `proCategories?.categoryIds`가 로드되면 `selectedIds` state 초기화
  - [x] 3.4: 버튼 탭 시 `selectedIds`에서 해당 id 토글 (다중 선택 가능)
  - [x] 3.5: `저장` 버튼: `useSetProCategories().mutate({ data: { categoryIds: selectedIds } })`
  - [x] 3.6: `onSuccess`: `queryClient.invalidateQueries({ queryKey: getGetProCategoriesQueryKey() })` + `router.back()`
  - [x] 3.7: `isPending` 시 저장 버튼 비활성화; 에러 한국어 표시
  - [x] 3.8: `SafeAreaView` + `ScrollView`; 카테고리 로드 실패 시 에러 UI + 재시도 버튼

- [x] Task 4 — 피드 요청 상세 + 견적 제안 화면 (AC3)
  - [x] 4.1: `apps/mobile/src/app/(pro)/feed/[id].tsx` 신규 생성
  - [x] 4.2: `useLocalSearchParams<{ id: string }>()` 로 `id` 추출
  - [x] 4.3: `useGetServiceRequestFeedDetail(id)` + `useListCategories({ limit: 100 })` 병렬 로드
  - [x] 4.4: 요청 상세 표시: 카테고리명·지역·설명·희망일정(있으면)·예산(있으면)·상태 배지
  - [x] 4.5: `request.status === 'open'` 인 경우만 견적 제안 폼 표시:
    - 가격 `Input` (`keyboardType="numeric"`)
    - 메시지 `TextInput` (multiline, `@gosoom/ui` Input이 미지원 시 RN `TextInput` 직접 사용)
    - 제안 버튼
  - [x] 4.6: `request.status !== 'open'` 인 경우 "이미 매칭되었거나 마감된 요청입니다" 안내 텍스트 (폼 숨김)
  - [x] 4.7: 제안 뮤테이션:
    ```typescript
    quoteMutation.mutate({
      requestId: id,
      data: { price: Number(priceInput), message },
    })
    ```
    - `onSuccess`: `router.replace('/(pro)/feed')`
    - `onError`: `error.message` 한국어 표시 (중복 견적 포함)
  - [x] 4.8: 가격 미입력 또는 0 이하 시 클라이언트 검증 (API 호출 없이 경고)
  - [x] 4.9: `isPending` 시 제안 버튼 비활성화
  - [x] 4.10: `SafeAreaView` + `KeyboardAvoidingView` + `ScrollView`

- [x] Task 5 — 내 견적 목록 화면 (AC4)
  - [x] 5.1: `apps/mobile/src/app/(pro)/quotes/index.tsx` 신규 생성
  - [x] 5.2: `useListMyQuotes({ cursor, limit: 20 })` + processedCursors ref 커서 페이지네이션
  - [x] 5.3: 각 항목 표시:
    - `item.serviceRequest?.region` 지역
    - `item.serviceRequest?.status` → 상태 배지 (STATUS_LABELS 매핑)
    - `item.price` 금액 (천 단위 쉼표)
    - `item.status` → 견적 상태 배지 (QUOTE_STATUS_LABELS 매핑)
    - `item.serviceRequest`가 null인 경우 "(삭제된 요청)" 표시
  - [x] 5.4: 로딩 스켈레톤(3개 Card), 에러 상태, 빈 목록("제안한 견적이 없습니다") 표시
  - [x] 5.5: FlatList + onEndReached 무한 스크롤

- [x] Task 6 — 타입체크 및 동작 확인
  - [x] 6.1: `pnpm --filter mobile typecheck` 통과
  - [ ] 6.2: Expo Go 실기기 실행 후 황금 경로 확인 (KTH 직접):
    - 카테고리 설정 → 저장 → 피드로 이동 확인
    - 피드 목록 → open 요청 탭 → 상세 → 견적 제안 확인
    - matched 요청 비활성 표시 확인 (탭 불가)
    - 내 견적 목록 상태 배지 확인
    - 중복 견적 에러 메시지 한국어 확인
  - [ ] 6.3: 빈 목록·로딩·에러 상태 UI 확인 (KTH 직접)

### Review Findings

#### Decision Needed
- [x] [Review][Decision] D1 — completed/cancelled 항목 탭 동작 — **dismissed**: matched만 차단이 스펙 AC2 준수, 현재대로 유지
- [x] [Review][Decision] D2 — NativeWind className 미사용 — **dismissed**: StyleSheet+tokens가 이 프로젝트 모바일 표준으로 인정
- [x] [Review][Patch] P8 — [MEDIUM] 견적 서버 에러 메시지 한국어 fallback 추가 [feed/[id].tsx:62]

#### Patches
- [x] [Review][Patch] P1 — [HIGH] pendingRefresh 레이스: 새로고침 후 피드/견적 동결 [feed/index.tsx:67-79, quotes/index.tsx:68-80]
- [x] [Review][Patch] P2 — [HIGH] 카테고리 0개 선택 저장 무검증 [categories/index.tsx:59-61]
- [x] [Review][Patch] P3 — [HIGH] 피드 상세 에러 화면 탈출 수단 없음 (뒤로가기/재시도 버튼 누락) [feed/[id].tsx:96-103]
- [x] [Review][Patch] P4 — [MEDIUM] id 파라미터 배열 타입 미검증 [feed/[id].tsx:39, 80-83]
- [x] [Review][Patch] P5 — [MEDIUM] 배경 revalidation 시 카테고리 선택 초기화 [categories/index.tsx:37-41]
- [x] [Review][Patch] P6 — [LOW] onError .message undefined 시 빈 에러 표시 [feed/[id].tsx:62, categories/index.tsx:49]
- [x] [Review][Patch] P7 — [LOW] 새로고침 시 빈 상태 UI 깜빡임 [feed/index.tsx, quotes/index.tsx]

#### Deferred
- [x] [Review][Defer] DEF1 — budget=0 표시 — `budget != null` 체크로 0원도 표시됨. API 계약상 0이 "설정 안 함"인지 "0원 예산"인지 불명확 — deferred, pre-existing API contract question
- [x] [Review][Defer] DEF2 — 소수점 금액 검증 없음 [feed/[id].tsx:70-74] — 백엔드 DB schema에 integer 제약 여부에 따라 달라짐 — deferred, depends on backend schema

## Dev Notes

### 현재 모바일 앱 상태 (Story 5.2 완료 기준)

```
apps/mobile/src/app/
├── _layout.tsx              # QueryClientProvider + AuthProvider + AuthGate 완비
├── (auth)/login.tsx         # 로그인 화면 — 완료
├── (auth)/signup.tsx        # 가입 화면 — 완료
├── (customer)/
│   ├── _layout.tsx          # Stack: requests/index, requests/new, requests/[id]
│   └── requests/
│       ├── index.tsx        # 내 요청 목록 — 완료
│       ├── new.tsx          # 요청 생성 — 완료
│       └── [id].tsx         # 요청 상세 + 견적 수락/거절 — 완료
└── (pro)/
    ├── _layout.tsx          # Stack: feed/index 만 등록 — ⬅ Task 1에서 수정
    └── feed/
        └── index.tsx        # 플레이스홀더 — ⬅ Task 2에서 교체
```

**이 스토리에서 신규 생성할 파일:**
```
apps/mobile/src/app/(pro)/
├── categories/
│   └── index.tsx            # 카테고리 설정 화면 (신규)
├── feed/
│   ├── index.tsx            # 피드 목록 (플레이스홀더 교체)
│   └── [id].tsx             # 요청 상세 + 견적 제안 (신규)
└── quotes/
    └── index.tsx            # 내 견적 목록 (신규)
```

### 확립된 인프라 — 재발명 금지

- `useAuth()` — `user`, `isLoading`, `login`, `signup`, `logout` (AuthContext)
- `@gosoom/api-client` — TanStack Query 훅 자동생성, Bearer 인터셉터 내장
- `@gosoom/ui` — `Button`, `Input`, `Card`, `tokens` RN 호환 컴포넌트

### API 훅 사용법 — 절대 직접 fetch 금지

```typescript
// ✅ 고수 관련 import — @gosoom/api-client에서 통합 import
import {
  // 카테고리 설정
  useGetProCategories,
  useSetProCategories,
  getGetProCategoriesQueryKey,
  // 피드
  useListServiceRequestFeed,
  useGetServiceRequestFeedDetail,
  getListServiceRequestFeedQueryKey,
  // 견적
  useCreateServiceRequestQuote,
  useListMyQuotes,
  // 공통
  useListCategories,
} from '@gosoom/api-client';
```

### 훅 시그니처 및 반환 타입

```typescript
// 고수 카테고리 조회
const { data: proCategories } = useGetProCategories<ProCategoriesRead, Error>();
// data.categoryIds: string[]

// 전체 카테고리 목록
const { data: allCategories } = useListCategories<PageCategoryRead, Error>({ limit: 100 });
// data.items: CategoryRead[] — { id: string, name: string }

// 카테고리 설정 뮤테이션
const setMutation = useSetProCategories({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getGetProCategoriesQueryKey() });
      router.back();
    },
    onError: (err) => setErrorMsg(err.message),
  },
});
setMutation.mutate({ data: { categoryIds: selectedIds } }); // categoryIds: string[]

// 피드 목록 (커서 페이지네이션)
const { data, isPending, isError, isFetching } =
  useListServiceRequestFeed<PageServiceRequestRead, Error>({ cursor, limit: 20 });
// data.items: ServiceRequestRead[]  — { id, categoryId, status, region, description, budget?, desiredSchedule?, createdAt }
// data.nextCursor: string | null | undefined

// 피드 요청 상세 (고수용 — useGetServiceRequest 아님!)
const { data: request } = useGetServiceRequestFeedDetail<ServiceRequestRead, Error>(id, {
  query: { enabled: !!id },
});

// 견적 제안 뮤테이션
const quoteMutation = useCreateServiceRequestQuote({
  mutation: {
    onSuccess: () => { router.replace('/(pro)/feed'); },
    onError: (err) => setErrorMsg(err.message),
  },
});
quoteMutation.mutate({ requestId: id, data: { price: Number(priceInput), message } });
// QuoteCreate: { price: number (0 이상), message: string (1~2000자) }

// 내 견적 목록 (커서 페이지네이션)
const { data, isPending, isError, isFetching } =
  useListMyQuotes<PageQuoteListItem, Error>({ cursor, limit: 20 });
// data.items: QuoteListItem[]
// QuoteListItem: { id, price, status, message, createdAt, serviceRequest: ServiceRequestSummary | null }
// ServiceRequestSummary: { id, categoryId, region, description, status }
// data.nextCursor: string | null | undefined
```

### 레이아웃 Stack 스크린 등록 패턴

```typescript
// apps/mobile/src/app/(pro)/_layout.tsx
return (
  <Stack screenOptions={{ headerShown: false }}>
    <Stack.Screen name="feed/index" />
    <Stack.Screen name="feed/[id]" options={{ title: '요청 상세', headerShown: true }} />
    <Stack.Screen name="categories/index" options={{ title: '카테고리 설정', headerShown: true }} />
    <Stack.Screen name="quotes/index" options={{ title: '내 견적', headerShown: true }} />
  </Stack>
);
```

### router.d.ts 수동 업데이트 — 신규 라우트 추가

```typescript
// apps/mobile/.expo/types/router.d.ts — 기존 타입에 추가 (hrefInputParams, hrefOutputParams, href 세 곳 모두)
// 추가할 항목:
// static: { pathname: `/(pro)/categories`; params?: Router.UnknownInputParams; }
// static: { pathname: `/(pro)/quotes`; params?: Router.UnknownInputParams; }
// dynamic href: `/(pro)/feed/${string}${...}`
// dynamic param: { pathname: `/(pro)/feed/[id]`; params?: Router.UnknownInputParams; }
```

### 커서 페이지네이션 패턴 (5.2에서 확립, 동일 패턴 재사용)

```typescript
// processedCursors ref로 race condition 방지 — 5.2 코드리뷰에서 pendingRefresh 가드 추가됨
const [cursor, setCursor] = useState<string | undefined>(undefined);
const [allItems, setAllItems] = useState<ServiceRequestRead[]>([]);
const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
const processedCursors = useRef(new Set<string | undefined>());
const pendingRefresh = useRef(false);

const { data, isPending, isFetching, refetch } = useListServiceRequestFeed({ cursor, limit: 20 });

useEffect(() => {
  if (isFetching) {
    if (pendingRefresh.current) pendingRefresh.current = false;
    return;
  }
  if (!data?.items) return;
  if (pendingRefresh.current) return; // refetch 시작 전 도착한 stale 응답 무시
  if (processedCursors.current.has(cursor)) return;
  processedCursors.current.add(cursor);
  setAllItems((prev) => cursor === undefined ? data.items : [...prev, ...data.items]);
  setNextCursor(data.nextCursor ?? null);
}, [data, cursor, isFetching]);

const handleLoadMore = () => {
  if (nextCursor && !isFetching) setCursor(nextCursor);
};

const handleRefresh = () => {
  pendingRefresh.current = true;
  processedCursors.current = new Set();
  setCursor(undefined);
  setAllItems([]);
  setNextCursor(undefined);
  refetch();
};
```

### @gosoom/ui 컴포넌트 주의사항 (5.1/5.2 디버그 경험)

```typescript
// Button — label prop 사용 (children 아님!)
<Button label="카테고리 저장" onPress={handleSave} disabled={isPending} />

// Input — onChangeText prop (onChange 아님), multiline/numberOfLines 미지원
// → 메시지 등 멀티라인 필드는 RN TextInput 직접 사용
import { TextInput } from 'react-native';
<TextInput
  value={message}
  onChangeText={setMessage}
  multiline
  numberOfLines={4}
  style={styles.messageInput}
  placeholder="메시지를 입력하세요"
  placeholderTextColor={tokens.colors.textSecondary}
/>

// 존재하지 않는 tokens — 사용 금지:
// tokens.fontSize.xs (없음) → 12 하드코딩
// tokens.colors.surface (없음) → tokens.colors.backgroundSecondary

// 사용 가능한 tokens:
// colors: background, backgroundSecondary, text, textSecondary, primary, danger, success, border
// spacing: xs, sm, md, lg, xl
// fontSize: sm, base, lg, xl
// fontWeight: regular, semibold, bold
// radius: sm, md, lg
```

### 상태 배지 매핑 (5.2와 동일, 일관성 유지)

```typescript
const STATUS_LABELS: Record<string, string> = {
  open: '접수됨',
  matched: '매칭됨',
  completed: '완료됨',
  cancelled: '취소됨',
};

const QUOTE_STATUS_LABELS: Record<string, string> = {
  pending: '검토 중',
  accepted: '수락됨',
  rejected: '거절됨',
  closed: '마감됨',
};
```

### matched 요청 비활성 처리 패턴

```typescript
// 피드 FlatList 항목 렌더러
const isMatched = item.status === 'matched';
<TouchableOpacity
  onPress={() => { if (!isMatched) router.push({ pathname: '/(pro)/feed/[id]', params: { id: item.id } }); }}
  activeOpacity={isMatched ? 1 : 0.7}
  style={[styles.card, isMatched && styles.cardDimmed]}
>
  {/* ... 항목 내용 ... */}
  {isMatched && <Text style={styles.matchedNote}>이미 매칭된 요청</Text>}
</TouchableOpacity>

// styles
cardDimmed: { opacity: 0.4 },
```

### SafeAreaView + KeyboardAvoidingView 패턴 (폼 화면 필수)

```typescript
import { KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function FeedDetailScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: tokens.colors.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={{ padding: tokens.spacing.lg }}>
          {/* 요청 상세 + 견적 폼 */}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
```

### 카테고리 이름 조회 패턴

```typescript
// categoryId → 이름 변환 (피드·견적 목록에서 사용)
const categoryMap = useMemo(
  () => new Map((allCategories?.items ?? []).map((c) => [c.id, c.name])),
  [allCategories]
);
const categoryName = categoryMap.get(item.categoryId) ?? item.categoryId;
```

### 금액 포맷

```typescript
// 천 단위 쉼표 표시
const formatPrice = (price: number) => price.toLocaleString('ko-KR') + '원';
```

### 피드 헤더 내비게이션 (커스텀 헤더 — headerShown: false)

feed/index는 headerShown: false이므로 커스텀 헤더 또는 화면 내 버튼으로 내비게이션:

```typescript
// 화면 상단에 버튼 배치
<View style={styles.headerRow}>
  <Text style={styles.screenTitle}>요청 피드</Text>
  <View style={styles.headerButtons}>
    <TouchableOpacity onPress={() => router.push('/(pro)/quotes')}>
      <Text style={styles.headerBtn}>내 견적</Text>
    </TouchableOpacity>
    <TouchableOpacity onPress={() => router.push('/(pro)/categories')}>
      <Text style={styles.headerBtn}>카테고리</Text>
    </TouchableOpacity>
    <TouchableOpacity onPress={logout}>
      <Text style={styles.logoutBtn}>로그아웃</Text>
    </TouchableOpacity>
  </View>
</View>
```

### 주의사항 — 하지 말 것

1. **`packages/api-client/src/generated/` 수정 금지** — Orval 자동생성, 빌드 시 덮어씀
2. **`useGetServiceRequest` 사용 금지** — 고수 피드 상세는 `useGetServiceRequestFeedDetail` 사용 (고수 권한 검사 포함)
3. **채팅 화면 이동 구현 금지** — Story 5.4의 범위
4. **신규 API 엔드포인트 추가 금지** — FR9-12 재사용만, 신규 FR 없음
5. **`(customer)/` 파일 수정 금지** — 이 스토리 범위 아님
6. **견적 상세 화면 구현 금지** — MVP 범위 아님, 목록만 표시
7. **`@react-native-picker/picker` 신규 설치 금지** — 카테고리 선택은 버튼 그리드 방식 사용 (5.2 패턴 동일)

### 웹 참고 파일 (구현 전 반드시 읽기)

```
apps/user-web/src/app/(pro)/categories/page.tsx   — 카테고리 설정 UI 패턴 (다중 선택)
apps/user-web/src/app/(pro)/feed/page.tsx          — 피드 목록 패턴
apps/user-web/src/app/(pro)/feed/[id]/page.tsx     — 요청 상세 + 견적 제안 복합 패턴
apps/user-web/src/app/(pro)/quotes/page.tsx        — 내 견적 목록 + 커서 페이지네이션
```

### 참조 모바일 파일 (패턴 재사용)

```
apps/mobile/src/app/(customer)/_layout.tsx         — Stack 스크린 등록 패턴
apps/mobile/src/app/(customer)/requests/index.tsx  — processedCursors + pendingRefresh 패턴
apps/mobile/src/app/(customer)/requests/new.tsx    — 카테고리 버튼 그리드 선택 패턴
apps/mobile/src/app/(customer)/requests/[id].tsx   — 병렬 훅 + 상태별 조건부 렌더링 패턴
```

## References

- [Source: epics.md#Story 5.3] — 유저 스토리, AC 전문
- [Source: architecture.md] — Expo SDK 55, expo-router, NativeWind v4, @gosoom/ui, api-client 패턴
- [Story 5.1: apps/mobile/src/features/auth/AuthContext.tsx] — useAuth() 인터페이스
- [Story 5.2: apps/mobile/src/app/(customer)/_layout.tsx] — Stack 등록 + router.d.ts 패턴
- [Story 5.2: apps/mobile/src/app/(customer)/requests/index.tsx] — processedCursors + pendingRefresh 확립 패턴
- [Story 5.2: apps/mobile/src/app/(customer)/requests/new.tsx] — 카테고리 버튼 그리드 선택 패턴
- [Source: packages/api-client/src/generated/pros/pros.ts] — useGetProCategories, useSetProCategories, getGetProCategoriesQueryKey
- [Source: packages/api-client/src/generated/service-requests/service-requests.ts] — useListServiceRequestFeed, useGetServiceRequestFeedDetail, getListServiceRequestFeedQueryKey, getGetServiceRequestFeedDetailQueryKey
- [Source: packages/api-client/src/generated/quotes/quotes.ts] — useCreateServiceRequestQuote, useListMyQuotes, getListMyQuotesQueryKey
- [Source: packages/api-client/src/generated/model/proCategoriesRead.ts] — ProCategoriesRead: { categoryIds: string[] }
- [Source: packages/api-client/src/generated/model/quoteCreate.ts] — QuoteCreate: { price: number, message: string }
- [Source: packages/api-client/src/generated/model/serviceRequestSummary.ts] — ServiceRequestSummary: { id, categoryId, region, description, status }
- [Source: packages/ui/src/tokens.ts] — 디자인 토큰 (colors, spacing, fontSize, fontWeight, radius)
- [Source: apps/mobile/.expo/types/router.d.ts] — 현재 라우트 타입 (추가 대상)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Task 6.1 타입에러 수정:
  - `useGetServiceRequestFeedDetail` — `query: { enabled }` 전달 시 `UseQueryOptions` 타입이 `queryKey` 필수 요구 → `enabled` 옵션 제거 (컴포넌트 마운트 시 id 항상 존재)
  - `tokens.fontWeight.bold` 미존재 → `tokens.fontWeight.semibold` 로 교체

### Completion Notes List

- Task 1 (레이아웃/내비게이션): `(pro)/_layout.tsx` Stack에 categories/index, feed/[id], quotes/index 스크린 등록. `router.d.ts`에 3개 신규 라우트 타입 수동 추가.
- Task 2 (피드 화면): 플레이스홀더 교체. processedCursors+pendingRefresh 패턴 커서 페이지네이션. 카테고리명 useMemo 캐싱. matched 항목 opacity:0.4 dimmed + 탭 비활성. 커스텀 헤더(내 견적/카테고리/로그아웃 버튼).
- Task 3 (카테고리 설정): useEffect로 proCategories 로드 시 selectedIds 초기화. 버튼 그리드 다중 선택. invalidateQueries + router.back() 성공 처리.
- Task 4 (피드 상세+견적 제안): KeyboardAvoidingView+ScrollView 폼. open 상태만 폼 표시. 클라이언트 검증(가격>0, 메시지 필수). multiline TextInput 사용.
- Task 5 (내 견적 목록): processedCursors 무한 스크롤. 금액 toLocaleString 포맷. serviceRequest null → "(삭제된 요청)". 이중 배지(견적 상태+요청 상태).
- Task 6: `pnpm --filter mobile typecheck` 통과. 실기기 확인은 KTH 직접 수행 필요.

### File List

- apps/mobile/src/app/(pro)/_layout.tsx (수정)
- apps/mobile/.expo/types/router.d.ts (수정)
- apps/mobile/src/app/(pro)/feed/index.tsx (교체)
- apps/mobile/src/app/(pro)/categories/index.tsx (신규)
- apps/mobile/src/app/(pro)/feed/[id].tsx (신규)
- apps/mobile/src/app/(pro)/quotes/index.tsx (신규)

## Change Log

- 2026-06-11: Story 5.3 생성 (ready-for-dev)
- 2026-06-11: Story 5.3 구현 완료 (Tasks 1-5 완료, Task 6.1 typecheck 통과, 6.2-6.3 실기기 확인 대기)
