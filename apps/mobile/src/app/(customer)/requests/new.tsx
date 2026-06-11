import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { Button, Input, tokens } from '@gosoom/ui';
import {
  useCreateServiceRequest,
  useListCategories,
  getListMyServiceRequestsQueryKey,
} from '@gosoom/api-client';

export default function RequestNewScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedCategoryId, setSelectedCategoryId] = useState('');
  const [region, setRegion] = useState('');
  const [description, setDescription] = useState('');
  const [desiredSchedule, setDesiredSchedule] = useState('');
  const [budget, setBudget] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { data: categoriesData, isPending: categoriesLoading, isError: categoriesError } = useListCategories({ limit: 100 });

  const createMutation = useCreateServiceRequest<Error>({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
        router.replace('/(customer)/requests');
      },
      onError: (err) => {
        setErrorMsg(err.message);
      },
    },
  });

  const handleSubmit = () => {
    setValidationError(null);
    setErrorMsg(null);

    if (!selectedCategoryId) {
      setValidationError('카테고리를 선택해 주세요.');
      return;
    }
    if (!region.trim()) {
      setValidationError('지역을 입력해 주세요.');
      return;
    }
    if (!description.trim()) {
      setValidationError('설명을 입력해 주세요.');
      return;
    }

    const parsedBudget = budget !== '' ? parseInt(budget, 10) : undefined;
    if (parsedBudget !== undefined && (Number.isNaN(parsedBudget) || parsedBudget < 0)) {
      setValidationError('예산은 0 이상의 숫자를 입력해 주세요.');
      return;
    }

    createMutation.mutate({
      data: {
        categoryId: selectedCategoryId,
        region: region.trim(),
        description: description.trim(),
        desiredSchedule: desiredSchedule.trim() || undefined,
        budget: parsedBudget,
      },
    });
  };

  const isPending = createMutation.isPending;

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={styles.content}>
          {/* 카테고리 선택 */}
          <View style={styles.section}>
            <Text style={styles.label}>카테고리 *</Text>
            {categoriesLoading ? (
              <Text style={styles.loadingText}>카테고리 로딩 중…</Text>
            ) : categoriesError ? (
              <Text style={styles.errorText}>카테고리를 불러오지 못했습니다. 앱을 다시 시작해 주세요.</Text>
            ) : (
              <View style={styles.categoryGrid}>
                {(categoriesData?.items ?? []).map((cat) => (
                  <TouchableOpacity
                    key={cat.id}
                    onPress={() => !isPending && setSelectedCategoryId(cat.id)}
                    style={[
                      styles.categoryBtn,
                      selectedCategoryId === cat.id && styles.categoryBtnSelected,
                      isPending && styles.disabled,
                    ]}
                  >
                    <Text
                      style={[
                        styles.categoryBtnText,
                        selectedCategoryId === cat.id && styles.categoryBtnTextSelected,
                      ]}
                    >
                      {cat.name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </View>

          {/* 지역 */}
          <View style={styles.section}>
            <Text style={styles.label}>지역 *</Text>
            <Input
              value={region}
              onChangeText={setRegion}
              placeholder="예: 서울 강남구"
              editable={!isPending}
            />
          </View>

          {/* 설명 — multiline이 필요하므로 TextInput 직접 사용 */}
          <View style={styles.section}>
            <Text style={styles.label}>설명 *</Text>
            <TextInput
              value={description}
              onChangeText={setDescription}
              placeholder="요청 내용을 자세히 입력해 주세요"
              placeholderTextColor={tokens.colors.textDisabled}
              editable={!isPending}
              multiline
              numberOfLines={4}
              style={[styles.textarea, !isPending ? undefined : styles.disabled]}
            />
          </View>

          {/* 희망 일정 (선택) */}
          <View style={styles.section}>
            <Text style={styles.label}>희망 일정 (선택)</Text>
            <Input
              value={desiredSchedule}
              onChangeText={setDesiredSchedule}
              placeholder="예: 이번 주 중, 6/20 오전"
              editable={!isPending}
            />
          </View>

          {/* 예산 (선택) */}
          <View style={styles.section}>
            <Text style={styles.label}>예산 (선택, ₩)</Text>
            <Input
              value={budget}
              onChangeText={setBudget}
              placeholder="예: 50000"
              keyboardType="numeric"
              editable={!isPending}
            />
          </View>

          {/* 유효성 에러 */}
          {validationError && (
            <Text style={styles.errorText}>{validationError}</Text>
          )}

          {/* API 에러 */}
          {errorMsg && (
            <Text style={styles.errorText}>{errorMsg}</Text>
          )}

          <Button
            label={isPending ? '제출 중…' : '요청 제출'}
            onPress={handleSubmit}
            disabled={isPending}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  flex: { flex: 1 },
  content: { padding: tokens.spacing.lg, gap: tokens.spacing.md },
  section: { gap: tokens.spacing.xs },
  label: {
    fontSize: tokens.fontSize.sm,
    fontWeight: tokens.fontWeight.medium,
    color: tokens.colors.text,
  },
  loadingText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
  },
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: tokens.spacing.xs,
  },
  categoryBtn: {
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.sm,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    backgroundColor: tokens.colors.background,
  },
  categoryBtnSelected: {
    borderColor: tokens.colors.primary,
    backgroundColor: `${tokens.colors.primary}15`,
  },
  categoryBtnText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.text,
  },
  categoryBtnTextSelected: {
    color: tokens.colors.primary,
    fontWeight: tokens.fontWeight.medium,
  },
  disabled: { opacity: 0.5 },
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
  errorText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.danger,
  },
});
