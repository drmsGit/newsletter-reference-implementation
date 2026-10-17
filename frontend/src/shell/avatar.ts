/**
 * The initials avatar's colour and letters (docs/design/HANDOFF.md section 4,
 * rule from 2026-10-13). The colour is a function of the name — the same name
 * is the same colour on every device and reload, with nothing random and
 * nothing stored — and only the hue varies, so the theme's saturation and
 * lightness keep the initials readable on every hue. The colour is
 * decoration: the initials carry the identity.
 */

/** FNV-1a, 32 bit, over the UTF-16 code units of the normalised name, mod 360. An email keeps
 * its +tag here (the handoff's vectors); only the initials drop it. */
export function avatarHue(name: string): number {
  const s = normalise(name)
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h % 360
}

/** First letter of the first and the last word; an email's part before the @, without a +tag. */
export function initials(name: string): string {
  let s = name.trim()
  if (s.includes('@') && !s.includes(' ')) s = s.split('@')[0].split('+')[0]
  const words = s.split(/[\s._-]+/).filter(Boolean)
  if (words.length === 0) return '?'
  const first = words[0][0]
  const last = words.length > 1 ? words[words.length - 1][0] : ''
  return (first + last).toUpperCase()
}

/** What the hue is taken from: the name as shown, trimmed, NFC, lower case (the reference implementation). */
function normalise(name: string): string {
  return name.trim().normalize('NFC').toLowerCase()
}
