import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { Button, Card, tokens } from '@gosoom/ui';
import {
  useListMyServiceRequests,
  getListMyServiceRequestsQueryKey,
  type ServiceRequestRead,
} from '@gosoom/api-client';

import { useAuth } from '@/features/auth';

const STATUS_LABELS: Record<string, string> = {
  open: '접수됨',
  matched: '매칭됨',
  completed: '완료됨',
  cancelled: '취소됨',
};

const STATUS_COLORS: Record<string, string> = {
  open: tokens.colors.primary,
  matched: tokens.colors.success,
  completed: tokens.colors.textSecondary,
  cancelled: tokens.colors.danger,
};

function RequestSkeleton() {
  return (
    <View style={styles.skeletonCard}>
      <View style={styles.skeletonLine} />
      <View style={[styles.skeletonLine, styles.skeletonShort]} />
    </View>
  );
}

export default function CustomerRequestsScreen() {
  const { logout, user } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<ServiceRequestRead[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
  const processedCursors = useRef(new Set<string | undefined>());
  const pendingRefresh = useRef(false);

  const { data, isPending, isFetching, isError } = useListMyServiceRequests(
    { cursor, limit: 20 },
  );

  useEffect(() => {
    if (!data?.items) return;
    if (pendingRefresh.current) {
      if (!isFetching) return;
      pendingRefresh.current = false;
      return;
    }
    if (isFetching) return;
    if (processedCursors.current.has(cursor)) return;
    processedCursors.current.add(cursor);
    setAllItems((prev) => (cursor === undefined ? data.items : [...prev, ...data.items]));
    setNextCursor(data.nextCursor ?? null);
  }, [data, cursor, isFetching]);

  const handleLoadMore = () => {
    if (nextCursor && !isFetching) setCursor(nextCursor);
  };

  const handleRefresh = () => {
    pendingRefresh.current = true;
    processedCursors.current = new Set();
    setAllItems([]);
    setNextCursor(undefined);
    setCursor(undefined);
    queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
  };

  const renderItem = ({ item }: { item: ServiceRequestRead }) => (
    <TouchableOpacity onPress={() => router.push(`/(customer)/requests/${item.id}`)}>
      <Card>
        <View style={styles.itemRow}>
          <View style={styles.itemInfo}>
            <Text style={styles.itemDescription} numberOfLines={2}>
              {item.description}
            </Text>
            <Text style={styles.itemRegion}>{item.region}</Text>
            <Text style={styles.itemDate}>
              {new Date(item.createdAt).toLocaleDateString('ko-KR')}
            </Text>
          </View>
          <View style={[styles.badge, { borderColor: STATUS_COLORS[item.status] ?? tokens.colors.textSecondary }]}>
            <Text style={[styles.badgeText, { color: STATUS_COLORS[item.status] ?? tokens.colors.textSecondary }]}>
              {STATUS_LABELS[item.status] ?? item.status}
            </Text>
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.safe}>
      {/* 헤더 */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>내 서비스 요청</Text>
          <Text style={styles.subtitle}>{user?.displayName}님 안녕하세요</Text>
        </View>
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={() => router.push('/(customer)/chat')} style={styles.headerBtn}>
            <Text style={styles.headerBtnText}>채팅</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={logout}>
            <Text style={styles.logoutText}>로그아웃</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* 로딩 스켈레톤 */}
      {isPending && (
        <View style={styles.listContainer}>
          <RequestSkeleton />
          <RequestSkeleton />
          <RequestSkeleton />
        </View>
      )}

      {/* 에러 상태 */}
      {isError && !isPending && (
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>요청 목록을 불러오지 못했습니다.</Text>
          <Button label="다시 시도" onPress={handleRefresh} />
        </View>
      )}

      {/* 빈 목록 상태 */}
      {!isPending && !isError && allItems.length === 0 && (
        <View style={styles.centerContent}>
          <Text style={styles.emptyText}>아직 요청이 없습니다.</Text>
          <Text style={styles.emptySubText}>첫 번째 서비스 요청을 만들어 보세요.</Text>
          <Button label="새 요청 만들기" onPress={() => router.push('/(customer)/requests/new')} />
        </View>
      )}

      {/* 목록 */}
      {!isPending && !isError && allItems.length > 0 && (
        <FlatList
          data={allItems}
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

      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push('/(customer)/requests/new')}
        accessibilityLabel="새 요청 만들기"
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.sm,
  },
  title: {
    fontSize: tokens.fontSize.lg,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  subtitle: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
    marginTop: 2,
  },
  headerButtons: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
  },
  headerBtn: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.sm,
    borderWidth: 1,
    borderColor: tokens.colors.border,
  },
  headerBtnText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.text,
  },
  logoutText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.danger,
    paddingTop: tokens.spacing.xs,
  },
  listContainer: {
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: tokens.spacing.sm,
    padding: tokens.spacing.md,
  },
  itemInfo: { flex: 1 },
  itemDescription: {
    fontSize: tokens.fontSize.base,
    color: tokens.colors.text,
    fontWeight: tokens.fontWeight.medium,
    marginBottom: 4,
  },
  itemRegion: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
    marginBottom: 2,
  },
  itemDate: {
    fontSize: 12,
    color: tokens.colors.textSecondary,
  },
  badge: {
    borderWidth: 1,
    borderRadius: tokens.radius.sm,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  badgeText: {
    fontSize: 12,
    fontWeight: tokens.fontWeight.medium,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: tokens.spacing.md,
    padding: tokens.spacing.xl,
  },
  errorText: { fontSize: tokens.fontSize.base, color: tokens.colors.danger, textAlign: 'center' },
  emptyText: { fontSize: tokens.fontSize.base, color: tokens.colors.text, textAlign: 'center' },
  emptySubText: { fontSize: tokens.fontSize.sm, color: tokens.colors.textSecondary, textAlign: 'center' },
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
  fab: {
    position: 'absolute',
    bottom: tokens.spacing.xl,
    right: tokens.spacing.xl,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: tokens.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  fabText: { fontSize: 28, color: '#fff', lineHeight: 32 },
});
