const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');
const fs = require('fs');

const config = getDefaultConfig(__dirname);

const rnwPath = path.resolve(__dirname, 'node_modules/react-native-web');

// Native-only modules that need web stubs
const webStubs = {
  '@stripe/stripe-react-native': path.resolve(__dirname, 'web-stubs/stripe.js'),
  'react-native-maps': path.resolve(__dirname, 'web-stubs/maps.js'),
};

const originalResolveRequest = config.resolver.resolveRequest;

config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === 'web') {
    // Stub out native-only modules
    if (webStubs[moduleName]) {
      return {
        filePath: webStubs[moduleName],
        type: 'sourceFile',
      };
    }

    // Redirect 'react-native' imports to 'react-native-web'
    if (moduleName === 'react-native') {
      return {
        filePath: path.resolve(rnwPath, 'dist', 'index.js'),
        type: 'sourceFile',
      };
    }

    // Redirect react-native subpath imports
    if (moduleName.startsWith('react-native/')) {
      return {
        filePath: path.resolve(rnwPath, 'dist', 'index.js'),
        type: 'sourceFile',
      };
    }

    // Catch unresolvable internal imports from within react-native
    const originDir = context.originModulePath || '';
    const isFromRN = originDir.includes('node_modules/react-native/');
    const isRelative = moduleName.startsWith('./') || moduleName.startsWith('../');

    if (isFromRN && isRelative) {
      try {
        if (originalResolveRequest) {
          return originalResolveRequest(context, moduleName, platform);
        }
        return context.resolveRequest(context, moduleName, platform);
      } catch {
        return {
          filePath: path.resolve(__dirname, 'web-stub.js'),
          type: 'sourceFile',
        };
      }
    }

    // Block .native.js resolution on web
    try {
      const result = originalResolveRequest
        ? originalResolveRequest(context, moduleName, platform)
        : context.resolveRequest(context, moduleName, platform);

      if (result && result.filePath && result.filePath.endsWith('.native.js')) {
        const plainPath = result.filePath.replace('.native.js', '.js');
        if (fs.existsSync(plainPath)) {
          return { filePath: plainPath, type: 'sourceFile' };
        }
      }
      return result;
    } catch {
      return context.resolveRequest(context, moduleName, platform);
    }
  }

  if (originalResolveRequest) {
    return originalResolveRequest(context, moduleName, platform);
  }
  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
