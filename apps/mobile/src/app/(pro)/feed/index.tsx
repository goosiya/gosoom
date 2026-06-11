import { useEffect, useMemo, useRef, useState } from 'react';
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

import { Card, tokens } from '@gosoom/ui';
import {
  useListServiceRequestFeed,
  useListCategories,
  type ServiceRequestRead,
  type PageServiceRequestRead,
  type PageCategoryRead,
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
  matched: tokens.colors.textSecondary,
  completed: tokens.colors.textSecondary,
  cancelled: tokens.colors.danger,
};

function FeedSkeleton() {
  return (
    <View style={styles.skeletonCard}>
      <View style={styles.skeletonLine} />
      <View style={[styles.skeletonLine, styles.skeletonShort]} />
    </View>
  );
}

export default function ProFeedScreen() {
  const { logout, user } = useAuth();
  const router = useRouter();

  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<ServiceRequestRead[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
  const processedCursors = useRef(new Set<string | undefined>());
  const pendingRefresh = useRef(false);

  const { data, isPending, isFetching, isError, refetch } =
    useListServiceRequestFeed<PageServiceRequestRead, Error>({ cursor, limit: 20 });

  const { data: allCategories } = useListCategories<PageCategoryRead, Error>({ limit: 100 });

  const categoryMap = useMemo(
    () => new Map((allCategories?.items ?? []).map((c) => [c.id, c.name])),
    [allCategories],
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
    refetch();
  };

  const renderItem = ({ item }: { item: ServiceRequestRead }) => {
    const isMatched = item.status === 'matched';
    const categoryName = categoryMap.get(item.categoryId) ?? item.categoryId;
    const truncatedDesc =
      item.description.length > 50 ? item.description.slice(0, 50) + '…' : item.description;

    return (
      <TouchableOpacity
        onPress={() => {
          if (!isMatched) {
            router.push({ pathname: '/(pro)/feed/[id]', params: { id: item.id } });
          }
        }}
        activeOpacity={isMatched ? 1 : 0.7}
        style={isMatched ? styles.cardDimmed : undefined}
      >
        <Card>
          <View style={styles.itemRow}>
            <View style={styles.itemInfo}>
              <Text style={styles.itemCategory}>{categoryName}</Text>
              <Text style={styles.itemRegion}>{item.region}</Text>
              <Text style={styles.itemDesc}>{truncatedDesc}</Text>
              {isMatched && (
                <Text style={styles.matchedNote}>이미 매칭된 요청</Text>
              )}
            </View>
            <View
              style={[
                styles.badge,
                { borderColor: STATUS_COLORS[item.status] ?? tokens.colors.textSecondary },
              ]}
            >
              <Text
                style={[
                  styles.badgeText,
                  { color: STATUS_COLORS[item.status] ?? tokens.colors.textSecondary },
                ]}
              >
                {STATUS_LABELS[item.status] ?? item.status}
              </Text>
            </View>
          </View>
        </Card>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      {/* 커스텀 헤더 */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>요청 피드</Text>
          <Text style={styles.subtitle}>{user?.displayName}님</Text>
        </View>
        <View style={styles.headerButtons}>
          <TouchableOpacity onPress={() => router.push('/(pro)/chat')} style={styles.headerBtn}>
            <Text style={styles.headerBtnText}>채팅</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/(pro)/quotes')} style={styles.headerBtn}>
            <Text style={styles.headerBtnText}>내 견적</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/(pro)/categories')} style={styles.headerBtn}>
            <Text style={styles.headerBtnText}>카테고리</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={logout}>
            <Text style={styles.logoutText}>로그아웃</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* 로딩 스켈레톤 */}
      {isPending && (
        <View style={styles.listContainer}>
          <FeedSkeleton />
          <FeedSkeleton />
          <FeedSkeleton />
        </View>
      )}

      {/* 에러 상태 */}
      {isError && !isPending && (
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>피드를 불러오지 못했습니다.</Text>
          <TouchableOpacity onPress={handleRefresh} style={styles.retryBtn}>
            <Text style={styles.retryBtnText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* 빈 피드 상태 */}
      {!isPending && !isError && !isFetching && allItems.length === 0 && (
        <View style={styles.centerContent}>
          <Text style={styles.emptyText}>설정된 카테고리에 맞는 요청이 없습니다.</Text>
          <Text style={styles.emptySubText}>카테고리를 설정하면 관련 요청이 표시됩니다.</Text>
          <TouchableOpacity
            onPress={() => router.push('/(pro)/categories')}
            style={styles.retryBtn}
          >
            <Text style={styles.retryBtnText}>카테고리 설정하기</Text>
          </TouchableOpacity>
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
    fontSize: 12,
    color: tokens.colors.text,
  },
  logoutText: {
    fontSize: 12,
    color: tokens.colors.danger,
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
  itemInfo: { flex: 1, gap: 2 },
  itemCategory: {
    fontSize: tokens.fontSize.sm,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  itemRegion: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
  },
  itemDesc: {
    fontSize: 12,
    color: tokens.colors.textSecondary,
  },
  matchedNote: {
    fontSize: 12,
    color: tokens.colors.textSecondary,
    marginTop: 2,
  },
  badge: {
    borderWidth: 1,
    borderRadius: tokens.radius.sm,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  badgeText: { fontSize: 12, fontWeight: tokens.fontWeight.medium },
  cardDimmed: { opacity: 0.4 },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: tokens.spacing.md,
    padding: tokens.spacing.xl,
  },
  errorText: { fontSize: tokens.fontSize.base, color: tokens.colors.danger, textAlign: 'center' },
  emptyText: { fontSize: tokens.fontSize.base, color: tokens.colors.text, textAlign: 'center' },
  emptySubText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
    textAlign: 'center',
  },
  retryBtn: {
    paddingHorizontal: tokens.spacing.lg,
    paddingVertical: tokens.spacing.sm,
    borderRadius: tokens.radius.md,
    backgroundColor: tokens.colors.primary,
  },
  retryBtnText: { fontSize: tokens.fontSize.sm, color: '#fff', fontWeight: tokens.fontWeight.medium },
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
