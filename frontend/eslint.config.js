// ESLint in CI (ADR-190, task-105). Errors block; warnings are reported and
// never fail the build. Blocking: ESLint's and typescript-eslint's
// recommended rules, and React's rules of hooks. Warning only: jsx-a11y,
// whose findings feed the keyboard and accessibility session (deferred
// 2026-10-05), and react-hooks' dependency-list advice. Widening what blocks
// is a decision, not a cleanup.
import js from '@eslint/js'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
import tseslint from 'typescript-eslint'

const warnOnly = (rules) => Object.fromEntries(Object.keys(rules).map((name) => [name, 'warn']))

export default tseslint.config(
  { ignores: ['dist', 'src/api/schema.d.ts'] },
  {
    files: ['**/*.{ts,tsx,js}'],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
    plugins: { 'react-hooks': reactHooks, 'jsx-a11y': jsxA11y },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
      // Taking keys out of an object by naming them (`const { a: _a, ...kept }`)
      // is how the audience editor keeps what a form does not edit.
      '@typescript-eslint/no-unused-vars': ['error', { ignoreRestSiblings: true }],
      ...warnOnly(jsxA11y.flatConfigs.recommended.rules),
    },
  },
)
