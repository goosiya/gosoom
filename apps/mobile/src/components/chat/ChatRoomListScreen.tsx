import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFocusEffect, useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { Card, tokens } from '@gosoom/ui';
import {
  useListChatRooms,
  getListChatRoomsQueryKey,
  type PageChatRoomListItem,
  type ChatRoomListItem,
} from '@gosoom/api-client';

import { useAuth } from '@/features/auth';

function RoomSkeleton() {
  return (
    <View style={styles.skeletonCard}>
      <View style={styles.skeletonLine} />
      <View style={[styles.skeletonLine, styles.skeletonShort]} />
    </View>
  );
}

export default function ChatRoomListScreen() {
  const { user } = useAuth();
  const router = useRouter();

  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allRooms, setAllRooms] = useState<ChatRoomListItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
  const processedCursors = useRef(new Set<string | undefined>());

  const { data, isPending, isFetching, isError } = useListChatRooms<PageChatRoomListItem, Error>(
    { mine: true, ...(cursor ? { cursor } : {}) },
  );

  const queryClient = useQueryClient();

  useFocusEffect(
    useCallback(() => {
      processedCursors.current.clear();
      setCursor(undefined);
      setNextCursor(undefined);
      queryClient.invalidateQueries({ queryKey: getListChatRoomsQueryKey() });
    }, [queryClient]),
  );

  useEffect(() => {
    if (isFetching) return;
    if (!data?.items) return;
    if (processedCursors.current.has(cursor)) return;
    processedCursors.current.add(cursor);
    setAllRooms((prev) => {
      if (cursor === undefined) return data.items;
      const existingIds = new Set(prev.map((r) => r.id));
      return [...prev, ...data.items.filter((r) => !existingIds.has(r.id))];
    });
    setNextCursor(data.nextCursor ?? null);
  }, [data, cursor, isFetching]);

  const handleLoadMore = () => {
    if (nextCursor && !isFetching) setCursor(nextCursor);
  };

  const handleRefresh = () => {
    processedCursors.current.clear();
    setCursor(undefined);
    setNextCursor(undefined);
    queryClient.invalidateQueries({ queryKey: getListChatRoomsQueryKey() });
  };

  const handleRoomPress = (roomId: string) => {
    if (!user?.role) return;
    if (user.role === 'customer') {
      router.push({ pathname: '/(customer)/chat/[id]', params: { id: roomId } });
    } else {
      router.push({ pathname: '/(pro)/chat/[id]', params: { id: roomId } });
    }
  };

  const truncate = (text: string, max: number) =>
    text.length > max ? text.slice(0, max) + '…' : text;

  const renderItem = ({ item }: { item: ChatRoomListItem }) => (
    <TouchableOpacity onPress={() => handleRoomPress(item.id)}>
      <Card>
        <View style={styles.itemRow}>
          <Text style={styles.counterpart}>{item.counterpartDisplayName}</Text>
          {item.serviceRequest ? (
            <View style={styles.requestInfo}>
              <Text style={styles.region}>{item.serviceRequest.region}</Text>
              <Text style={styles.description}>
                {truncate(item.serviceRequest.description, 50)}
              </Text>
            </View>
          ) : (
            <Text style={styles.deletedRequest}>(삭제된 요청)</Text>
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safe}>
      {isPending && (
        <View style={styles.listContainer}>
          <RoomSkeleton />
          <RoomSkeleton />
          <RoomSkeleton />
        </View>
      )}

      {isError && !isPending && (
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>채팅 목록을 불러오지 못했습니다.</Text>
        </View>
      )}

      {!isPending && !isError && allRooms.length === 0 && !isFetching && (
        <View style={styles.centerContent}>
          <Text style={styles.emptyText}>참여 중인 채팅방이 없습니다.</Text>
        </View>
      )}

      {!isPending && !isError && allRooms.length > 0 && (
        <FlatList
          data={allRooms}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.listContainer}
          onEndReached={handleLoadMore}
          onEndReachedThreshold={0.3}
          onRefresh={handleRefresh}
          refreshing={isFetching && cursor === undefined}
          ListFooterComponent={
            isFetching && cursor !== undefined ? (
              <ActivityIndicator style={styles.loadingMore} color={tokens.colors.primary} />
            ) : null
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  listContainer: {
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  itemRow: {
    padding: tokens.spacing.md,
    gap: tokens.spacing.xs,
  },
  counterpart: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  requestInfo: { gap: 2 },
  region: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
  },
  description: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
  },
  deletedRequest: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: tokens.spacing.xl,
  },
  errorText: { fontSize: tokens.fontSize.base, color: tokens.colors.danger, textAlign: 'center' },
  emptyText: { fontSize: tokens.fontSize.base, color: tokens.colors.textSecondary, textAlign: 'center' },
  loadingMore: { marginVertical: tokens.spacing.md },
  skeletonCard: {
    backgroundColor: tokens.colors.backgroundSecondary,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  skeletonLine: {
    height: 16,
    backgroundColor: tokens.colors.border,
    borderRadius: tokens.radius.sm,
  },
  skeletonShort: { width: '60%' },
});
