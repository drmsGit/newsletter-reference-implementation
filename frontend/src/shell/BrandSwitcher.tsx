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
 */
export default function BrandSwitcher({ session }: { session: SessionContext }) {
  const switchBrand = useSwitchBrand()
  const brand = session.brand

  if (!brand?.switchable) return null

  return (
    <Select
      selectedKey={brand.id}
      isDisabled={switchBrand.isPending}
      onSelectionChange={(key) => switchBrand.mutate(Number(key))}
    >
      <Label>Brand</Label>
      <Button>
        <SelectValue />
      </Button>
      <Popover>
        <ListBox items={session.brands}>
          {(item) => <ListBoxItem id={item.id}>{item.name}</ListBoxItem>}
        </ListBox>
      </Popover>
    </Select>
  )
}
