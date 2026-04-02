// frontend/src/contexts/ThemeContext.ts
// Provides current theme to deeply nested components without prop drilling.

import { createContext, useContext } from 'react';

type Theme = 'light' | 'dark';

export const ThemeContext = createContext<Theme>('light');

export function useCurrentTheme(): Theme {
  return useContext(ThemeContext);
}
