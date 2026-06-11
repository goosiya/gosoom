// 모노레포 인식 Metro 설정 (Expo 공식 monorepo + NativeWind)
const { getDefaultConfig } = require('expo/metro-config');
const { withNativeWind } = require('nativewind/metro');
const path = require('path');

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, '../..');

const config = getDefaultConfig(projectRoot);

// 1) 모노레포 전체를 감시 (packages/* 변경 감지)
config.watchFolders = [monorepoRoot];

// 2) 앱 → 루트 순으로 node_modules 해석 (.npmrc node-linker=hoisted와 정합)
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(monorepoRoot, 'node_modules'),
];

module.exports = withNativeWind(config, { input: './src/global.css' });
