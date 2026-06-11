import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';

import { Button, Input, tokens } from '@gosoom/ui';
import {
  useGetServiceRequestFeedDetail,
  useCreateServiceRequestQuote,
  useListCategories,
  type ServiceRequestRead,
  type PageCategoryRead,
} from '@gosoom/api-client';

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

export default function FeedDetailScreen() {
  const { id: rawId } = useLocalSearchParams<{ id: string | string[] }>();
  const id = Array.isArray(rawId) ? rawId[0] : rawId;
  const router = useRouter();

  const [priceInput, setPriceInput] = useState('');
  const [message, setMessage] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { data: request, isPending, isError } =
    useGetServiceRequestFeedDetail<ServiceRequestRead, Error>(id);

  const { data: allCategories } = useListCategories<PageCategoryRead, Error>({ limit: 100 });

  const categoryMap = useMemo(
    () => new Map((allCategories?.items ?? []).map((c) => [c.id, c.name])),
    [allCategories],
  );

  const quoteMutation = useCreateServiceRequestQuote({
    mutation: {
      onSuccess: () => {
        router.replace('/(pro)/feed');
      },
      onError: (err) => setErrorMsg((err as Error)?.message ?? '견적 제출에 실패했습니다.'),
    },
  });

  const handleSubmit = () => {
    setValidationError(null);
    setErrorMsg(null);

    const priceNum = Number(priceInput);
    if (!priceInput || isNaN(priceNum) || priceNum <= 0) {
      setValidationError('금액은 0보다 큰 숫자를 입력해 주세요.');
      return;
    }
    if (!message.trim()) {
      setValidationError('메시지를 입력해 주세요.');
      return;
    }

    quoteMutation.mutate({
      requestId: id,
      data: { price: priceNum, message: message.trim() },
    });
  };

  if (isPending) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerContent}>
          <ActivityIndicator color={tokens.colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (isError || !request) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>요청 정보를 불러오지 못했습니다.</Text>
          <Button label="뒤로 가기" onPress={() => router.back()} />
        </View>
      </SafeAreaView>
    );
  }

  const isOpen = request.status === 'open';
  const categoryName = categoryMap.get(request.categoryId) ?? request.categoryId;

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={styles.content}>
          {/* 요청 정보 섹션 */}
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.sectionTitle}>요청 정보</Text>
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

            <View style={styles.fieldList}>
              <View style={styles.field}>
                <Text style={styles.fieldLabel}>카테고리</Text>
                <Text style={styles.fieldValue}>{categoryName}</Text>
              </View>
              <View style={styles.field}>
                <Text style={styles.fieldLabel}>지역</Text>
                <Text style={styles.fieldValue}>{request.region}</Text>
              </View>
              <View style={styles.field}>
                <Text style={styles.fieldLabel}>요청 내용</Text>
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
            </View>
          </View>

          {/* 견적 제안 폼 — open 상태만 */}
          {isOpen && (
            <View style={styles.card}>
              <Text style={styles.sectionTitle}>견적 제안</Text>

              <View style={styles.formSection}>
                <Text style={styles.label}>금액 (원) *</Text>
                <Input
                  value={priceInput}
                  onChangeText={setPriceInput}
                  placeholder="예: 50000"
                  keyboardType="numeric"
                  editable={!quoteMutation.isPending}
                />
              </View>

              <View style={styles.formSection}>
                <Text style={styles.label}>메시지 *</Text>
                <TextInput
                  value={message}
                  onChangeText={setMessage}
                  multiline
                  numberOfLines={4}
                  style={[styles.textarea, quoteMutation.isPending && styles.disabled]}
                  placeholder="고객에게 전달할 메시지를 작성하세요"
                  placeholderTextColor={tokens.colors.textSecondary}
                  editable={!quoteMutation.isPending}
                />
              </View>

              {validationError && (
                <Text style={styles.errorText}>{validationError}</Text>
              )}
              {errorMsg && (
                <Text style={styles.errorText}>{errorMsg}</Text>
              )}

              <Button
                label={quoteMutation.isPending ? '제출 중…' : '견적 제안하기'}
                onPress={handleSubmit}
                disabled={quoteMutation.isPending}
              />
            </View>
          )}

          {/* 비오픈 상태 안내 */}
          {!isOpen && (
            <View style={styles.card}>
              <Text style={styles.infoText}>이미 매칭되었거나 마감된 요청입니다.</Text>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  flex: { flex: 1 },
  content: { padding: tokens.spacing.lg, gap: tokens.spacing.md },
  card: {
    backgroundColor: tokens.colors.backgroundSecondary,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
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
  formSection: { gap: tokens.spacing.xs },
  label: {
    fontSize: tokens.fontSize.sm,
    fontWeight: tokens.fontWeight.medium,
    color: tokens.colors.text,
  },
  textarea: {
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    paddingVertical: tokens.spacing.md,
    paddingHorizontal: tokens.spacing.md,
    fontSize: tokens.fontSize.base,
    color: tokens.colors.text,
    backgroundColor: tokens.colors.background,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  disabled: { opacity: 0.5 },
  errorText: { fontSize: tokens.fontSize.sm, color: tokens.colors.danger },
  infoText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
    textAlign: 'center',
    paddingVertical: tokens.spacing.sm,
  },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: tokens.spacing.xl,
  },
});
