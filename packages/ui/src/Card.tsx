// RN-Web 호환 Card 컨테이너 프리미티브 (AR16).
import type { ReactNode } from 'react';
import { View, StyleSheet } from 'react-native';

export interface CardProps {
  children: ReactNode;
}

export function Card({ children }: CardProps) {
  return <View style={styles.card}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
});
