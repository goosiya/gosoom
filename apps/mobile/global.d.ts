/// <reference types="expo/types" />
/// <reference types="nativewind/types" />

// Expo web에서 Metro가 번들하는 CSS 모듈/CSS import의 tsc용 타입 선언.
// (런타임 번들은 Metro가 처리, tsc --noEmit 보조용)
declare module '*.module.css';
declare module '*.css';
