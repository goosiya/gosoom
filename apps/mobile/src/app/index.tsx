// 공개 메인 랜딩 화면(`/`). 미인증 방문자에게 노출되며 로그인/회원가입으로 연결.
// 인증된 사용자는 _layout.tsx의 AuthGate가 역할별 대시보드로 리다이렉트.
import { Feather } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View, useWindowDimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { tokens } from '@gosoom/ui';

type FeatherName = keyof typeof Feather.glyphMap;

const FEATURES: { icon: FeatherName; title: string; description: string }[] = [
  {
    icon: 'search',
    title: '원하는 서비스를 요청',
    description: '필요한 일을 등록하면 가까운 고수들이 확인합니다.',
  },
  {
    icon: 'file-text',
    title: '맞춤 견적 비교',
    description: '여러 고수의 견적을 한눈에 비교하고 선택하세요.',
  },
  {
    icon: 'message-circle',
    title: '실시간 채팅',
    description: '수락한 견적의 고수와 바로 대화하며 일정을 조율하세요.',
  },
];

// 브랜드 컬러 투명도 변형 (RN은 8자리 hex 지원)
const PRIMARY_TINT = tokens.colors.primary + '14'; // 약 8%
const PRIMARY_TINT_STRONG = tokens.colors.primary + '1F'; // 약 12%

export default function LandingScreen() {
  const router = useRouter();
  const { width } = useWindowDimensions();
  // 태블릿/웹 등 넓은 화면에서는 콘텐츠 폭을 제한해 가독성 유지.
  const isWide = width >= 768;
  const contentMaxWidth = isWide ? 640 : undefined;

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <ScrollView
        contentContainerStyle={[styles.scroll, { maxWidth: contentMaxWidth, alignSelf: 'center', width: '100%' }]}
        showsVerticalScrollIndicator={false}>
        {/* 상단 브랜드 */}
        <View style={styles.topBar}>
          <Text style={styles.brand}>meetgo</Text>
          <TouchableOpacity
            onPress={() => router.push('/(auth)/login')}
            accessibilityRole="button">
            <Text style={styles.topBarLink}>로그인</Text>
          </TouchableOpacity>
        </View>

        {/* 히어로 — 배경 장식 도형이 들어간 패널 */}
        <View style={styles.hero}>
          {/* 장식 배경(클리핑됨): 컬러 블롭 + 링 + 점 클러스터 */}
          <View style={styles.heroDecor} pointerEvents="none">
            <View style={styles.heroBlobOne} />
            <View style={styles.heroBlobTwo} />
            <View style={styles.heroRing} />
            <View style={styles.dotCluster}>
              {Array.from({ length: 16 }).map((_, i) => (
                <View key={i} style={styles.dot} />
              ))}
            </View>
          </View>

          <View style={styles.badge}>
            <Feather name="zap" size={13} color={tokens.colors.primary} />
            <Text style={styles.badgeText}>고객·고수 서비스 매칭 플랫폼</Text>
          </View>
          <Text style={[styles.heroTitle, isWide && styles.heroTitleWide]}>
            필요한 서비스,{'\n'}
            <Text style={styles.heroTitleAccent}>meetgo</Text>에서 연결하세요
          </Text>
          <Text style={styles.heroSubtitle}>
            요청을 등록하면 검증된 고수들의 맞춤 견적을 받아볼 수 있어요.
            비교하고, 채팅하고, 바로 시작하세요.
          </Text>
        </View>

        {/* 앱 미리보기 카드 */}
        <View style={styles.previewWrap}>
          <View style={styles.previewCard}>
            {/* 요청 헤더 */}
            <View style={styles.previewHeader}>
              <View style={styles.previewIconCircle}>
                <Feather name="box" size={18} color={tokens.colors.primary} />
              </View>
              <View style={styles.flex1}>
                <Text style={styles.previewTitle}>이사·청소 도움</Text>
                <Text style={styles.previewMeta}>서울 강남구 · 오늘</Text>
              </View>
              <View style={styles.statusChip}>
                <Text style={styles.statusChipText}>모집중</Text>
              </View>
            </View>

            {/* 본문 스켈레톤 */}
            <View style={styles.skeletonGroup}>
              <View style={[styles.skeletonBar, { width: '100%' }]} />
              <View style={[styles.skeletonBar, { width: '66%' }]} />
            </View>

            {/* 도착한 견적 */}
            <View style={styles.quoteCard}>
              <View style={styles.quoteAvatar}>
                <Text style={styles.quoteAvatarText}>김</Text>
              </View>
              <View style={styles.flex1}>
                <Text style={styles.quoteName}>김고수 고수</Text>
                <View style={styles.ratingRow}>
                  <Feather name="star" size={11} color={tokens.colors.primary} />
                  <Text style={styles.ratingText}>4.9 · 후기 128</Text>
                </View>
              </View>
              <Text style={styles.quotePrice}>120,000원</Text>
            </View>
          </View>

          {/* 플로팅 매칭 배지 */}
          <View style={styles.matchedBadge}>
            <Text style={styles.matchedBadgeText}>매칭 완료 🎉</Text>
          </View>
        </View>

        {/* 기능 카드 */}
        <View style={styles.features}>
          {FEATURES.map((feature) => (
            <View key={feature.title} style={styles.featureCard}>
              <View style={styles.featureIconCircle}>
                <Feather name={feature.icon} size={20} color={tokens.colors.primary} />
              </View>
              <View style={styles.flex1}>
                <Text style={styles.featureTitle}>{feature.title}</Text>
                <Text style={styles.featureDesc}>{feature.description}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* CTA 버튼 */}
        <View style={styles.ctaGroup}>
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => router.push('/(auth)/signup')}
            accessibilityRole="button">
            <Text style={styles.primaryButtonText}>무료로 시작하기</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={() => router.push('/(auth)/login')}
            accessibilityRole="button">
            <Text style={styles.secondaryButtonText}>로그인</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  flex1: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: tokens.spacing.lg,
    paddingBottom: tokens.spacing.xxl,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: tokens.spacing.md,
  },
  brand: {
    fontSize: 22,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.primary,
  },
  topBarLink: {
    fontSize: tokens.fontSize.base,
    color: tokens.colors.primary,
    fontWeight: tokens.fontWeight.medium,
  },
  hero: {
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 20,
    backgroundColor: tokens.colors.primary + '12', // 약 7% 틴트 패널
    paddingHorizontal: tokens.spacing.lg,
    paddingTop: tokens.spacing.xl,
    paddingBottom: tokens.spacing.xl,
    marginTop: tokens.spacing.sm,
    gap: tokens.spacing.lg,
  },
  // 히어로 배경 장식
  heroDecor: {
    ...StyleSheet.absoluteFillObject,
  },
  heroBlobOne: {
    position: 'absolute',
    top: -50,
    right: -40,
    width: 170,
    height: 170,
    borderRadius: 999,
    backgroundColor: tokens.colors.primary + '24',
  },
  heroBlobTwo: {
    position: 'absolute',
    bottom: -60,
    left: -50,
    width: 190,
    height: 190,
    borderRadius: 999,
    backgroundColor: tokens.colors.primary + '17',
  },
  heroRing: {
    position: 'absolute',
    top: 24,
    right: 48,
    width: 64,
    height: 64,
    borderRadius: 999,
    borderWidth: 2,
    borderColor: tokens.colors.primary + '38',
  },
  dotCluster: {
    position: 'absolute',
    top: 18,
    right: 18,
    width: 52,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 999,
    backgroundColor: tokens.colors.primary + '4D',
  },
  badge: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: PRIMARY_TINT,
    borderWidth: 1,
    borderColor: PRIMARY_TINT_STRONG,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.xs + 2,
    borderRadius: 999,
  },
  badgeText: {
    color: tokens.colors.primary,
    fontSize: tokens.fontSize.sm,
    fontWeight: tokens.fontWeight.medium,
  },
  heroTitle: {
    fontSize: 32,
    lineHeight: 42,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  heroTitleWide: {
    fontSize: 40,
    lineHeight: 52,
  },
  heroTitleAccent: {
    color: tokens.colors.primary,
  },
  heroSubtitle: {
    fontSize: tokens.fontSize.base,
    lineHeight: 24,
    color: tokens.colors.textSecondary,
  },

  // 앱 미리보기 카드
  previewWrap: {
    paddingTop: tokens.spacing.md,
    paddingBottom: tokens.spacing.lg,
  },
  previewCard: {
    backgroundColor: tokens.colors.background,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    padding: tokens.spacing.lg,
    gap: tokens.spacing.md,
    // 그림자(iOS/Android)
    shadowColor: tokens.colors.primary,
    shadowOpacity: 0.12,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 4,
  },
  previewHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
  },
  previewIconCircle: {
    width: 40,
    height: 40,
    borderRadius: tokens.radius.md,
    backgroundColor: PRIMARY_TINT,
    justifyContent: 'center',
    alignItems: 'center',
  },
  previewTitle: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  previewMeta: {
    fontSize: 12,
    color: tokens.colors.textSecondary,
    marginTop: 1,
  },
  statusChip: {
    backgroundColor: PRIMARY_TINT,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: 4,
    borderRadius: 999,
  },
  statusChipText: {
    fontSize: 11,
    fontWeight: tokens.fontWeight.medium,
    color: tokens.colors.primary,
  },
  skeletonGroup: { gap: tokens.spacing.sm },
  skeletonBar: {
    height: 10,
    borderRadius: 999,
    backgroundColor: tokens.colors.backgroundSecondary,
  },
  quoteCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    backgroundColor: PRIMARY_TINT,
    borderWidth: 1,
    borderColor: PRIMARY_TINT_STRONG,
    borderRadius: tokens.radius.md,
    padding: tokens.spacing.md,
  },
  quoteAvatar: {
    width: 32,
    height: 32,
    borderRadius: 999,
    backgroundColor: tokens.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },
  quoteAvatarText: {
    color: tokens.colors.textOnPrimary,
    fontSize: 13,
    fontWeight: tokens.fontWeight.semibold,
  },
  quoteName: {
    fontSize: 13,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  ratingRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 1 },
  ratingText: { fontSize: 11, color: tokens.colors.textSecondary },
  quotePrice: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.primary,
  },
  matchedBadge: {
    position: 'absolute',
    top: 0,
    right: tokens.spacing.sm,
    backgroundColor: tokens.colors.primary,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: 6,
    borderRadius: 999,
    shadowColor: tokens.colors.primary,
    shadowOpacity: 0.3,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 5,
  },
  matchedBadgeText: {
    color: tokens.colors.textOnPrimary,
    fontSize: 12,
    fontWeight: tokens.fontWeight.semibold,
  },

  // 기능 카드
  features: {
    gap: tokens.spacing.md,
    paddingVertical: tokens.spacing.lg,
  },
  featureCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.md,
    backgroundColor: tokens.colors.backgroundSecondary,
    borderRadius: tokens.radius.lg,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    padding: tokens.spacing.lg,
  },
  featureIconCircle: {
    width: 44,
    height: 44,
    borderRadius: tokens.radius.md,
    backgroundColor: PRIMARY_TINT,
    justifyContent: 'center',
    alignItems: 'center',
  },
  featureTitle: {
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
    color: tokens.colors.text,
  },
  featureDesc: {
    fontSize: tokens.fontSize.sm,
    lineHeight: 20,
    color: tokens.colors.textSecondary,
    marginTop: 2,
  },

  // CTA
  ctaGroup: {
    gap: tokens.spacing.md,
    paddingTop: tokens.spacing.md,
  },
  primaryButton: {
    height: 52,
    backgroundColor: tokens.colors.primary,
    borderRadius: tokens.radius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  primaryButtonText: {
    color: tokens.colors.textOnPrimary,
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
  },
  secondaryButton: {
    height: 52,
    backgroundColor: tokens.colors.background,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: tokens.colors.text,
    fontSize: tokens.fontSize.base,
    fontWeight: tokens.fontWeight.semibold,
  },
});
