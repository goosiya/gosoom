---
baseline_commit: 3dc7151f1c51ec31f667d85d06502c51f283d35
---

# Story 5.2: 모바일 고객 플로우

Status: done

## Story

As a 고객,
I want 모바일에서 서비스 요청을 올리고 견적을 비교·수락/거절하기를,
so that 이동 중에도 거래를 진행할 수 있다.

## Acceptance Criteria

1. **AC1 — 내 요청 목록 (FR5·FR6 재사용):** 로그인한 고객이 요청 목록 화면을 열면 `GET /api/v1/service-requests`(내 요청 필터)가 호출되어 요청 목록이 상태 배지와 함께 표시되고, 항목 탭 시 상세 화면으로 이동한다.

2. **AC2 — 요청 생성 (FR5 재사용):** 요청 생성 화면에서 카테고리·지역·설명(·희망일정·예산 선택) 입력 후 제출하면 `POST /api/v1/service-requests`가 호출되고 성공 시 요청 목록 화면으로 이동하며 목록이 갱신된다.

3. **AC3 — 상태 관리 (FR7 재사용):** 요청 상세 화면에서 `open` 상태면 취소 버튼, `matched` 상태면 완료 버튼이 표시되고, 탭 시 `PATCH /api/v1/service-requests/{id}` status update가 호출되어 화면이 갱신된다.

4. **AC4 — 견적 비교 (FR8 재사용):** 요청 상세 화면에서 `open`/`matched` 상태 요청에 대해 `GET /api/v1/service-requests/{id}/quotes`로 받은 견적 목록이 고수 표시명·금액·메시지와 함께 표시된다.

5. **AC5 — 견적 수락 (FR13 재사용):** 견적 수락 탭 시 `POST /api/v1/quotes/{id}/accept`가 호출되어 채팅방이 생성되고, 관련 쿼리 캐시(`요청 상세`, `견적 목록`, `내 요청 목록`)가 갱신된다. 수락 성공 후 요청 목록으로 이동한다(채팅 화면 이동은 Story 5.4에서 구현).

6. **AC6 — 견적 거절 (FR14 재사용):** 견적 거절 탭 시 `POST /api/v1/quotes/{id}/reject`가 호출되고 견적 목록 캐시가 갱신되어 해당 견적 상태가 `rejected`로 갱신 표시된다.

7. **AC7 — NativeWind + 공유 UI (NFR2):** 모든 화면이 NativeWind className 및 `@gosoom/ui`의 Button·Input·Card·tokens로 렌더링되고, TanStack Query 로딩·에러 상태가 한국어로 표시된다.

## Tasks / Subtasks

> ⚡ **수동 설정 체크포인트:** 이 스토리는 별도 외부 설정 없음. Story 5.1의 `.env`(`EXPO_PUBLIC_API_URL`) 설정이 유지되어 있어야 한다.

- [x] Task 1 — 고객 레이아웃 & 내비게이션 업데이트 (AC1-AC6)
  - [x] 1.1: `apps/mobile/src/app/(customer)/_layout.tsx`의 Stack 스크린 등록에 `requests/new`와 `requests/[id]` 추가
  - [x] 1.2: 각 스크린에 적절한 `options.title` 설정 (예: "새 요청", "요청 상세")
  - [x] 1.3: `apps/mobile/.expo/types/router.d.ts`에 신규 라우트 타입 수동 추가 (`/(customer)/requests/new`, `/(customer)/requests/[id]`) — Expo dev server 실행 시 자동 재생성되나 typecheck를 위해 수동 추가 필요

- [x] Task 2 — 내 요청 목록 화면 구현 (AC1)
  - [x] 2.1: `apps/mobile/src/app/(customer)/requests/index.tsx` — 플레이스홀더를 실제 구현으로 교체
  - [x] 2.2: `useListMyServiceRequests()` 훅으로 요청 목록 로드 (커서 페이지네이션, FlatList `onEndReached`로 load more)
  - [x] 2.3: 각 항목: 카테고리명·지역·상태 배지·생성일 표시; 탭 시 `/(customer)/requests/[id]` 이동
  - [x] 2.4: "새 요청 만들기" FAB(또는 버튼) — `/(customer)/requests/new`로 이동
  - [x] 2.5: 로딩 스켈레톤(3개 Card), 에러 상태, 빈 목록 상태 각각 한국어로 표시
  - [x] 2.6: 상태 배지 문자열 매핑: `open→접수됨`, `matched→매칭됨`, `completed→완료됨`, `cancelled→취소됨`
  - [x] 2.7: 로그아웃 버튼 또는 헤더 메뉴 포함 (기존 플레이스홀더 로그아웃 버튼 유지)

- [x] Task 3 — 서비스 요청 생성 화면 (AC2)
  - [x] 3.1: `apps/mobile/src/app/(customer)/requests/new.tsx` 신규 생성
  - [x] 3.2: `useListCategories({ limit: 100 })` 로 카테고리 목록 로드 → Picker 또는 선택 버튼 목록으로 표시
  - [x] 3.3: `Input` 컴포넌트(`@gosoom/ui`)로 지역(region)·설명(description) 필수 필드 구현
  - [x] 3.4: 선택 필드: 희망일정(desiredSchedule, text)·예산(budget, number keyboardType='numeric') — 비워도 제출 가능
  - [x] 3.5: `useCreateServiceRequest()` mutation: `mutate({ data: { categoryId, region, description, desiredSchedule?, budget? } })`
  - [x] 3.6: `onSuccess` 시 `queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() })` + `router.replace('/(customer)/requests')` 호출
  - [x] 3.7: 제출 중 `isPending` 시 버튼 비활성화; 에러 시 `error.message` 표시
  - [x] 3.8: `SafeAreaView` + `KeyboardAvoidingView` 래핑 필수 (iOS 키보드 가림 방지)
  - [x] 3.9: 필수 필드 미입력 시 한국어 경고 표시 (API 호출 없이 클라이언트 검증)

- [x] Task 4 — 요청 상세 & 견적 화면 (AC3-AC6)
  - [x] 4.1: `apps/mobile/src/app/(customer)/requests/[id].tsx` 신규 생성
  - [x] 4.2: `useLocalSearchParams<{ id: string }>()` 로 `id` 추출
  - [x] 4.3: `useGetServiceRequest(id)` 로 요청 상세 로드 (카테고리명 표시 위해 `useListCategories({ limit: 100 })` 병렬 호출)
  - [x] 4.4: `useListServiceRequestQuotes(id)` 로 견적 목록 로드 — 각 견적: 고수 표시명·금액·메시지·상태 표시
  - [x] 4.5: 상태별 액션 버튼:
    - `status === 'open'`: `취소` 버튼 → `useUpdateServiceRequestStatus().mutate({ requestId: id, data: { action: 'cancel' } })`
    - `status === 'matched'`: `완료` 버튼 → `useUpdateServiceRequestStatus().mutate({ requestId: id, data: { action: 'complete' } })`
    - `status === 'completed'` / `cancelled`: 액션 버튼 없음
  - [x] 4.6: 견적 수락 버튼 (`open` 상태이고 견적 `status === 'pending'`인 경우에만 활성화):
    - `useAcceptQuote().mutate({ quoteId: quote.id })`
    - `onSuccess`: `invalidateQueries` 3개 — `getGetServiceRequestQueryKey(id)`, `getListServiceRequestQuotesQueryKey(id)`, `getListMyServiceRequestsQueryKey()` + `router.replace('/(customer)/requests')`
  - [x] 4.7: 견적 거절 버튼 (`open` 상태이고 견적 `status === 'pending'`인 경우에만 활성화):
    - `useRejectQuote().mutate({ quoteId: quote.id })`
    - `onSuccess`: `invalidateQueries` — `getListServiceRequestQuotesQueryKey(id)`
  - [x] 4.8: 모든 mutation `onError` 시 에러 메시지 한국어로 표시
  - [x] 4.9: 로딩 스켈레톤(상세 + 견적 각각), 에러 상태, 빈 견적 목록 상태 처리
  - [x] 4.10: `ScrollView` 내부 레이아웃 (상세 + 견적 섹션)

- [x] Task 5 — 타입체크 및 동작 확인
  - [x] 5.1: `pnpm --filter mobile typecheck` 통과
  - [ ] 5.2: Expo Go로 실기기 실행 후 황금 경로 확인 (코드 구현 완료 후 KTH가 직접 수행):
    - 요청 생성 → 목록 갱신 확인
    - 요청 상세 → 견적 표시 확인
    - 견적 수락 → 목록으로 이동 + 상태 `matched` 확인
    - 견적 거절 → 해당 견적 `rejected` 갱신 확인
    - 취소 → 상태 `cancelled` 확인
  - [ ] 5.3: 빈 목록·로딩·에러 상태 UI 확인 (KTH 직접)

### Review Findings

- [x] [Review][Patch] acceptError 전역 상태가 모든 견적 카드에 중복 표시 [`[id].tsx:328`] — 수락 실패 시 오류 메시지가 모든 견적 카드에 동일하게 반복 표시됨. `rejectErrors`는 quote별 Record로 구현되어 있으나 `acceptError`는 단일 string으로 일관성 결여. → `acceptErrors: Record<string, string>`으로 변경 적용
- [x] [Review][Patch] AC4 위반 — completed/cancelled 상태에서도 견적 섹션 항상 렌더링 [`[id].tsx:247`] — AC4는 `open`/`matched` 상태 요청에 한해 견적 목록을 표시하도록 명시. `completed`/`cancelled` 상태에서도 `useListServiceRequestQuotes` 호출과 "받은 견적" 섹션이 렌더링됨. → `shouldShowQuotes` 조건부 렌더링 적용
- [x] [Review][Patch] 카테고리 로드 실패 시 에러 UI 없음 [`new.tsx`] — `useListCategories`의 `isError` 케이스 미처리. 카테고리 API 실패 시 빈 그리드만 표시, 재시도 방법 없음. → `isError` 분기 추가
- [x] [Review][Patch] "받은 견적" 타이틀이 request 로딩/에러 상태에서도 항상 렌더링 [`[id].tsx:247`] — `isPending`/`isError` 시에도 "받은 견적" 텍스트가 항상 표시되어 시각적으로 어색함. → `shouldShowQuotes` 조건 블록에 포함
- [x] [Review][Patch] 수락/거절 뮤테이션 isPending 상태가 모든 견적에 공유됨 [`[id].tsx`] — `acceptMutation.isPending`, `rejectMutation.isPending`이 컴포넌트 전역 상태. 한 견적 처리 중 모든 견적 버튼이 비활성화되며 어느 견적이 처리 중인지 구별 불가. → `processingQuoteId` state 추가, quote별 라벨/비활성화 처리
- [x] [Review][Patch] handleRefresh 후 stale cursor 응답으로 allItems 오염 가능성 [`index.tsx`] — `processedCursors.current = new Set()` 초기화 후 이전 cursor의 in-flight 응답이 늦게 도착하면 `allItems`에 오염된 데이터가 삽입될 수 있음. → `pendingRefresh` ref 추가, refetch 시작 대기 후 처리
- [x] [Review][Defer] `id`가 배열로 파싱될 수 있음 [`[id].tsx`] — deferred, expo-router 표준 패턴에서 단일 동적 세그먼트는 항상 string 반환
- [x] [Review][Defer] budget `parseInt` 소수점/비정형 입력 수락 [`new.tsx`] — deferred, `keyboardType="numeric"`으로 실제 입력 차단됨, MVP 단계 허용
- [x] [Review][Defer] `formatDate` Invalid Date 표시 가능성 [`[id].tsx`] — deferred, API 반환값 ISO 형식 보장됨
- [x] [Review][Defer] background refetch 후 `allItems` 미갱신 [`index.tsx`] — deferred, MVP 단계 허용 가능한 동작

## Dev Notes

### 현재 모바일 앱 상태 (Story 5.1 완료 기준)

```
apps/mobile/src/app/
├── _layout.tsx              # QueryClientProvider + AuthProvider + AuthGate 완비
├── (auth)/login.tsx         # 로그인 화면 — 완료
├── (auth)/signup.tsx        # 가입 화면 — 완료
├── (customer)/
│   ├── _layout.tsx          # 고객 보호 레이아웃 (역할 검증) — ⬅ Task 1에서 수정
│   └── requests/
│       └── index.tsx        # 플레이스홀더 — ⬅ Task 2에서 교체
└── (pro)/
    ├── _layout.tsx
    └── feed/index.tsx       # 플레이스홀더
```

**5.1에서 확정된 인프라 (재사용, 재발명 금지):**
- `useAuth()` — `user`, `isLoading`, `login`, `signup`, `logout` 제공 (AuthContext)
- `@gosoom/api-client` — TanStack Query 훅 자동생성, Bearer 인터셉터 내장
- `@gosoom/ui` — `Button`, `Input`, `Card`, `tokens` RN 호환 컴포넌트

### API 훅 사용법 — 절대 직접 fetch 금지

```typescript
// ❌ 절대 금지
await fetch(`${API_URL}/service-requests`);

// ✅ 올바른 방법 — Orval 자동생성 훅 사용
import {
  useListMyServiceRequests,
  useGetServiceRequest,
  useCreateServiceRequest,
  useUpdateServiceRequestStatus,
  useListServiceRequestQuotes,
  useAcceptQuote,
  useRejectQuote,
  useListCategories,
  getListMyServiceRequestsQueryKey,
  getGetServiceRequestQueryKey,
  getListServiceRequestQuotesQueryKey,
} from '@gosoom/api-client';
```

### 쿼리 훅 패턴

```typescript
// 목록 조회 (커서 페이지네이션)
const { data, isPending, isError, isFetching } =
  useListMyServiceRequests({ cursor, limit: 20 });
// data.items: ServiceRequestRead[]
// data.nextCursor: string | null | undefined

// 상세 조회
const { data: request, isPending, isError } =
  useGetServiceRequest(id, {
    query: { enabled: !!id },
  });

// 견적 목록 (특정 요청)
const { data: quotesData } = useListServiceRequestQuotes(id);
// quotesData.items: QuoteWithProInfo[]

// 카테고리 목록 (전체, 선택 화면용)
const { data: categories } = useListCategories({ limit: 100 });
// categories.items: CategoryRead[] — { id, name }
```

### 뮤테이션 훅 패턴

```typescript
// 서비스 요청 생성
const createMutation = useCreateServiceRequest({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      router.replace('/(customer)/requests');
    },
    onError: (err) => setErrorMsg(err.message),
  },
});
createMutation.mutate({
  data: { categoryId, region, description, desiredSchedule, budget },
});

// 상태 업데이트 (취소/완료)
// ServiceRequestStatusUpdateAction 허용값: 'cancel' | 'complete'
const statusMutation = useUpdateServiceRequestStatus({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
    },
  },
});
statusMutation.mutate({ requestId: id, data: { action: 'cancel' } }); // 또는 'complete'

// 견적 수락 — 반환값 ChatRoomRead (chatRoom.id는 Story 5.4에서 사용)
const acceptMutation = useAcceptQuote({
  mutation: {
    onSuccess: (_chatRoom) => {
      queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      // ⚠️ 채팅 화면 이동은 Story 5.4에서 구현. 지금은 목록으로 이동
      router.replace('/(customer)/requests');
    },
    onError: (err) => setErrorMsg(err.message),
  },
});
acceptMutation.mutate({ quoteId: quote.id });

// 견적 거절
const rejectMutation = useRejectQuote({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
    },
    onError: (err) => setErrorMsg(err.message),
  },
});
rejectMutation.mutate({ quoteId: quote.id });
```

### 커서 페이지네이션 패턴 (FlatList용)

```typescript
// race condition 방지: processedCursors ref 사용 — 동일 커서 중복 처리 방지
const [cursor, setCursor] = useState<string | undefined>(undefined);
const [allItems, setAllItems] = useState<ServiceRequestRead[]>([]);
const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
const processedCursors = useRef(new Set<string | undefined>());

const { data, isPending, isFetching } = useListMyServiceRequests({ cursor, limit: 20 });

useEffect(() => {
  if (isFetching || !data?.items) return;
  if (processedCursors.current.has(cursor)) return;
  processedCursors.current.add(cursor);
  setAllItems((prev) => cursor === undefined ? data.items : [...prev, ...data.items]);
  setNextCursor(data.nextCursor ?? null);
}, [data, cursor, isFetching]);

// FlatList onEndReached
const handleLoadMore = () => {
  if (nextCursor && !isFetching) setCursor(nextCursor);
};
```

### expo-router 동적 라우트 파라미터 추출

```typescript
// apps/mobile/src/app/(customer)/requests/[id].tsx
import { useLocalSearchParams } from 'expo-router';

export default function RequestDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  // id는 URL 세그먼트 값 (UUIDv7 문자열)
  // ...
}
```

### 레이아웃 Stack 스크린 등록

```typescript
// apps/mobile/src/app/(customer)/_layout.tsx
// 기존 Stack.Screen('requests/index') 유지하고 신규 추가
return (
  <Stack screenOptions={{ headerShown: false }}>
    <Stack.Screen name="requests/index" />
    <Stack.Screen name="requests/new" options={{ title: '새 요청 만들기', headerShown: true }} />
    <Stack.Screen name="requests/[id]" options={{ title: '요청 상세', headerShown: true }} />
  </Stack>
);
// headerShown: false는 requests/index (커스텀 헤더), true는 detail/new (기본 뒤로 버튼 활용)
```

### router.d.ts 수동 업데이트 (typecheck용)

```typescript
// apps/mobile/.expo/types/router.d.ts — 기존 타입에 추가
// (Expo dev server 실행 시 자동 재생성되지만, typecheck만 할 때는 수동 추가 필요)
declare module 'expo-router' {
  export namespace ExpoRouter {
    export interface __routes<T extends string = string> extends Record<string, unknown> {
      // ... 기존 라우트들 ...
      StaticRoutes: '/(customer)/requests' | '/(customer)/requests/new' | /* 기존 */ ...;
      DynamicRoutes: '/(customer)/requests/[id]' | /* 기존 */ ...;
    }
  }
}
```

### @gosoom/ui 컴포넌트 사용법

```typescript
import { Button, Input, Card, tokens } from '@gosoom/ui';

// Button — label prop 사용 (children 아님!)
<Button label="요청 만들기" onPress={handleSubmit} disabled={isPending} />

// Input — onChangeText prop (onChange 아님)
<Input
  value={region}
  onChangeText={setRegion}
  placeholder="지역을 입력하세요"
  editable={!isPending}
/>

// Card — children 래핑
<Card>
  <Text>카드 내용</Text>
</Card>

// tokens — StyleSheet.create에서 사용
const styles = StyleSheet.create({
  container: { backgroundColor: tokens.colors.background, padding: tokens.spacing.md },
  title: { fontSize: tokens.fontSize.lg, fontWeight: tokens.fontWeight.semibold, color: tokens.colors.text },
  badge: { color: tokens.colors.primary },
  danger: { color: tokens.colors.danger },
  success: { color: tokens.colors.success },
});
```

### 상태 배지 매핑 (일관성 유지)

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

### SafeAreaView + KeyboardAvoidingView 패턴 (폼 화면 필수)

```typescript
import { KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function RequestNewScreen() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: tokens.colors.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={{ padding: tokens.spacing.lg }}>
          {/* 폼 내용 */}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
```

### 카테고리 선택 UI (Picker 대안)

`@react-native-picker/picker`는 별도 설치 필요. 설치 없이 구현하려면:
- 카테고리 목록을 버튼 그리드로 표시 (선택 시 배경색 변경)
- 또는 expo-router Modal을 활용한 선택 화면

권장: 간단한 버튼 목록 방식 (Touchable로 선택/해제 토글)

```typescript
categories.items.map((cat) => (
  <TouchableOpacity
    key={cat.id}
    onPress={() => setSelectedCategoryId(cat.id)}
    style={[
      styles.categoryBtn,
      selectedCategoryId === cat.id && styles.categoryBtnSelected,
    ]}
  >
    <Text>{cat.name}</Text>
  </TouchableOpacity>
))
```

### Story 5.1에서 발견된 패턴 (재사용)

- **에러 메시지**: `err.message` 직접 표시 (api-client에서 이미 한국어로 변환)
- **라우트 이동**: `router.push(...)` for 새 화면, `router.replace(...)` for 뒤로 갈 수 없는 화면 (완료 후)
- **스타일**: `StyleSheet.create()`과 `tokens` 조합 사용
- **NativeWind**: `className` prop 사용 가능하지만 StyleSheet 방식도 OK (일관성만 유지)
- **null 반환 패턴**: 로딩 중 `return null` 대신 스켈레톤 표시 (UX 개선)

### 웹 참고 파일 (구현 전 반드시 읽기)

```
apps/user-web/src/app/(customer)/requests/page.tsx       — 목록 화면 패턴
apps/user-web/src/app/(customer)/requests/new/page.tsx   — 생성 폼 패턴
apps/user-web/src/app/(customer)/requests/[id]/page.tsx  — 상세+견적 복합 패턴 (가장 중요)
```

**[id] 페이지 핵심 패턴 (반드시 참고):**
- 동시 3개 훅: `useGetServiceRequest`, `useListServiceRequestQuotes`, `useListCategories`
- `QueryClient.invalidateQueries` 다중 키 처리 패턴
- 견적 수락 후 `ChatRoomRead.id` 처리
- 상태별 조건부 버튼 렌더링

### 주의사항 — 하지 말 것

1. **`packages/api-client/src/generated/` 수정 금지** — Orval 자동생성, 빌드 시 덮어씀
2. **`useUpdateServiceRequestStatus`에 임의 action 값 사용 금지** — 'cancel' | 'complete' 만 유효
3. **채팅 화면 이동 구현 금지** — Story 5.4의 범위. 수락 후 `router.replace('/(customer)/requests')` 로 충분
4. **신규 API 엔드포인트 추가 금지** — 이 스토리는 FR1-18 재사용만, 신규 FR 없음
5. **`(pro)/` 또는 다른 그룹 파일 수정 금지** — 이 스토리의 범위 아님

## References

- [Source: epics.md#Story 5.2] — 유저 스토리, AC 전문
- [Source: architecture.md] — Expo SDK 55, expo-router, NativeWind v4, @gosoom/ui, api-client 패턴
- [Story 5.1: apps/mobile/src/features/auth/AuthContext.tsx] — useAuth() 인터페이스
- [Story 5.1: apps/mobile/src/app/(customer)/_layout.tsx] — 현재 Stack 레이아웃 (수정 대상)
- [Story 5.1: apps/mobile/src/app/(customer)/requests/index.tsx] — 현재 플레이스홀더 (교체 대상)
- [Source: apps/user-web/src/app/(customer)/requests/[id]/page.tsx] — 핵심 참조 구현
- [Source: packages/api-client/src/generated/service-requests/] — 훅 시그니처 확인
- [Source: packages/api-client/src/generated/quotes/] — 견적 훅 시그니처 확인
- [Source: packages/ui/src/tokens.ts] — 디자인 토큰 (colors, spacing, fontSize, fontWeight, radius)
- [Source: packages/ui/src/index.ts] — Button, Input, Card, tokens export 확인

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- TypeCheck 1회차 실패: `tokens.fontSize.xs` (없는 토큰) → 12 하드코딩으로 수정
- TypeCheck 1회차 실패: `tokens.colors.surface` (없는 색상) → `tokens.colors.backgroundSecondary`로 수정
- TypeCheck 1회차 실패: `HTTPValidationError`에 `message` 없음 → 훅 제네릭 `<TData, Error>` 명시로 수정
- TypeCheck 1회차 실패: `useGetServiceRequest` `query: { enabled }` 전달 시 `queryKey` 필수 오류 → 제네릭으로 단순화
- TypeCheck 1회차 실패: `@gosoom/ui` `Input`에 `multiline`/`numberOfLines`/`style` 미지원 → description 필드는 RN `TextInput` 직접 사용

### Completion Notes List

- Task 1: `_layout.tsx`에 `requests/new`, `requests/[id]` Stack.Screen 추가 (title, headerShown 포함)
- Task 1: `router.d.ts`에 신규 라우트 타입 수동 추가 (typecheck 지원)
- Task 2: `requests/index.tsx` 플레이스홀더를 완전한 구현으로 교체 — 커서 페이지네이션(processedCursors ref 패턴), FAB, 상태 배지, 로딩/에러/빈 상태 모두 구현
- Task 3: `requests/new.tsx` 신규 생성 — 카테고리 버튼 그리드, 클라이언트 유효성 검증, KeyboardAvoidingView
- Task 4: `requests/[id].tsx` 신규 생성 — 3개 훅 병렬 로드, 상태별 액션 버튼, 견적 수락/거절 (쿼리 캐시 3개 무효화)
- Task 5: `pnpm --filter mobile typecheck` 통과 확인

### File List

apps/mobile/src/app/(customer)/_layout.tsx
apps/mobile/src/app/(customer)/requests/index.tsx
apps/mobile/src/app/(customer)/requests/new.tsx
apps/mobile/src/app/(customer)/requests/[id].tsx
apps/mobile/.expo/types/router.d.ts
_bmad-output/implementation-artifacts/sprint-status.yaml

## Change Log

- 2026-06-11: Story 5.2 생성 (ready-for-dev)
- 2026-06-11: Story 5.2 구현 완료 — Task 1~5 완료, typecheck 통과, 상태 review
- 2026-06-11: 코드 리뷰 완료 — 6개 패치 적용 (AC4 견적 섹션 조건부 렌더링, acceptErrors 견적별 분리, processingQuoteId 개별 상태 추적, 카테고리 에러 UI, pendingRefresh 가드), 상태 done
