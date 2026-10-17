import {
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
} from 'react-aria-components'

import { useSwitchBrand, type SessionContext } from '../api/session'
import { avatarHue, initials } from './avatar'

/**
 * Change the brand this session is working in.
 *
 * **Renders nothing at all when the session is not switchable.** ADR-150 point 4
 * promises that a company with one brand "never has to think about the
 * switcher", and the backend already computes that answer -- `brand.switchable`
 * is false when the signed-in person holds a grant on exactly one brand. Hiding
 * it here rather than disabling it is what keeps that promise: a disabled
 * control is still a control somebody has to understand.
 *
 * The list is `session.brands`, which is the brands this person may switch to
 * rather than every brand that exists. Offering more would be showing somebody
 * a list of other people's brands.
 *
 * v2 (task-372): the label sits inside the control (navigation board). In the
 * collapsed rail the switcher is the brand's tile, which opens the navigation
 * so the brand can be chosen; the brand's name stays its accessible name.
 */
export default function BrandSwitcher({
  session,
  collapsed = false,
  onExpand,
}: {
  session: SessionContext
  collapsed?: boolean
  onExpand?: () => void
}) {
  const switchBrand = useSwitchBrand()
  const brand = session.brand

  if (!brand?.switchable) return null

  if (collapsed)
    return (
      <Button
        className="brand-tile avatar avatar--square"
        aria-label={`Brand: ${brand.name}. Open the navigation to switch.`}
        style={{ '--avatar-hue': avatarHue(brand.name) } as React.CSSProperties}
        onPress={onExpand}
      >
        {initials(brand.name)}
      </Button>
    )

  return (
    <Select
      className="react-aria-Select brand-select"
      selectedKey={brand.id}
      isDisabled={switchBrand.isPending}
      onSelectionChange={(key) => switchBrand.mutate(Number(key))}
    >
      <Label className="sr-only">Brand</Label>
      <Button className="brand-btn">
        <span className="brand-btn__text">
          <span className="brand-btn__label" aria-hidden="true">Brand</span>
          <SelectValue />
        </span>
      </Button>
      <Popover>
        <ListBox items={session.brands}>
          {(item) => <ListBoxItem id={item.id}>{item.name}</ListBoxItem>}
        </ListBox>
      </Popover>
    </Select>
  )
}
