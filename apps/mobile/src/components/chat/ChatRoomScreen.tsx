import { useEffect, useReducer, useRef, useState } from 'react';
import {
  FlatList,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

import { Button, tokens } from '@gosoom/ui';
import {
  list_messages,
  useSendMessage,
  type MessageRead,
} from '@gosoom/api-client';

import { useAuth } from '@/features/auth';

type MsgAction =
  | { type: 'POLL'; items: MessageRead[] }
  | { type: 'SENT'; msg: MessageRead };

function messagesReducer(state: MessageRead[], action: MsgAction): MessageRead[] {
  switch (action.type) {
    case 'POLL': {
      const existing = new Set(state.map((m) => m.id));
      const fresh = action.items.filter((m) => !existing.has(m.id));
      return fresh.length ? [...state, ...fresh] : state;
    }
    case 'SENT':
      return state.some((m) => m.id === action.msg.id) ? state : [...state, action.msg];
    default:
      return state;
  }
}

export default function ChatRoomScreen() {
  const rawId = useLocalSearchParams<{ id: string | string[] }>().id;
  const chatRoomId = Array.isArray(rawId) ? rawId[0] : rawId;
  const { user } = useAuth();

  const lastIdRef = useRef<string | undefined>(undefined);
  const [allMessages, dispatchMsg] = useReducer(messagesReducer, []);
  const [content, setContent] = useState('');
  const [sendError, setSendError] = useState<string | null>(null);
  const flatListRef = useRef<FlatList<MessageRead>>(null);

  const { data: pollData, isError: isPollError } = useQuery({
    queryKey: ['chat-messages', chatRoomId],
    queryFn: () => list_messages(chatRoomId!, { after: lastIdRef.current }),
    refetchInterval: 2000,
    enabled: !!chatRoomId,
  });

  useEffect(() => {
    if (!pollData?.items?.length) return;
    dispatchMsg({ type: 'POLL', items: pollData.items });
    const lastItem = pollData.items[pollData.items.length - 1];
    if (lastItem?.id && (!lastIdRef.current || lastItem.id > lastIdRef.current)) {
      lastIdRef.current = lastItem.id;
    }
  }, [pollData]);

  useEffect(() => {
    if (allMessages.length > 0) {
      flatListRef.current?.scrollToEnd({ animated: true });
    }
  }, [allMessages]);

  const sendMutation = useSendMessage<Error>({
    mutation: {
      onSuccess: (newMsg) => {
        dispatchMsg({ type: 'SENT', msg: newMsg });
        if (!lastIdRef.current || newMsg.id > lastIdRef.current) {
          lastIdRef.current = newMsg.id;
        }
        setContent('');
        setSendError(null);
      },
      onError: (err) => setSendError(err.message || '메시지 전송에 실패했습니다.'),
    },
  });

  const handleSend = () => {
    if (!content.trim() || !chatRoomId) return;
    sendMutation.mutate({ chatRoomId, data: { content: content.trim() } });
  };

  const isMyMessage = (msg: MessageRead) => msg.senderId === user?.id;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <FlatList
          ref={flatListRef}
          data={allMessages}
          keyExtractor={(item) => item.id}
          style={styles.flex}
          contentContainerStyle={styles.messageList}
          renderItem={({ item }) => (
            <View style={[styles.bubble, isMyMessage(item) ? styles.myBubble : styles.theirBubble]}>
              <Text style={[styles.bubbleText, isMyMessage(item) ? styles.myText : styles.theirText]}>
                {item.content}
              </Text>
            </View>
          )}
        />

        {isPollError && (
          <Text style={styles.errorText}>메시지를 불러오지 못했습니다.</Text>
        )}
        <View style={styles.inputRow}>
          <TextInput
            value={content}
            onChangeText={(text) => { setContent(text); if (sendError) setSendError(null); }}
            placeholder="메시지를 입력하세요"
            placeholderTextColor={tokens.colors.textSecondary}
            style={styles.messageInput}
            returnKeyType="send"
            onSubmitEditing={handleSend}
            blurOnSubmit={false}
            editable={!sendMutation.isPending}
          />
          <Button
            label={sendMutation.isPending ? '전송 중…' : '전송'}
            onPress={handleSend}
            disabled={sendMutation.isPending || !content.trim()}
          />
        </View>
        {sendError && <Text style={styles.errorText}>{sendError}</Text>}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: tokens.colors.background },
  flex: { flex: 1 },
  messageList: {
    padding: tokens.spacing.md,
    gap: tokens.spacing.sm,
  },
  bubble: {
    maxWidth: '75%',
    borderRadius: tokens.radius.lg,
    paddingHorizontal: tokens.spacing.md,
    paddingVertical: tokens.spacing.sm,
  },
  myBubble: {
    alignSelf: 'flex-end',
    backgroundColor: tokens.colors.primary,
  },
  theirBubble: {
    alignSelf: 'flex-start',
    backgroundColor: tokens.colors.backgroundSecondary,
  },
  bubbleText: { fontSize: tokens.fontSize.sm },
  myText: { color: '#FFFFFF' },
  theirText: { color: tokens.colors.text },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: tokens.spacing.sm,
    borderTopWidth: 1,
    borderTopColor: tokens.colors.border,
    gap: tokens.spacing.sm,
  },
  messageInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: tokens.colors.border,
    borderRadius: tokens.radius.md,
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.text,
    backgroundColor: tokens.colors.backgroundSecondary,
  },
  errorText: {
    fontSize: tokens.fontSize.sm,
    color: tokens.colors.danger,
    paddingHorizontal: tokens.spacing.md,
    paddingBottom: tokens.spacing.xs,
  },
});
