import type { ReactNode } from 'react'
import { I18nProvider } from 'react-aria-components'

/**
 * The language the interface is written in: British English, as its text
 * ("Personalise", "colour") and the page's lang attribute say.
 */
export const INTERFACE_LOCALE = 'en-GB'

/**
 * React Aria's own words (a hidden "Dismiss", "selected", a list's
 * announcements) in the interface's language, not the browser's: without it a
 * German browser hears "Schließen" in an English interface (task-392 item 18).
 * Record content keeps its own languages; this is only the interface's.
 */
export default function InterfaceLanguage({ children }: { children: ReactNode }) {
  return <I18nProvider locale={INTERFACE_LOCALE}>{children}</I18nProvider>
}
