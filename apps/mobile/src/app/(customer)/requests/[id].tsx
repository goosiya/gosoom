import { useState } from 'react';
import {
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { Button, Card, tokens } from '@gosoom/ui';
import {
  useGetServiceRequest,
  useUpdateServiceRequestStatus,
  useListServiceRequestQuotes,
  useListCategories,
  useAcceptQuote,
  useRejectQuote,
  getGetServiceRequestQueryKey,
  getListMyServiceRequestsQueryKey,
  getListServiceRequestQuotesQueryKey,
  type QuoteWithProInfo,
  type ServiceRequestRead,
  type PageQuoteWithProInfo,
  type ChatRoomRead,
} from '@gosoom/api-client';

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

function DetailSkeleton() {
  return (
    <View style={styles.skeletonBlock}>
      <View style={styles.skeletonLine} />
      <View style={styles.skeletonLine} />
      <View style={[styles.skeletonLine, styles.skeletonShort]} />
    </View>
  );
}

function QuoteSkeleton() {
  return (
    <View style={styles.skeletonCard}>
      <View style={styles.skeletonLine} />
      <View style={[styles.skeletonLine, styles.skeletonShort]} />
    </View>
  );
}

export default function RequestDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const [statusError, setStatusError] = useState<string | null>(null);
  const [acceptErrors, setAcceptErrors] = useState<Record<string, string>>({});
  const [rejectErrors, setRejectErrors] = useState<Record<string, string>>({});
  const [processingQuoteId, setProcessingQuoteId] = useState<{ action: 'accept' | 'reject'; id: string } | null>(null);

  const { data: request, isPending, isError } =
    useGetServiceRequest<ServiceRequestRead, Error>(id);

  const shouldShowQuotes = request?.status === 'open' || request?.status === 'matched';

  const { data: quotesData, isPending: quotesLoading, isError: quotesError } =
    useListServiceRequestQuotes<PageQuoteWithProInfo, Error>(id);

  const { data: categoriesData } = useListCategories({ limit: 100 });
  const categoryMap = new Map(
    (categoriesData?.items ?? []).map((c) => [c.id, c.name]),
  );

  const statusMutation = useUpdateServiceRequestStatus<Error>({
    mutation: {
      onSuccess: () => {
        setStatusError(null);
        queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      },
      onError: (err) => setStatusError(err.message),
    },
  });

  const acceptMutation = useAcceptQuote<Error>({
    mutation: {
      onSuccess: (chatRoom: ChatRoomRead) => {
        setProcessingQuoteId(null);
        queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
        if (chatRoom?.id) {
          router.replace({ pathname: '/(customer)/chat/[id]', params: { id: chatRoom.id } });
        } else {
          router.replace('/(customer)/requests');
        }
      },
      onError: (err, variables) => {
        setProcessingQuoteId(null);
        setAcceptErrors((prev) => ({ ...prev, [variables.quoteId]: err.message }));
      },
    },
  });

  const rejectMutation = useRejectQuote<Error>({
    mutation: {
      onSuccess: (_data, variables) => {
        setProcessingQuoteId(null);
        setRejectErrors((prev) => {
          const next = { ...prev };
          delete next[variables.quoteId];
          return next;
        });
        queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
      },
      onError: (err, variables) => {
        setProcessingQuoteId(null);
        setRejectErrors((prev) => ({ ...prev, [variables.quoteId]: err.message }));
      },
    },
  });

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* 상세 로딩 */}
        {isPending && <DetailSkeleton />}

        {/* 상세 에러 */}
        {isError && (
          <Card>
            <View style={styles.centerPad}>
              <Text style={styles.errorText}>요청 정보를 불러오지 못했습니다.</Text>
            </View>
          </Card>
        )}

        {/* 요청 정보 카드 */}
        {request && (
          <Card>
            <View style={styles.cardPad}>
              {/* 헤더: 제목 + 상태 배지 */}
              <View style={styles.cardHeader}>
                <Text style={styles.sectionTitle}>요청 상세</Text>
                <View
                  style={[
                    styles.badge,
                    { borderColor: STATUS_COLORS[request.status] ?? tokens.colors.textSecondary },
                  ]}
                >
                  <Text
                    style={[
                      styles.badgeText,
                      { color: STATUS_COLORS[request.status] ?? tokens.colors.textSecondary },
                    ]}
                  >
                    {STATUS_LABELS[request.status] ?? request.status}
                  </Text>
                </View>
              </View>

              {/* 상세 필드 */}
              <View style={styles.fieldList}>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>카테고리</Text>
                  <Text style={styles.fieldValue}>
                    {categoryMap.get(request.categoryId) ?? request.categoryId}
                  </Text>
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>지역</Text>
                  <Text style={styles.fieldValue}>{request.region}</Text>
                </View>
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>설명</Text>
                  <Text style={styles.fieldValue}>{request.description}</Text>
                </View>
                {request.desiredSchedule && (
                  <View style={styles.field}>
                    <Text style={styles.fieldLabel}>희망 일정</Text>
                    <Text style={styles.fieldValue}>{request.desiredSchedule}</Text>
                  </View>
                )}
                {request.budget != null && (
                  <View style={styles.field}>
                    <Text style={styles.fieldLabel}>예산</Text>
                    <Text style={styles.fieldValue}>
                      {request.budget.toLocaleString('ko-KR')}원
                    </Text>
                  </View>
                )}
                <View style={styles.field}>
                  <Text style={styles.fieldLabel}>생성일</Text>
                  <Text style={styles.fieldValue}>{formatDate(request.createdAt)}</Text>
                </View>
              </View>

              {/* 구분선 */}
              <View style={styles.divider} />

              {/* 액션 버튼 */}
              <View style={styles.actionRow}>
                {request.status === 'open' && (
                  <Button
                    label={statusMutation.isPending ? '처리 중…' : '취소하기'}
                    onPress={() =>
                      statusMutation.mutate({ requestId: id, data: { action: 'cancel' } })
                    }
                    disabled={statusMutation.isPending}
                  />
                )}
                {request.status === 'matched' && (
                  <Button
                    label={statusMutation.isPending ? '처리 중…' : '완료하기'}
                    onPress={() =>
                      statusMutation.mutate({ requestId: id, data: { action: 'complete' } })
                    }
                    disabled={statusMutation.isPending}
                  />
                )}
              </View>
              {statusError && <Text style={styles.errorText}>{statusError}</Text>}
            </View>
          </Card>
        )}

        {/* 견적 섹션 — open/matched 상태에서만 표시 (AC4) */}
        {shouldShowQuotes && (
          <>
            <Text style={styles.quotesTitle}>받은 견적</Text>

            {/* 견적 로딩 */}
            {quotesLoading && (
              <>
                <QuoteSkeleton />
                <QuoteSkeleton />
              </>
            )}

            {/* 견적 에러 */}
            {quotesError && !quotesLoading && (
              <Card>
                <View style={styles.centerPad}>
                  <Text style={styles.errorText}>견적을 불러오지 못했습니다.</Text>
                </View>
              </Card>
            )}

            {/* 빈 견적 목록 */}
            {!quotesLoading && !quotesError && (!quotesData?.items || quotesData.items.length === 0) && (
              <Card>
                <View style={styles.centerPad}>
                  <Text style={styles.emptyText}>아직 받은 견적이 없습니다.</Text>
                </View>
              </Card>
            )}

            {/* 견적 목록 */}
            {!quotesLoading && !quotesError && quotesData?.items && quotesData.items.length > 0 && (
              <View style={styles.quoteList}>
                {quotesData.items.map((quote: QuoteWithProInfo) => (
                  <Card key={quote.id}>
                    <View style={styles.cardPad}>
                      {/* 고수명 + 견적 상태 */}
                      <View style={styles.cardHeader}>
                        <Text style={styles.proName}>{quote.pro.displayName}</Text>
                        <View
                          style={[
                            styles.badge,
                            {
                              borderColor:
                                QUOTE_STATUS_COLORS[quote.status] ?? tokens.colors.textSecondary,
                            },
                          ]}
                        >
                          <Text
                            style={[
                              styles.badgeText,
                              {
                                color:
                                  QUOTE_STATUS_COLORS[quote.status] ?? tokens.colors.textSecondary,
                              },
                            ]}
                          >
                            {QUOTE_STATUS_LABELS[quote.status] ?? quote.status}
                          </Text>
                        </View>
                      </View>

                      {/* 금액 */}
                      <Text style={styles.price}>{quote.price.toLocaleString('ko-KR')}원</Text>

                      {/* 메시지 */}
                      <Text style={styles.message}>{quote.message}</Text>

                      {/* 수락/거절 버튼 (open 상태 + pending 견적만) */}
                      {request.status === 'open' && quote.status === 'pending' && (
                        <View style={styles.quoteActions}>
                          <Button
                            label={processingQuoteId?.id === quote.id && processingQuoteId.action === 'accept' ? '처리 중…' : '수락하기'}
                            onPress={() => {
                              setProcessingQuoteId({ action: 'accept', id: quote.id });
                              acceptMutation.mutate({ quoteId: quote.id });
                            }}
                            disabled={processingQuoteId !== null}
                          />
                          <Button
                            label={processingQuoteId?.id === quote.id && processingQuoteId.action === 'reject' ? '처리 중…' : '거절하기'}
                            onPress={() => {
                              setProcessingQuoteId({ action: 'reject', id: quote.id });
                              rejectMutation.mutate({ quoteId: quote.id });
                            }}
                            disabled={processingQuoteId !== null}
                          />
                        </View>
                      )}
                      {acceptErrors[quote.id] && <Text style={styles.errorText}>{acceptErrors[quote.id]}</Text>}
                      {rejectErrors[quote.id] && (
                        <Text style={styles.errorText}>{rejectErrors[quote.id]}</Text>
                      )}
                    </View>
                  </Card>
                ))}
              </View>
            )}
          </>
        )}

        {/* 하단 여백 */}
        <View style={{ height: tokens.spacing.xl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  content: { padding: tokens.spacing.md, gap: tokens.spacing.md },
  cardPad: { padding: tokens.spacing.md, gap: tokens.spacing.sm },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  badge: {
    borderWidth: 1,
    borderRadius: tokens.radius.sm,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 2,
  },
  badgeText: { fontSize: 12, fontWeight: tokens.fontWeight.medium },
  fieldList: { gap: tokens.spacing.sm },
  field: { gap: 2 },
  fieldLabel: {
    fontSize: 12,
    color: tokens.colors.textSecondary,
    fontWeight: tokens.fontWeight.medium,
  },
  fieldValue: { fontSize: tokens.fontSize.sm, color: tokens.colors.text },
  divider: {
    height: 1,
    backgroundColor: tokens.colors.border,
    marginVertical: tokens.spacing.xs,
  },
  actionRow: { flexDirection: 'row', gap: tokens.spacing.sm },
  quotesTitle: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
    marginTop: tokens.spacing.sm,
  },
  quoteList: { gap: tokens.spacing.sm },
  proName: {
    fontSize: tokens.fontSize.sm,
    fontWeight: tokens.fontWeight.medium,
    color: tokens.colors.text,
  },
  price: {
    fontSize: tokens.fontSize.lg,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.primary,
  },
  message: { fontSize: tokens.fontSize.sm, color: tokens.colors.textSecondary },
  quoteActions: { flexDirection: 'row', gap: tokens.spacing.sm, paddingTop: tokens.spacing.xs },
  centerPad: { padding: tokens.spacing.lg, alignItems: 'center' },
  errorText: { fontSize: tokens.fontSize.sm, color: tokens.colors.danger },
  emptyText: { fontSize: tokens.fontSize.sm, color: tokens.colors.textSecondary },
  skeletonBlock: {
    backgroundColor: tokens.colors.backgroundSecondary,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
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
