import {
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
} from 'react-aria-components'

/**
 * One labelled choice from a fixed list -- React Aria's Select, which gives it
 * the listbox semantics and keyboard handling a native `<select>` styled to
 * match would not. Shared by Settings and the approval inbox's filters.
 *
 * An option's `indent` nests it visually under the one before it (a category
 * under its parent); typing a letter still finds it by its name.
 */
export default function Choice({
  label,
  options,
  selected,
  onChange,
}: {
  label: string
  options: { id: string; name: string; indent?: number }[]
  selected: string
  onChange: (id: string) => void
}) {
  return (
    <Select selectedKey={selected} onSelectionChange={(key) => onChange(String(key))}>
      <Label>{label}</Label>
      <Button>
        <SelectValue />
      </Button>
      <Popover>
        <ListBox items={options}>
          {(item) => (
            <ListBoxItem
              id={item.id}
              textValue={item.name}
              style={item.indent ? { paddingInlineStart: `${0.5 + item.indent * 1.25}em` } : undefined}
            >
              {item.name}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </Select>
  )
}
