import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, Card, tokens } from '@gosoom/ui';
import {
  useListMyQuotes,
  type PageQuoteListItem,
} from '@gosoom/api-client';

type QuoteListItem = PageQuoteListItem['items'][0];

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

const QUOTE_STATUS_LABELS: Record<string, string> = {
  pending: '검토 중',
  accepted: '수락됨',
  rejected: '거절됨',
  closed: '마감됨',
};

const QUOTE_STATUS_COLORS: Record<string, string> = {
  pending: tokens.colors.primary,
  accepted: tokens.colors.success,
  rejected: tokens.colors.danger,
  closed: tokens.colors.textSecondary,
};

const formatPrice = (price: number) => price.toLocaleString('ko-KR') + '원';

function QuoteSkeleton() {
  return (
    <View style={styles.skeletonCard}>
      <View style={styles.skeletonLine} />
      <View style={[styles.skeletonLine, styles.skeletonShort]} />
    </View>
  );
}

export default function MyQuotesScreen() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<QuoteListItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
  const processedCursors = useRef(new Set<string | undefined>());
  const pendingRefresh = useRef(false);

  const { data, isPending, isFetching, isError, refetch } =
    useListMyQuotes<PageQuoteListItem, Error>({ cursor, limit: 20 });

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

  const renderItem = ({ item }: { item: QuoteListItem }) => {
    const req = item.serviceRequest;
    return (
      <Card>
        <View style={styles.itemPad}>
          {/* 금액 + 견적 상태 */}
          <View style={styles.rowBetween}>
            <Text style={styles.price}>{formatPrice(item.price)}</Text>
            <View
              style={[
                styles.badge,
                { borderColor: QUOTE_STATUS_COLORS[item.status] ?? tokens.colors.textSecondary },
              ]}
            >
              <Text
                style={[
                  styles.badgeText,
                  { color: QUOTE_STATUS_COLORS[item.status] ?? tokens.colors.textSecondary },
                ]}
              >
                {QUOTE_STATUS_LABELS[item.status] ?? item.status}
              </Text>
            </View>
          </View>

          {/* 요청 정보 */}
          {req ? (
            <View style={styles.reqInfo}>
              <View style={styles.divider} />
              <View style={styles.rowBetween}>
                <View style={styles.reqDetail}>
                  <Text style={styles.reqRegion}>{req.region}</Text>
                  <Text style={styles.reqDesc} numberOfLines={2}>
                    {req.description}
                  </Text>
                </View>
                <View
                  style={[
                    styles.badge,
                    { borderColor: STATUS_COLORS[req.status ?? ''] ?? tokens.colors.textSecondary },
                  ]}
                >
                  <Text
                    style={[
                      styles.badgeText,
                      { color: STATUS_COLORS[req.status ?? ''] ?? tokens.colors.textSecondary },
                    ]}
                  >
                    {STATUS_LABELS[req.status ?? ''] ?? req.status}
                  </Text>
                </View>
              </View>
            </View>
          ) : (
            <Text style={styles.deletedReq}>(삭제된 요청)</Text>
          )}
        </View>
      </Card>
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      {/* 로딩 스켈레톤 */}
      {isPending && (
        <View style={styles.listContainer}>
          <QuoteSkeleton />
          <QuoteSkeleton />
          <QuoteSkeleton />
        </View>
      )}

      {/* 에러 상태 */}
      {isError && !isPending && (
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>견적 목록을 불러오지 못했습니다.</Text>
          <Button label="다시 시도" onPress={handleRefresh} />
        </View>
      )}

      {/* 빈 목록 */}
      {!isPending && !isError && !isFetching && allItems.length === 0 && (
        <View style={styles.centerContent}>
          <Text style={styles.emptyText}>제안한 견적이 없습니다.</Text>
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
  listContainer: {
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  itemPad: { padding: tokens.spacing.md, gap: tokens.spacing.sm },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  price: {
    fontSize: tokens.fontSize.lg,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.primary,
  },
  badge: {
    borderWidth: 1,
    borderRadius: tokens.radius.sm,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  badgeText: { fontSize: 12, fontWeight: tokens.fontWeight.medium },
  reqInfo: { gap: tokens.spacing.xs },
  divider: {
    height: 1,
    backgroundColor: tokens.colors.border,
  },
  reqDetail: { flex: 1, paddingRight: tokens.spacing.sm },
  reqRegion: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
  },
  reqDesc: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.text,
    marginTop: 2,
  },
  deletedReq: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
    fontStyle: 'italic',
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: tokens.spacing.md,
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
