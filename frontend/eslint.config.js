// ESLint for frontend/ (spec 11). TypeScript is linted with type information, in CI and in
// pre-commit alike (ADR 0016). Formatting is Prettier's job, so no stylistic rules here.
import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import { defineConfig, globalIgnores } from 'eslint/config'
import tseslint from 'typescript-eslint'

export default defineConfig([
  // src/api/generated/ is written by npm run gen:api and never edited (ADR 0016).
  globalIgnores(['dist', 'coverage', 'src/api/generated']),
  {
    files: ['**/*.js'],
    extends: [js.configs.recommended],
  },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.strictTypeChecked,
      reactHooks.configs.flat.recommended,
    ],
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
  },
])
