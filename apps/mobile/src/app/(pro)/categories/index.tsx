import { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { Button, tokens } from '@gosoom/ui';
import {
  useGetProCategories,
  useSetProCategories,
  useListCategories,
  getGetProCategoriesQueryKey,
  type ProCategoriesRead,
  type PageCategoryRead,
} from '@gosoom/api-client';

export default function ProCategoriesScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const initialized = useRef(false);

  const { data: proCategories, isPending: proCatLoading, isError: proCatError } =
    useGetProCategories<ProCategoriesRead, Error>();

  const { data: allCategories, isPending: allCatLoading, isError: allCatError } =
    useListCategories<PageCategoryRead, Error>({ limit: 100 });

  useEffect(() => {
    if (!initialized.current && proCategories?.categoryIds) {
      setSelectedIds(proCategories.categoryIds);
      initialized.current = true;
    }
  }, [proCategories]);

  const setMutation = useSetProCategories({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetProCategoriesQueryKey() });
        router.back();
      },
      onError: (err) => setErrorMsg((err as Error)?.message ?? '오류가 발생했습니다.'),
    },
  });

  const toggleCategory = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id],
    );
  };

  const handleSave = () => {
    setErrorMsg(null);
    if (selectedIds.length === 0) {
      setErrorMsg('최소 1개 이상의 카테고리를 선택해 주세요.');
      return;
    }
    setMutation.mutate({ data: { categoryIds: selectedIds } });
  };

  const isPending = setMutation.isPending;
  const isLoading = proCatLoading || allCatLoading;

  if (isLoading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerContent}>
          <ActivityIndicator color={tokens.colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (proCatError || allCatError) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centerContent}>
          <Text style={styles.errorText}>카테고리를 불러오지 못했습니다.</Text>
          <Button label="다시 시도" onPress={() => router.back()} />
        </View>
      </SafeAreaView>
    );
  }

  const categories = allCategories?.items ?? [];

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.description}>
          활동할 서비스 카테고리를 선택하세요. 선택한 카테고리의 요청이 피드에 표시됩니다.
        </Text>

        <View style={styles.grid}>
          {categories.map((cat) => {
            const isSelected = selectedIds.includes(cat.id);
            return (
              <TouchableOpacity
                key={cat.id}
                onPress={() => !isPending && toggleCategory(cat.id)}
                style={[
                  styles.categoryBtn,
                  isSelected && styles.categoryBtnSelected,
                  isPending && styles.disabled,
                ]}
                activeOpacity={isPending ? 1 : 0.7}
              >
                <Text
                  style={[
                    styles.categoryBtnText,
                    isSelected && styles.categoryBtnTextSelected,
                  ]}
                >
                  {cat.name}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {errorMsg && <Text style={styles.errorText}>{errorMsg}</Text>}

        <Button
          label={isPending ? '저장 중…' : '카테고리 저장'}
          onPress={handleSave}
          disabled={isPending}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  content: { padding: tokens.spacing.lg, gap: tokens.spacing.md },
  description: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.textSecondary,
    lineHeight: 20,
  },
  grid: {
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
  errorText: { fontSize: tokens.fontSize.sm, color: tokens.colors.danger },
  centerContent: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: tokens.spacing.md,
    padding: tokens.spacing.xl,
  },
});
