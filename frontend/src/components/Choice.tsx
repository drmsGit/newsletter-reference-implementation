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
 *
 * Nothing chosen shows `placeholder`, in the client's language rather than
 * React Aria's default, which follows the browser's ("Element wählen").
 */
export default function Choice({
  label,
  options,
  selected,
  onChange,
  placeholder = 'Choose…',
}: {
  label: string
  options: { id: string; name: string; indent?: number }[]
  selected: string
  onChange: (id: string) => void
  placeholder?: string
}) {
  return (
    <Select selectedKey={selected} onSelectionChange={(key) => onChange(String(key))} placeholder={placeholder}>
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
