import { describe, expect, it } from 'vitest'

import { avatarHue, initials } from './avatar'

/** The handoff's own vectors (docs/design/HANDOFF.md section 4), so the app matches the boards. */
const VECTORS: [string, string, number][] = [
  ['Nordlicht Kaffee', 'NK', 206],
  ['Maria Hartmann', 'MH', 176],
  ['Jonas Weber', 'JW', 121],
  ['Anke Voss', 'AV', 319],
  ['Robin Approver', 'RA', 156],
  ['Acme Agency', 'AA', 210],
  ['Scheduler', 'S', 242],
  ['m.hartmann@nordlicht-kaffee.example', 'MH', 163],
  ['kim.lee@example.test', 'KL', 200],
  ['anna+news@example.test', 'A', 93],
  ['support@example.test', 'S', 244],
]

describe('the initials avatar (task-372)', () => {
  it.each(VECTORS)('%s gives %s and hue %i', (name, letters, hue) => {
    expect(initials(name)).toBe(letters)
    expect(avatarHue(name)).toBe(hue)
  })

  it('is the same colour however the name is typed', () => {
    expect(avatarHue('  anke voss ')).toBe(avatarHue('ANKE VOSS'))
  })
})
