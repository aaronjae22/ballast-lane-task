// Fails a test that logs a console warning or error it didn't declare (ADR 0016). React,
// React Router and Mantine report misuse (missing keys, act() warnings, uncontrolled inputs)
// only through the console, so a passing test must also be a silent one.

type Level = 'error' | 'warn'

interface Expectation {
  level: Level
  pattern: RegExp
  seen: boolean
}

const levels: readonly Level[] = ['error', 'warn']
let expectations: Expectation[] = []
let unexpected: string[] = []

function describe(args: unknown[]): string {
  return args.map((arg) => (arg instanceof Error ? arg.message : String(arg))).join(' ')
}

/** Replaces console.error and console.warn with recorders. Called before each test. */
export function installConsoleGuard(): void {
  expectations = []
  unexpected = []
  for (const level of levels) {
    console[level] = (...args: unknown[]) => {
      const message = describe(args)
      const match = expectations.find((e) => e.level === level && e.pattern.test(message))
      if (match) match.seen = true
      else unexpected.push(`console.${level}: ${message}`)
    }
  }
}

/** Declares a message this test is expected to log. It fails if the message never comes. */
export function expectConsole(level: Level, pattern: RegExp): void {
  expectations.push({ level, pattern, seen: false })
}

/** Throws if anything unexpected was logged, or an expected message wasn't. Then resets. */
export function checkConsole(): void {
  const missing = expectations
    .filter((e) => !e.seen)
    .map((e) => `expected console.${e.level} matching ${String(e.pattern)} was never logged`)
  const problems = [...unexpected, ...missing]
  expectations = []
  unexpected = []
  if (problems.length > 0) throw new Error(problems.join('\n'))
}
