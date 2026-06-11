---
baseline_commit: ec94674
---

# Story 5.4: 모바일 채팅

Status: done

## Story

As a 고객·고수,
I want 모바일에서 채팅방 목록을 보고 메시지를 주고받기를,
So that 어디서나 거래 상대와 대화할 수 있다.

## Acceptance Criteria

1. **AC1 — 채팅방 목록 (FR18 재사용):** 고객과 고수 모두 채팅 진입 시 `useListChatRooms({ mine: true, cursor })` 로 본인 참여 방 목록이 커서 페이지네이션으로 표시된다. 각 항목에 상대방 `counterpartDisplayName` 과 연관 서비스 요청 정보(`serviceRequest.region`, `serviceRequest.description` 50자 truncate)가 표시되고, 탭 시 해당 채팅방으로 이동한다.

2. **AC2 — 채팅방 진입 경로:** 고객은 `(customer)/requests/index` 헤더 "채팅" 버튼, 또는 견적 수락 직후 자동 이동으로 채팅방 목록·방에 진입한다. 고수는 `(pro)/feed/index` 헤더 "채팅" 버튼으로 진입한다.

3. **AC3 — 견적 수락 후 채팅 자동 이동 (FR13/FR15 재사용):** 고객이 견적을 수락하면 `useAcceptQuote` onSuccess에서 반환된 `ChatRoomRead.id` 로 `router.replace('/(customer)/chat/[id]', { id: chatRoom.id })` 가 호출되어 즉시 채팅방으로 이동한다.

4. **AC4 — 증분 폴링 (FR16/FR17, CM1):** 채팅방 화면 진입 시 `list_messages` raw 함수를 `refetchInterval: 2000` 으로 폴링한다. 초기 로드는 `after` 없이 최근 50개를 가져오고, 이후 폴링은 `after=lastMessageId` 로 신규 메시지만 수신한다. 쿼리 키는 `['chat-messages', chatRoomId]` 고정 (lastId 미포함).

5. **AC5 — 메시지 전송 (FR16):** TextInput에 내용 입력 후 전송 버튼 탭 시 `useSendMessage.mutate({ chatRoomId, data: { content } })` 가 호출된다. 전송 성공 시 새 메시지가 목록에 즉시(낙관적) 추가되고 `lastIdRef` 가 갱신된다. 빈 내용은 클라이언트에서 차단한다. 전송 중 버튼 비활성화.

6. **AC6 — 메시지 좌우 정렬 (FR17):** 내 메시지(`senderId === user.id`)는 우측, 상대 메시지는 좌측에 표시된다. `useAuth().user.id` 로 비교.

7. **AC7 — 중복 메시지 방지:** 낙관적 append와 2초 폴링의 경쟁 조건으로 동일 메시지가 두 번 렌더링되지 않도록 id 기반 dedup을 적용한다.

8. **AC8 — NativeWind + 공유 UI (NFR2):** 모든 화면이 `@gosoom/ui` 의 `Button`·`Card`·`tokens` 와 StyleSheet로 렌더링되고, 로딩·에러 상태가 한국어로 표시된다.

## Tasks / Subtasks

> ⚡ **수동 설정 체크포인트:** Story 5.1의 `.env`(`EXPO_PUBLIC_API_URL`) 설정 유지 필수. 채팅 폴링 동작 확인을 위해 Expo Go 실기기 실행 필요 (localhost 불가).

- [x] Task 1 — 내비게이션 & 레이아웃 업데이트 (AC1-AC3)
  - [x] 1.1: `apps/mobile/src/app/(customer)/_layout.tsx` Stack에 신규 스크린 등록:
    - `chat/index` (options: `{ title: '채팅 목록', headerShown: true }`)
    - `chat/[id]` (options: `{ title: '채팅', headerShown: true }`)
  - [x] 1.2: `apps/mobile/src/app/(pro)/_layout.tsx` Stack에 신규 스크린 등록:
    - `chat/index` (options: `{ title: '채팅 목록', headerShown: true }`)
    - `chat/[id]` (options: `{ title: '채팅', headerShown: true }`)
  - [x] 1.3: `apps/mobile/.expo/types/router.d.ts` 에 신규 라우트 타입 수동 추가 (3곳: hrefInputParams, hrefOutputParams, href):
    - `/(customer)/chat` (static)
    - `/(customer)/chat/[id]` (dynamic)
    - `/(pro)/chat` (static)
    - `/(pro)/chat/[id]` (dynamic)
  - [x] 1.4: `apps/mobile/src/app/(customer)/requests/index.tsx` 헤더에 "채팅" 버튼 추가 → `router.push('/(customer)/chat')`
  - [x] 1.5: `apps/mobile/src/app/(pro)/feed/index.tsx` 헤더 headerButtons 에 "채팅" 버튼 추가 → `router.push('/(pro)/chat')`
  - [x] 1.6: `apps/mobile/src/app/(customer)/requests/[id].tsx` 의 `acceptMutation.onSuccess` 수정:
    - 기존: `router.replace('/(customer)/requests')`
    - 변경: `router.replace({ pathname: '/(customer)/chat/[id]', params: { id: chatRoom.id } })`
    - `onSuccess: (chatRoom) =>` 로 파라미터 추가 (기존에는 무시함)

- [x] Task 2 — 공유 채팅 컴포넌트 생성 (AC1, AC8)
  - [x] 2.1: `apps/mobile/src/components/chat/ChatRoomListScreen.tsx` 신규 생성
    - `useListChatRooms<PageChatRoomListItem, Error>({ mine: true, cursor })` + processedCursors ref 커서 페이지네이션
    - 각 항목 표시: `counterpartDisplayName` (굵게) + `serviceRequest?.region` + `serviceRequest?.description` (50자 truncate)
    - `serviceRequest` null 시 "(삭제된 요청)" 표시
    - FlatList + onEndReached 무한 스크롤
    - 탭 시 `router.push({ pathname: '/(customer)/chat/[id]', params: { id: item.id } })` 또는 `/(pro)/chat/[id]` — role 분기 필요 (`useAuth().user.role`)
    - 로딩 스켈레톤(3개 Card), 에러 상태, 빈 목록("참여 중인 채팅방이 없습니다") 표시
    - SafeAreaView + FlatList
  - [x] 2.2: `apps/mobile/src/components/chat/ChatRoomScreen.tsx` 신규 생성 (AC4-AC7)
    - `useLocalSearchParams<{ id: string | string[] }>()` 로 `id` 추출 — 배열 타입 가드 필수 (`Array.isArray(id) ? id[0] : id`)
    - `useQuery({ queryKey: ['chat-messages', chatRoomId], queryFn: () => list_messages(chatRoomId, { after: lastIdRef.current }), refetchInterval: 2000, enabled: !!chatRoomId })` 로 증분 폴링
    - `useRef<string | undefined>(undefined)` 로 `lastIdRef` 관리
    - `useState<MessageRead[]>([])` 로 `allMessages` 누적
    - useEffect: 새 items 도착 시 id-dedup 후 append + lastIdRef 갱신
    - `useSendMessage<Error>` mutation: onSuccess → 낙관적 append + lastIdRef 갱신 + input 초기화
    - `useAuth().user.id` 로 senderId 비교 → 좌우 정렬
    - FlatList (inverted=false) + `flatListRef.current?.scrollToEnd()` — 새 메시지 시 하단 유지
    - KeyboardAvoidingView + TextInput (하단 입력창)
    - 전송 버튼: content.trim() 없음 시 비활성 + isPending 시 비활성
    - SafeAreaView + KeyboardAvoidingView + FlatList

- [x] Task 3 — 역할별 화면 파일 생성 (thin wrappers) (AC1-AC7)
  - [x] 3.1: `apps/mobile/src/app/(customer)/chat/index.tsx` 신규 생성 — ChatRoomListScreen re-export
  - [x] 3.2: `apps/mobile/src/app/(customer)/chat/[id].tsx` 신규 생성 — ChatRoomScreen re-export
  - [x] 3.3: `apps/mobile/src/app/(pro)/chat/index.tsx` 신규 생성 — ChatRoomListScreen re-export
  - [x] 3.4: `apps/mobile/src/app/(pro)/chat/[id].tsx` 신규 생성 — ChatRoomScreen re-export

- [x] Task 4 — 타입체크 및 동작 확인
  - [x] 4.1: `pnpm --filter mobile typecheck` 통과
  - [ ] 4.2: Expo Go 실기기 실행 후 황금 경로 확인 (KTH 직접):
    - 고객: 견적 수락 → 채팅방 자동 이동 → 메시지 전송 확인
    - 고수: 피드 헤더 채팅 버튼 → 채팅방 목록 → 방 진입 → 메시지 전송 확인
    - 양쪽에서 2초 폴링으로 상대 메시지 자동 갱신 확인
    - 내 메시지 우측 / 상대 메시지 좌측 정렬 확인
    - 전송 중 버튼 비활성화 확인
  - [ ] 4.3: 빈 목록·로딩·에러 상태 UI 확인 (KTH 직접)

## Dev Notes

### 현재 모바일 앱 상태 (Story 5.3 완료 기준)

```
apps/mobile/src/app/
├── _layout.tsx              # QueryClientProvider + AuthProvider + AuthGate + Slot
├── (auth)/login.tsx         # 로그인 — 완료
├── (auth)/signup.tsx        # 가입 — 완료
├── (customer)/
│   ├── _layout.tsx          # Stack: requests/index, requests/new, requests/[id]
│   └── requests/
│       ├── index.tsx        # 내 요청 목록 + 헤더 (로그아웃만 있음)
│       ├── new.tsx          # 요청 생성 — 완료
│       └── [id].tsx         # 요청 상세 + 견적 수락/거절 → 수락 후 requests로 이동 ⬅ 수정
└── (pro)/
    ├── _layout.tsx          # Stack: feed/index, feed/[id], categories/index, quotes/index
    ├── feed/
    │   ├── index.tsx        # 피드 목록 + 커스텀 헤더(내 견적, 카테고리, 로그아웃) ⬅ 채팅 버튼 추가
    │   └── [id].tsx         # 요청 상세 + 견적 제안 — 완료
    ├── categories/index.tsx # 카테고리 설정 — 완료
    └── quotes/index.tsx     # 내 견적 목록 — 완료
```

**이 스토리에서 신규 생성할 파일:**
```
apps/mobile/src/
├── components/
│   └── chat/
│       ├── ChatRoomListScreen.tsx   # 공유 채팅방 목록 구현
│       └── ChatRoomScreen.tsx       # 공유 채팅방 구현
└── app/
    ├── (customer)/
    │   ├── _layout.tsx              # 수정: chat/index, chat/[id] 스크린 등록
    │   ├── chat/
    │   │   ├── index.tsx            # 신규 (thin wrapper)
    │   │   └── [id].tsx             # 신규 (thin wrapper)
    │   └── requests/
    │       ├── index.tsx            # 수정: 헤더 채팅 버튼 추가
    │       └── [id].tsx             # 수정: acceptMutation.onSuccess 채팅 이동
    └── (pro)/
        ├── _layout.tsx              # 수정: chat/index, chat/[id] 스크린 등록
        ├── chat/
        │   ├── index.tsx            # 신규 (thin wrapper)
        │   └── [id].tsx             # 신규 (thin wrapper)
        └── feed/
            └── index.tsx            # 수정: 헤더 채팅 버튼 추가
```

### 확립된 인프라 — 재발명 금지

- `useAuth()` — `user.id`, `user.role`, `isLoading`, `login`, `logout` (AuthContext)
- `@gosoom/api-client` — TanStack Query 훅 자동생성, Bearer 인터셉터 내장
- `@gosoom/ui` — `Button`, `Input`, `Card`, `tokens` RN 호환 컴포넌트
- processedCursors + pendingRefresh 패턴 — 커서 페이지네이션 (5.2/5.3에서 확립)

### API 훅 사용법 — 절대 직접 fetch 금지

```typescript
// ✅ 채팅 관련 import — @gosoom/api-client에서 통합 import
import {
  // 채팅방 목록 (hook)
  useListChatRooms,
  type PageChatRoomListItem,
  type ChatRoomListItem,
  // 메시지 (raw function + hook)
  list_messages,           // useQuery의 queryFn으로 직접 사용 (incremental polling 패턴)
  useSendMessage,
  type MessageRead,
  type MessageCreate,
  // 타입
  type ChatRoomRead,
} from '@gosoom/api-client';
```

### 훅 시그니처 및 반환 타입

```typescript
// 채팅방 목록 (cursor 페이지네이션)
const { data, isPending, isError, isFetching } =
  useListChatRooms<PageChatRoomListItem, Error>({ mine: true, cursor });
// data.items: ChatRoomListItem[]
// ChatRoomListItem: {
//   id: string,
//   serviceRequestId: string,
//   createdAt: string,
//   counterpartDisplayName: string,
//   serviceRequest?: ServiceRequestSummary | null
// }
// data.nextCursor: string | null

// 메시지 폴링 — useListMessages 훅 대신 raw function + useQuery 사용 (queryKey 안정화)
import { useQuery } from '@tanstack/react-query';
const { data: pollData } = useQuery({
  queryKey: ['chat-messages', chatRoomId],  // lastId 포함 금지!
  queryFn: () => list_messages(chatRoomId, { after: lastIdRef.current }),
  refetchInterval: 2000,
  enabled: !!chatRoomId,
});
// pollData?.items: MessageRead[]
// MessageRead: { id: string, chatRoomId: string, senderId: string, content: string, createdAt: string }

// 메시지 전송 뮤테이션
const sendMutation = useSendMessage({
  mutation: {
    onSuccess: (newMsg) => {
      setAllMessages(prev => {
        // dedup 후 append
        if (prev.some(m => m.id === newMsg.id)) return prev;
        return [...prev, newMsg];
      });
      lastIdRef.current = newMsg.id;
      setContent('');
    },
    onError: (err) => setSendError(err.message || '메시지 전송에 실패했습니다.'),
  },
});
// sendMutation.mutate({ chatRoomId: string, data: { content: string } })

// useAcceptQuote (기존 — onSuccess 시그니처 수정)
const acceptMutation = useAcceptQuote<Error>({
  mutation: {
    onSuccess: (chatRoom: ChatRoomRead) => {  // 기존에 () => 였음, chatRoom 파라미터 추가!
      // ... queryClient.invalidateQueries 들 ...
      router.replace({ pathname: '/(customer)/chat/[id]', params: { id: chatRoom.id } });
    },
    onError: ...
  }
});
```

### 증분 폴링 패턴 — 핵심 원칙

```typescript
// ChatRoomScreen.tsx 핵심 패턴
import { useRef, useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { list_messages, useSendMessage, type MessageRead } from '@gosoom/api-client';
import { useAuth } from '@/features/auth';

export default function ChatRoomScreen() {
  const rawId = useLocalSearchParams<{ id: string | string[] }>().id;
  const chatRoomId = Array.isArray(rawId) ? rawId[0] : rawId; // 배열 타입 가드
  const { user } = useAuth();

  const lastIdRef = useRef<string | undefined>(undefined);
  const [allMessages, setAllMessages] = useState<MessageRead[]>([]);
  const [content, setContent] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const flatListRef = useRef(null);

  // 쿼리 키에 lastId 포함 금지 — refetchInterval이 리셋됨
  const { data: pollData } = useQuery({
    queryKey: ['chat-messages', chatRoomId],
    queryFn: () => list_messages(chatRoomId!, { after: lastIdRef.current }),
    refetchInterval: 2000,
    enabled: !!chatRoomId,
  });

  // 새 메시지 누적 + dedup
  useEffect(() => {
    if (!pollData?.items?.length) return;
    setAllMessages(prev => {
      const existingIds = new Set(prev.map(m => m.id));
      const newMsgs = pollData.items.filter(m => !existingIds.has(m.id));
      if (!newMsgs.length) return prev;
      return [...prev, ...newMsgs];
    });
    lastIdRef.current = pollData.items[pollData.items.length - 1].id;
  }, [pollData]);

  // 새 메시지 시 스크롤 하단
  useEffect(() => {
    if (allMessages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [allMessages]);

  const sendMutation = useSendMessage({
    mutation: {
      onSuccess: (newMsg) => {
        setAllMessages(prev => {
          if (prev.some(m => m.id === newMsg.id)) return prev;
          return [...prev, newMsg];
        });
        lastIdRef.current = newMsg.id;
        setContent('');
        setSendError(null);
      },
      onError: (err) => setSendError(err.message || '메시지 전송에 실패했습니다.'),
    },
  });

  const handleSend = () => {
    if (!content.trim() || !chatRoomId) return;
    sendMutation.mutate({ chatRoomId, data: { content: content.trim() } });
  };

  // MessageRead의 senderId와 useAuth().user.id 비교
  const isMyMessage = (msg: MessageRead) => msg.senderId === user?.id;
  // ...
}
```

### 채팅방 목록 커서 페이지네이션 패턴

```typescript
// ChatRoomListScreen.tsx — 5.2/5.3에서 확립된 processedCursors 패턴 재사용
const [cursor, setCursor] = useState<string | undefined>(undefined);
const [allRooms, setAllRooms] = useState<ChatRoomListItem[]>([]);
const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
const processedCursors = useRef(new Set<string | undefined>());
const pendingRefresh = useRef(false);

const { data, isPending, isFetching } = useListChatRooms<PageChatRoomListItem, Error>(
  { mine: true, ...(cursor ? { cursor } : {}) }
);

useEffect(() => {
  if (isFetching) {
    if (pendingRefresh.current) pendingRefresh.current = false;
    return;
  }
  if (!data?.items) return;
  if (pendingRefresh.current) return;
  if (processedCursors.current.has(cursor)) return;
  processedCursors.current.add(cursor);
  setAllRooms(prev => cursor === undefined ? data.items : [...prev, ...data.items]);
  setNextCursor(data.nextCursor ?? null);
}, [data, cursor, isFetching]);

const handleLoadMore = () => {
  if (nextCursor && !isFetching) setCursor(nextCursor);
};
```

### 채팅방 목록 항목 탭 → role별 라우팅

채팅방 목록 컴포넌트는 고객과 고수 양쪽에서 사용된다. 탭 시 이동 경로는 role에 따라 분기:

```typescript
const { user } = useAuth();

const handleRoomPress = (roomId: string) => {
  if (user?.role === 'customer') {
    router.push({ pathname: '/(customer)/chat/[id]', params: { id: roomId } });
  } else {
    router.push({ pathname: '/(pro)/chat/[id]', params: { id: roomId } });
  }
};
```

### @gosoom/ui 컴포넌트 주의사항 (5.1-5.3 경험 축적)

```typescript
// Button — label prop 사용 (children 아님!)
<Button label="전송" onPress={handleSend} disabled={sendMutation.isPending || !content.trim()} />

// TextInput — Input 컴포넌트 multiline 미지원, RN TextInput 직접 사용
import { TextInput, Platform } from 'react-native';
<TextInput
  value={content}
  onChangeText={setContent}
  placeholder="메시지를 입력하세요"
  placeholderTextColor={tokens.colors.textSecondary}
  style={styles.messageInput}
  // 단일 라인 채팅 입력이므로 multiline 불필요
  returnKeyType="send"
  onSubmitEditing={handleSend}
  blurOnSubmit={false}
/>

// 사용 가능한 tokens:
// colors: background, backgroundSecondary, text, textSecondary, primary, danger, success, border
// spacing: xs, sm, md, lg, xl
// fontSize: sm, base, lg, xl
// fontWeight: regular, semibold, bold
// radius: sm, md, lg
// tokens.fontWeight.medium — 존재하지 않음! (5.2 리뷰에서 badge에서 직접 사용하지 말 것)
```

### SafeAreaView + KeyboardAvoidingView 패턴 (채팅 화면 필수)

```typescript
import { KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

// 채팅방 화면 레이아웃 구조
<SafeAreaView style={{ flex: 1, backgroundColor: tokens.colors.background }}>
  <KeyboardAvoidingView
    style={{ flex: 1 }}
    behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
  >
    {/* 메시지 목록 */}
    <FlatList
      ref={flatListRef}
      data={allMessages}
      keyExtractor={(item) => item.id}
      style={{ flex: 1 }}
      contentContainerStyle={{ padding: tokens.spacing.md, gap: tokens.spacing.sm }}
      renderItem={({ item }) => (
        <View style={[
          styles.messageBubble,
          isMyMessage(item) ? styles.myBubble : styles.theirBubble,
        ]}>
          <Text style={[
            styles.messageText,
            isMyMessage(item) ? styles.myText : styles.theirText,
          ]}>
            {item.content}
          </Text>
        </View>
      )}
    />
    {/* 입력창 */}
    <View style={styles.inputRow}>
      <TextInput ... style={{ flex: 1 }} />
      <Button label={sendMutation.isPending ? "..." : "전송"} onPress={handleSend} ... />
    </View>
    {sendError && <Text style={styles.errorText}>{sendError}</Text>}
  </KeyboardAvoidingView>
</SafeAreaView>

// 메시지 버블 스타일
const styles = StyleSheet.create({
  messageBubble: {
    maxWidth: '75%',
    borderRadius: tokens.radius.lg,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
  },
  myBubble: {
    alignSelf: 'flex-end',
    backgroundColor: tokens.colors.primary,
  },
  theirBubble: {
    alignSelf: 'flex-start',
    backgroundColor: tokens.colors.backgroundSecondary,
  },
  myText: { color: '#FFFFFF', fontSize: tokens.fontSize.sm },
  theirText: { color: tokens.colors.text, fontSize: tokens.fontSize.sm },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: tokens.colors.border,
    gap: tokens.spacing.sm,
  },
  messageInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.text,
    backgroundColor: tokens.colors.backgroundSecondary,
  },
  errorText: { fontSize: tokens.fontSize.sm, color: tokens.colors.danger, paddingHorizontal: tokens.spacing.md },
});
```

### thin wrapper 패턴

역할별 페이지 파일은 공유 컴포넌트를 re-export하는 1줄 파일:

```typescript
// apps/mobile/src/app/(customer)/chat/index.tsx
export { default } from '@/components/chat/ChatRoomListScreen';

// apps/mobile/src/app/(customer)/chat/[id].tsx
export { default } from '@/components/chat/ChatRoomScreen';

// apps/mobile/src/app/(pro)/chat/index.tsx
export { default } from '@/components/chat/ChatRoomListScreen';

// apps/mobile/src/app/(pro)/chat/[id].tsx
export { default } from '@/components/chat/ChatRoomScreen';
```

### _layout.tsx 스크린 등록 패턴

```typescript
// apps/mobile/src/app/(customer)/_layout.tsx — chat 스크린 추가
return (
  <Stack screenOptions={{ headerShown: false }}>
    <Stack.Screen name="requests/index" />
    <Stack.Screen name="requests/new" options={{ title: '새 요청 만들기', headerShown: true }} />
    <Stack.Screen name="requests/[id]" options={{ title: '요청 상세', headerShown: true }} />
    <Stack.Screen name="chat/index" options={{ title: '채팅 목록', headerShown: true }} />
    <Stack.Screen name="chat/[id]" options={{ title: '채팅', headerShown: true }} />
  </Stack>
);

// apps/mobile/src/app/(pro)/_layout.tsx — chat 스크린 추가
return (
  <Stack screenOptions={{ headerShown: false }}>
    <Stack.Screen name="feed/index" />
    <Stack.Screen name="feed/[id]" options={{ title: '요청 상세', headerShown: true }} />
    <Stack.Screen name="categories/index" options={{ title: '카테고리 설정', headerShown: true }} />
    <Stack.Screen name="quotes/index" options={{ title: '내 견적', headerShown: true }} />
    <Stack.Screen name="chat/index" options={{ title: '채팅 목록', headerShown: true }} />
    <Stack.Screen name="chat/[id]" options={{ title: '채팅', headerShown: true }} />
  </Stack>
);
```

### router.d.ts 수동 업데이트 — 4개 신규 라우트 추가

```typescript
// hrefInputParams에 추가 (기존 항목들 뒤에):
| { pathname: `/(customer)/chat`; params?: Router.UnknownInputParams; }
| { pathname: `/(customer)/chat/[id]`; params?: Router.UnknownInputParams; }
| { pathname: `/(pro)/chat`; params?: Router.UnknownInputParams; }
| { pathname: `/(pro)/chat/[id]`; params?: Router.UnknownInputParams; }

// hrefOutputParams에 동일하게 추가 (UnknownInputParams → UnknownOutputParams)

// href에 추가:
| `/(customer)/chat${...}`           // static
| `/(customer)/chat/${string}${...}` // dynamic
| `/(pro)/chat${...}`                // static
| `/(pro)/chat/${string}${...}`      // dynamic
// + 동일 pathname 객체 형태도 추가 (router.d.ts 패턴 참조)
```

### 고객 헤더 채팅 버튼 추가 — requests/index.tsx

현재 `(customer)/requests/index.tsx`의 헤더에 로그아웃 버튼만 있음. "채팅" 버튼을 headerRow에 추가:

```typescript
// 현재 헤더 패턴 참조 (pro/feed/index.tsx의 headerRow와 동일 구조)
<View style={styles.headerRow}>
  <Text style={styles.screenTitle}>내 요청</Text>
  <View style={styles.headerButtons}>
    <TouchableOpacity onPress={() => router.push('/(customer)/chat')}>
      <Text style={styles.headerBtn}>채팅</Text>
    </TouchableOpacity>
    <TouchableOpacity onPress={() => router.push('/(customer)/requests/new')}>
      <Text style={styles.headerBtn}>새 요청</Text>
    </TouchableOpacity>
    <TouchableOpacity onPress={logout}>
      <Text style={styles.logoutBtn}>로그아웃</Text>
    </TouchableOpacity>
  </View>
</View>
```

> ⚠️ 현재 `requests/index.tsx`의 실제 헤더 패턴을 먼저 읽어서 정확한 스타일명과 구조를 확인 후 적용할 것.

### 고수 헤더 채팅 버튼 추가 — feed/index.tsx

현재 `(pro)/feed/index.tsx` 헤더에 `내 견적`, `카테고리`, `로그아웃` 버튼이 있음. "채팅" 버튼을 추가:

```typescript
// 기존 헤더 (5.3에서 구현됨):
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

// 수정 후 — "채팅" 버튼을 내 견적 앞에 추가:
<View style={styles.headerButtons}>
  <TouchableOpacity onPress={() => router.push('/(pro)/chat')}>
    <Text style={styles.headerBtn}>채팅</Text>
  </TouchableOpacity>
  <TouchableOpacity onPress={() => router.push('/(pro)/quotes')}>
    <Text style={styles.headerBtn}>내 견적</Text>
  </TouchableOpacity>
  {/* ... 카테고리, 로그아웃 ... */}
</View>
```

> ⚠️ 현재 `feed/index.tsx`를 직접 읽어서 실제 스타일명과 구조를 확인 후 적용할 것.

### acceptMutation.onSuccess 수정 — requests/[id].tsx

```typescript
// 현재 코드 (Story 5.2에서 구현됨):
const acceptMutation = useAcceptQuote<Error>({
  mutation: {
    onSuccess: () => {                        // ← 파라미터 없음
      setProcessingQuoteId(null);
      queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      router.replace('/(customer)/requests'); // ← 변경 대상
    },
    onError: ...
  },
});

// 변경 후:
const acceptMutation = useAcceptQuote<Error>({
  mutation: {
    onSuccess: (chatRoom) => {              // ← ChatRoomRead 파라미터 추가
      setProcessingQuoteId(null);
      queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      router.replace({ pathname: '/(customer)/chat/[id]', params: { id: chatRoom.id } });
    },
    onError: ...
  },
});
```

추가 import 필요:
```typescript
import { type ChatRoomRead } from '@gosoom/api-client'; // 또는 타입 추론으로 자동
```

### 알려진 함정

1. **`useListMessages` 대신 raw `list_messages` 사용 이유 ⚠️:**
   `useListMessages` 훅을 직접 쓰면 `params.after` 가 쿼리 키에 포함되어 `lastId` 갱신마다 쿼리 키가 바뀌고 `refetchInterval`이 리셋된다. 반드시 raw `list_messages` + 커스텀 `useQuery` 패턴을 사용할 것.

2. **`id` 파라미터 배열 타입 가드 필수 ✅:**
   `useLocalSearchParams<{ id: string | string[] }>()` — expo-router는 이론적으로 string[]을 반환 가능. `Array.isArray(rawId) ? rawId[0] : rawId` 처리 필수 (5.2/5.3 코드리뷰 교훈).

3. **TanStack Query `refetchInterval` unmount 시 자동 정리 ✅:**
   컴포넌트 언마운트 시 TanStack Query가 자동으로 `refetchInterval`을 정리한다. 별도 cleanup 불필요.

4. **메모리 누적 — `allMessages` 무한 증가 허용 (MVP) ✅:**
   폴링으로 메시지가 누적되나 MVP 수준에서 허용. 컴포넌트 마운트 해제 시 state가 초기화됨.

5. **`ChatRoomRead` import 위치:**
   `ChatRoomRead` 타입은 `@gosoom/api-client` 에서 직접 import (quotes.ts에서 사용되고 model/chatRoomRead.ts에서 생성됨).

6. **채팅 목록 `useListChatRooms` 쿼리 키 — cursor 포함 시 무한 스크롤 호환 확인:**
   `useListChatRooms({ mine: true, cursor })` 는 cursor가 변경될 때 새 쿼리를 만든다. processedCursors 패턴을 통해 중복 처리를 방지할 것.

7. **`tokens.fontWeight.medium` 존재하지 않음 ⚠️:**
   5.2 리뷰에서 확인됨. `tokens.fontWeight.regular`(400), `tokens.fontWeight.semibold`(600), `tokens.fontWeight.bold`(700)만 존재.

8. **공유 컴포넌트 role 분기 — hardcode 금지:**
   `ChatRoomListScreen`은 고객/고수 모두 사용. 탭 시 이동 경로를 `useAuth().user.role` 로 동적 분기할 것. 특정 역할로 하드코딩 금지.

### 웹 참고 파일 (구현 전 반드시 읽기)

```
apps/user-web/src/app/chat/page.tsx          — 채팅방 목록 (processedCursors 패턴, counterpartDisplayName 표시)
apps/user-web/src/app/chat/[id]/page.tsx     — 채팅방 (증분 폴링, useRef 패턴, 좌우 정렬, 낙관적 append)
```

### 참조 모바일 파일 (패턴 재사용)

```
apps/mobile/src/app/(customer)/_layout.tsx         — Stack 스크린 등록 패턴
apps/mobile/src/app/(pro)/_layout.tsx              — Stack 스크린 등록 패턴 (최신)
apps/mobile/src/app/(customer)/requests/index.tsx  — processedCursors + 헤더 버튼 패턴
apps/mobile/src/app/(customer)/requests/[id].tsx   — acceptMutation 현재 코드 (수정 대상)
apps/mobile/src/app/(pro)/feed/index.tsx           — 커스텀 헤더 버튼 패턴 (채팅 버튼 추가 대상)
apps/mobile/src/app/(pro)/quotes/index.tsx         — processedCursors 무한 스크롤 패턴
apps/mobile/.expo/types/router.d.ts                — 현재 라우트 타입 (추가 대상)
```

## Dev Agent Record

### Implementation Plan

- Task 1: 레이아웃 파일 2개에 chat 스크린 등록, router.d.ts 수동 업데이트, 헤더에 채팅 버튼 추가, acceptMutation.onSuccess를 채팅방 자동 이동으로 변경
- Task 2: 공유 컴포넌트 2개 신규 생성 (ChatRoomListScreen: processedCursors 커서 페이지네이션 + role 분기, ChatRoomScreen: 증분 폴링 2초 + dedup + 낙관적 append + 좌우 정렬)
- Task 3: 역할별 thin wrapper 4개 생성
- Task 4: tsc --noEmit 통과 확인 (useSendMessage<Error> 타입 명시로 HTTPValidationError 에러 해결)

### Completion Notes

- 모든 코드 구현 완료 및 `pnpm --filter mobile typecheck` 통과
- Task 4.2/4.3는 Expo Go 실기기 수동 테스트 항목으로 KTH 직접 확인 필요
- 핵심 구현 사항:
  - `useListMessages` 대신 raw `list_messages` + `useQuery(refetchInterval: 2000)` 패턴으로 증분 폴링 구현
  - `lastIdRef`로 `after` 파라미터 관리 (쿼리 키 안정화)
  - id-dedup으로 낙관적 append와 폴링 경쟁 조건 해결
  - `useAuth().user.role`로 채팅방 목록에서 역할별 라우팅 분기
  - `useSendMessage<Error>` 타입 파라미터 명시로 TypeScript 에러 해결

## File List

- `apps/mobile/src/app/(customer)/_layout.tsx` — 수정: chat/index, chat/[id] 스크린 등록
- `apps/mobile/src/app/(pro)/_layout.tsx` — 수정: chat/index, chat/[id] 스크린 등록
- `apps/mobile/.expo/types/router.d.ts` — 수정: 채팅 라우트 4개 추가
- `apps/mobile/src/app/(customer)/requests/index.tsx` — 수정: 헤더 채팅 버튼 추가
- `apps/mobile/src/app/(pro)/feed/index.tsx` — 수정: 헤더 채팅 버튼 추가
- `apps/mobile/src/app/(customer)/requests/[id].tsx` — 수정: acceptMutation.onSuccess 채팅 자동 이동
- `apps/mobile/src/components/chat/ChatRoomListScreen.tsx` — 신규: 공유 채팅방 목록 컴포넌트
- `apps/mobile/src/components/chat/ChatRoomScreen.tsx` — 신규: 공유 채팅방 화면 컴포넌트
- `apps/mobile/src/app/(customer)/chat/index.tsx` — 신규: thin wrapper
- `apps/mobile/src/app/(customer)/chat/[id].tsx` — 신규: thin wrapper
- `apps/mobile/src/app/(pro)/chat/index.tsx` — 신규: thin wrapper
- `apps/mobile/src/app/(pro)/chat/[id].tsx` — 신규: thin wrapper

## References

- [Source: epics.md#Story 5.4] — 유저 스토리, AC 전문
- [Story 4.4: apps/user-web/src/app/chat/[id]/page.tsx] — 증분 폴링 useRef 패턴 원형
- [Story 4.5: apps/user-web/src/app/chat/page.tsx] — 채팅방 목록 processedCursors 패턴 원형
- [Story 5.3: apps/mobile/src/app/(pro)/_layout.tsx] — Stack 스크린 등록 패턴
- [Story 5.3: apps/mobile/src/app/(pro)/feed/index.tsx] — 커스텀 헤더 버튼 패턴
- [Story 5.2: apps/mobile/src/app/(customer)/requests/[id].tsx] — acceptMutation 현재 코드
- [Source: packages/api-client/src/generated/chat-rooms/chat-rooms.ts] — useListChatRooms, list_messages, useSendMessage
- [Source: packages/api-client/src/generated/model/chatRoomListItem.ts] — ChatRoomListItem 타입
- [Source: packages/api-client/src/generated/model/messageRead.ts] — MessageRead 타입
- [Source: packages/api-client/src/generated/model/chatRoomRead.ts] — ChatRoomRead: { id, serviceRequestId, customerId, proId, quoteId, createdAt }
- [Source: packages/ui/src/tokens.ts] — 디자인 토큰
- [Source: apps/mobile/.expo/types/router.d.ts] — 현재 라우트 타입 (추가 대상)
- [Source: architecture.md] — 채팅 폴링 계약: refetchInterval 2~3초, after=lastId 증분 패턴

### Review Findings

**Patch (14건)**

- [x] [Review][Patch] `SafeAreaView` + `KeyboardAvoidingView` iOS inset 이중처리 — `edges={['top']}` 또는 `edges={['top', 'left', 'right']}`를 SafeAreaView에 지정해 bottom inset을 KAV에 위임 [ChatRoomScreen.tsx:82]
- [x] [Review][Patch] 화면 복귀 시 채팅 목록 stale + `processedCursors` Set 차단 — `useFocusEffect` 진입 시 `processedCursors.current.clear()`, `setAllRooms([])`, `setCursor(undefined)`, `queryClient.invalidateQueries` 순서로 실행 [ChatRoomListScreen.tsx:38, 52–54]
- [x] [Review][Patch] `FlatList`에 `onRefresh` 핸들러 없어 pull-to-refresh 작동 불가 [ChatRoomListScreen.tsx:116–130]
- [x] [Review][Patch] `handleRoomPress`에서 `user?.role`이 undefined/null 시 고수 경로로 폴백 — `user`가 없거나 role이 예상 외 값이면 고객이 `/(pro)/chat/[id]`로 이동 [ChatRoomListScreen.tsx:62–68]
- [x] [Review][Patch] `pendingRefresh` dead code — true로 설정하는 코드 없어 `isFetching` 분기가 실질적으로 아무것도 하지 않음 [ChatRoomListScreen.tsx:46–48]
- [x] [Review][Patch] 커서 페이지 append 시 중복 id 가드 없음 — 페이지 경계에서 서버가 동일 항목을 두 페이지에 반환할 경우 FlatList keyExtractor 충돌. `data.items.filter(r => !new Set(prev.map(r=>r.id)).has(r.id))` 적용 [ChatRoomListScreen.tsx:54]
- [x] [Review][Patch] 폴링 에러 시 `ChatRoomScreen` UI 피드백 없음 — `useQuery`의 `isError`를 구독하지 않아 네트워크 단절 시 빈 화면만 표시 [ChatRoomScreen.tsx:35–40]
- [x] [Review][Patch] `sendError`가 텍스트 입력 수정 시 지워지지 않음 — `onChangeText`에서 `setSendError(null)` 호출 필요 [ChatRoomScreen.tsx:103–107]
- [x] [Review][Patch] `lastIdRef` 갱신 경쟁 조건 — 폴링 응답의 마지막 아이템 ID가 `onSuccess`에서 설정한 ID보다 오래된 경우 ref가 역전됨. `lastIdRef.current`를 ID 비교(최신 우선) 후 갱신해야 함 [ChatRoomScreen.tsx:50, 66]
- [x] [Review][Patch] `pollData.items` 마지막 아이템 id null 가드 누락 — `lastIdRef.current = pollData.items[pollData.items.length - 1].id` 실행 전 `lastItem?.id` 존재 확인 필요 [ChatRoomScreen.tsx:50]
- [x] [Review][Patch] 채팅 전송 중 상태 label `'...'` → `'전송 중…'` 한국어로 수정 (AC8) [ChatRoomScreen.tsx:115]
- [x] [Review][Patch] `acceptMutation.onSuccess`에서 `chatRoom.id` null/undefined 시 폴백 없음 — id가 없으면 `/(customer)/chat/undefined`로 이동. `if (!chatRoom?.id)` 가드 + 폴백 라우트 추가 [requests/[id].tsx:117]
- [x] [Review][Patch] 빈 목록 상태가 초기 로드 직후 순간 flash — `!isPending && !isError && allRooms.length === 0` 조건에 `&& !isFetching` 추가 [ChatRoomListScreen.tsx:109]
- [x] [Review][Patch] `headerBtnText` fontSize 12 하드코딩 — `tokens.fontSize.sm` 사용 필요 [requests/index.tsx:211]

**Defer (5건)**

- [x] [Review][Defer] 초기 로드 후 첫 2초 빈 화면 flash — `isPending` false 후 첫 폴링 결과까지 빈 채팅 화면 표시. MVP 허용 범위. [ChatRoomScreen.tsx] — deferred, pre-existing design choice
- [x] [Review][Defer] `acceptMutation.onSuccess`에서 `invalidateQueries` await 없이 navigate — 기존 패턴과 동일하며 채팅 화면 진입에 영향 없음. [requests/[id].tsx:110–115] — deferred, pre-existing pattern
- [x] [Review][Defer] `useListChatRooms` 쿼리 키에 cursor 포함 여부 — orval 코드젠 내부 동작으로 이 파일에서 직접 제어 불가. [ChatRoomListScreen.tsx:41–43] — deferred, third-party generated code
- [x] [Review][Defer] 메시지 API 응답 정렬 방향 방어 로직 없음 — API 계약(오름차순)에 의존. 웹 버전도 동일 패턴. [ChatRoomScreen.tsx] — deferred, API contract assumption consistent with web
- [x] [Review][Defer] `nextCursor` 빈 문자열 처리 — 서버 API 스펙상 string | null이며 빈 문자열 반환 케이스 미정의. [ChatRoomListScreen.tsx:58–60] — deferred, API contract unclear

## Change Log

- 2026-06-11: Story 5.4 생성 (ready-for-dev)
- 2026-06-11: Story 5.4 구현 완료 — 모바일 채팅 기능 전체 구현 (레이아웃, 채팅방 목록, 채팅방 화면, 헤더 버튼, 견적 수락 자동 이동)
- 2026-06-11: 코드 리뷰 완료 — 0 decision-needed, 14 patch, 5 deferred, 11 dismissed
